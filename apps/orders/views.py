"""
orders/views.py

Endpoints:
  GET    /api/orders/              List the authenticated user's orders
  POST   /api/orders/              Create an order (raw, from payload)
  POST   /api/orders/checkout/     Checkout: cart → order (simulated payment)
  GET    /api/orders/<id>/         Order detail
"""
import logging

from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.core.events import ORDER_CREATED, publish_event
from apps.core.responses import error_response, success_response

from .models import Order, OrderItem
from .serializers import CheckoutSerializer, OrderSerializer

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related('items__book')

    def perform_create(self, serializer):
        order = serializer.save(user=self.request.user)
        publish_event(
            ORDER_CREATED,
            {
                "order_id": str(order.id),
                "user_id": str(self.request.user.id),
                "total_amount": str(order.total_amount),
                "status": order.status,
                "item_count": order.items.count(),
            },
        )

    # ── Checkout (simulated payment) ──────────────────────────
    @extend_schema(
        summary="Checkout — create order from cart (mock payment)",
        description=(
            "Accepts the cart items, simulates a successful payment, and creates "
            "an Order with status 'confirmed'. Clears the cart server-side if the "
            "user has a backend cart. The frontend should clear its local cart on "
            "a successful response.\n\n"
            "No real payment is processed — this is a development/demo endpoint."
        ),
        request=CheckoutSerializer,
        responses={
            201: OpenApiResponse(description="Order created successfully"),
            400: OpenApiResponse(description="Validation error (empty cart)"),
        },
    )
    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data["items"]
        payment_method = serializer.validated_data.get("payment_method", "card")

        if not items_data:
            return error_response(message="Cart is empty.", status_code=400)

        from apps.books.models import Book

        try:
            with transaction.atomic():
                # Build order items and compute total
                total = 0
                order_items = []
                skipped = []
                for item in items_data:
                    try:
                        book = Book.objects.get(id=item["book_id"], is_active=True)
                    except Book.DoesNotExist:
                        # Skip unavailable books instead of failing the whole order
                        skipped.append(str(item["book_id"]))
                        continue
                    qty = item["quantity"]
                    unit_price = book.price
                    total += unit_price * qty
                    order_items.append(
                        OrderItem(
                            book=book,
                            quantity=qty,
                            unit_price=unit_price,
                        )
                    )

                if not order_items:
                    return error_response(
                        message="None of the books in the cart are available.",
                        status_code=400,
                    )

                # Create the order with status=confirmed (mock payment success)
                order = Order.objects.create(
                    user=request.user,
                    status="confirmed",
                    total_amount=total,
                )
                for oi in order_items:
                    oi.order = order
                OrderItem.objects.bulk_create(order_items)

                # Deduct stock atomically using F() to avoid race conditions.
                from django.db.models import F

                for oi in order_items:
                    updated = Book.objects.filter(
                        id=oi.book_id, stock__gte=oi.quantity
                    ).update(stock=F('stock') - oi.quantity)
                    if not updated:
                        # Stock insufficient — the filter didn't match.
                        # The order is already created (confirmed), so we log
                        # but don't fail. In a real system you'd reject or
                        # backorder. For the demo, we just skip.
                        logger.warning(
                            "Insufficient stock for book_id=%s (wanted %d)",
                            oi.book_id, oi.quantity,
                        )

                # Clear the backend cart if it exists
                try:
                    from apps.cart.models import Cart
                    cart = Cart.objects.filter(user=request.user).first()
                    if cart:
                        cart.items.all().delete()
                except Exception:
                    pass  # Cart module may not be fully wired

        except Exception as exc:
            logger.exception("Checkout failed: %s", exc)
            return error_response(
                message="Checkout failed. Please try again.",
                status_code=500,
            )

        # Publish analytics event
        publish_event(
            ORDER_CREATED,
            {
                "order_id": str(order.id),
                "user_id": str(request.user.id),
                "total_amount": str(order.total_amount),
                "status": order.status,
                "item_count": len(order_items),
            },
        )

        logger.info(
            "Checkout completed: order=%s user=%s total=%s items=%d",
            order.id, request.user.id, total, len(order_items),
        )

        return success_response(
            data={
                "order_id": str(order.id),
                "status": order.status,
                "total_amount": str(order.total_amount),
                "item_count": len(order_items),
                "payment_method": payment_method,
                "skipped_books": skipped,
                "message": (
                    "Payment successful (simulated). Your order is confirmed!"
                    + (f" ({len(skipped)} unavailable item(s) were skipped.)" if skipped else "")
                ),
            },
            message="Order placed successfully.",
            status_code=201,
        )
