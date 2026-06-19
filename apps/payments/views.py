"""
payments/views.py — Razorpay payment endpoints.

Endpoints (router basename 'payment'):
  POST /api/payments/create-order/   Create a bookstore Order (pending) +
                                     Razorpay order; returns checkout params.
  POST /api/payments/verify/         Verify the Razorpay signature, mark the
                                     Payment 'paid' and the Order 'confirmed'.
  GET  /api/payments/<order_id>/status/   Payment status for a bookstore order.

Security / correctness:
  - Amount is computed server-side from the books (never trusted from client).
  - Signature is verified server-side with the key secret.
  - razorpay_order_id is unique and a status guard makes verify idempotent,
    preventing duplicate payment processing.
  - Order is only marked 'confirmed' after a verified payment, which is what
    drives author sales stats (status in confirmed/processing/shipped/delivered).
"""
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import F
from decimal import Decimal
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.core.events import ORDER_CREATED, publish_event
from apps.core.responses import error_response, success_response
from apps.coupons.services import CouponError, validate_coupon
from apps.orders.models import Order, OrderItem, OrderDelivery
from apps.books.models import Book

from . import services
from .models import Payment
from .serializers import (
    CreateOrderSerializer,
    PaymentSerializer,
    VerifyPaymentSerializer,
)

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.GenericViewSet):
    """Razorpay payment flow scoped to the authenticated user."""
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user).select_related('order')

    # ── Create Razorpay order ─────────────────────────────────
    @extend_schema(
        summary="Create a Razorpay order for checkout",
        description=(
            "Creates a bookstore Order (status 'pending') from the cart items, "
            "computes the amount server-side, and creates a matching Razorpay "
            "order. Returns the Razorpay order id, key id and amount (in paise) "
            "for Razorpay Checkout. No money moves until the payment is verified."
        ),
        request=CreateOrderSerializer,
        responses={201: OpenApiResponse(description="Razorpay order created")},
    )
    @action(detail=False, methods=["post"], url_path="create-order")
    def create_order(self, request):
        if not services.is_configured():
            return error_response(
                message="Payments are not available right now.",
                status_code=503,
            )

        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data["items"]
        coupon_code = serializer.validated_data.get("coupon_code", "").strip()
        delivery_data = serializer.validated_data.get("delivery")

        try:
            with transaction.atomic():
                total = 0
                order_items = []
                skipped = []
                for item in items_data:
                    try:
                        book = Book.objects.get(id=item["book_id"], is_active=True)
                    except Book.DoesNotExist:
                        skipped.append(item["book_id"])
                        continue
                    qty = item["quantity"]
                    total += book.price * qty
                    order_items.append(
                        OrderItem(book=book, quantity=qty, unit_price=book.price)
                    )

                if not order_items:
                    return error_response(
                        message="None of the books in the cart are available.",
                        status_code=400,
                    )

                # Re-validate the coupon server-side against the computed
                # subtotal — never trust a client-supplied discount.
                coupon = None
                discount_amount = Decimal("0")
                if coupon_code:
                    try:
                        coupon, discount_amount = validate_coupon(coupon_code, total)
                    except CouponError as exc:
                        return error_response(message=str(exc), status_code=400)

                charge_total = max(Decimal(str(total)) - discount_amount, Decimal("0"))

                # Create the order as PENDING — not a sale until paid.
                order = Order.objects.create(
                    user=request.user,
                    status="pending",
                    total_amount=charge_total,
                    discount_amount=discount_amount,
                    coupon=coupon,
                )
                for oi in order_items:
                    oi.order = order
                OrderItem.objects.bulk_create(order_items)

                # Snapshot delivery details onto the order (for tracking).
                if delivery_data:
                    OrderDelivery.objects.create(order=order, **delivery_data)

                # Create the Razorpay order for the discounted amount.
                rp_order = services.create_order(
                    amount=charge_total,
                    receipt=str(order.id),
                    notes={"order_id": str(order.id), "user_id": str(request.user.id)},
                )

                Payment.objects.create(
                    order=order,
                    user=request.user,
                    amount=charge_total,
                    currency=rp_order.get("currency", "INR"),
                    status="created",
                    razorpay_order_id=rp_order["id"],
                )
        except services.PaymentServiceError as exc:
            return error_response(message=exc.message, status_code=exc.status_code)
        except Exception as exc:
            logger.exception("create_order failed: %s", exc)
            return error_response(
                message="Could not start checkout. Please try again.",
                status_code=500,
            )

        return success_response(
            data={
                "order_id": str(order.id),
                "razorpay_order_id": rp_order["id"],
                "razorpay_key_id": settings.RAZORPAY_KEY_ID,
                "amount": rp_order["amount"],          # paise
                "currency": rp_order["currency"],
                "total_amount": str(charge_total),     # rupees, for display
                "discount_amount": str(discount_amount),
                "coupon_code": coupon.code if coupon else None,
                "skipped_books": skipped,
            },
            message="Razorpay order created.",
            status_code=201,
        )

    # ── Verify payment ────────────────────────────────────────
    @extend_schema(
        summary="Verify a Razorpay payment",
        description=(
            "Verifies the signature returned by Razorpay Checkout. On success, "
            "marks the Payment 'paid' and the Order 'confirmed', deducts stock "
            "and clears the cart. Idempotent — re-verifying an already-paid "
            "order is a no-op success."
        ),
        request=VerifyPaymentSerializer,
        responses={200: OpenApiResponse(description="Payment verified")},
    )
    @action(detail=False, methods=["post"], url_path="verify")
    def verify(self, request):
        serializer = VerifyPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            payment = Payment.objects.select_related("order").get(
                razorpay_order_id=data["razorpay_order_id"],
                user=request.user,
            )
        except Payment.DoesNotExist:
            return error_response(message="Payment record not found.", status_code=404)

        # Idempotency guard — already processed.
        if payment.status == "paid":
            return success_response(
                data=PaymentSerializer(payment).data,
                message="Payment already verified.",
            )

        # Verify the signature server-side.
        valid = services.verify_signature(
            data["razorpay_order_id"],
            data["razorpay_payment_id"],
            data["razorpay_signature"],
        )
        if not valid:
            payment.status = "failed"
            payment.error_description = "Signature verification failed."
            payment.save(update_fields=["status", "error_description", "updated_at"])
            return error_response(
                message="Payment verification failed.", status_code=400
            )

        try:
            with transaction.atomic():
                payment.razorpay_payment_id = data["razorpay_payment_id"]
                payment.razorpay_signature = data["razorpay_signature"]
                payment.status = "paid"
                payment.save(update_fields=[
                    "razorpay_payment_id", "razorpay_signature",
                    "status", "updated_at",
                ])

                order = payment.order
                order.status = "confirmed"
                order.save(update_fields=["status", "updated_at"])

                # Count the coupon redemption now that the order is paid.
                if order.coupon_id:
                    from apps.coupons.models import Coupon
                    Coupon.objects.filter(id=order.coupon_id).update(
                        used_count=F("used_count") + 1
                    )

                # Deduct stock atomically.
                for oi in order.items.all():
                    updated = (
                        Book.objects
                        .filter(id=oi.book_id, stock__gte=oi.quantity)
                        .update(stock=F("stock") - oi.quantity)
                    )
                    if not updated:
                        logger.warning(
                            "Insufficient stock for book_id=%s (wanted %d) on paid order %s",
                            oi.book_id, oi.quantity, order.id,
                        )

                # Clear the backend cart.
                try:
                    from apps.cart.models import Cart
                    cart = Cart.objects.filter(user=request.user).first()
                    if cart:
                        cart.items.all().delete()
                except Exception:
                    pass
        except Exception as exc:
            logger.exception("verify post-processing failed: %s", exc)
            return error_response(
                message="Payment verified but order update failed. Contact support.",
                status_code=500,
            )

        # Analytics: order is now a confirmed sale.
        publish_event(
            ORDER_CREATED,
            {
                "order_id": str(order.id),
                "user_id": str(request.user.id),
                "total_amount": str(order.total_amount),
                "status": order.status,
                "item_count": order.items.count(),
            },
        )

        logger.info("Payment verified: order=%s user=%s", order.id, request.user.id)

        return success_response(
            data=PaymentSerializer(payment).data,
            message="Payment successful. Your order is confirmed!",
        )

    # ── Payment status ────────────────────────────────────────
    @extend_schema(
        summary="Get payment status for a bookstore order",
        responses={200: OpenApiResponse(description="Payment status")},
    )
    @action(detail=False, methods=["get"], url_path=r"(?P<order_id>[^/.]+)/status")
    def status(self, request, order_id=None):
        try:
            payment = Payment.objects.select_related("order").get(
                order_id=order_id, user=request.user
            )
        except Payment.DoesNotExist:
            return error_response(message="Payment record not found.", status_code=404)

        return success_response(
            data=PaymentSerializer(payment).data,
            message="Payment status retrieved.",
        )
