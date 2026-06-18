"""
coupons/views.py

Endpoints:
  POST /api/coupons/validate/   Validate a coupon code against an order total
  GET  /api/coupons/            List active coupons (admin only)
"""
from decimal import Decimal

from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated

from apps.core.responses import error_response, success_response

from .models import Coupon
from .serializers import CouponSerializer


class ValidateCouponSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class CouponViewSet(viewsets.ModelViewSet):
    queryset = Coupon.objects.filter(is_active=True)
    serializer_class = CouponSerializer

    def get_permissions(self):
        if self.action == 'validate':
            return [IsAuthenticated()]
        return [IsAdminUser()]

    @extend_schema(
        summary="Validate a coupon code",
        description=(
            "Check if a coupon code is valid for the given order total. "
            "Returns the discount type, value, and computed discount amount."
        ),
        request=ValidateCouponSerializer,
        responses={
            200: OpenApiResponse(description="Coupon valid — discount details returned"),
            400: OpenApiResponse(description="Invalid or expired coupon"),
        },
    )
    @action(detail=False, methods=["post"], url_path="validate")
    def validate(self, request):
        ser = ValidateCouponSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        code = ser.validated_data["code"].strip().upper()
        order_total = ser.validated_data["order_total"]

        try:
            coupon = Coupon.objects.get(code__iexact=code, is_active=True)
        except Coupon.DoesNotExist:
            return error_response(message="Invalid coupon code.", status_code=400)

        now = timezone.now()

        # Check date validity
        if coupon.valid_from and now < coupon.valid_from:
            return error_response(message="This coupon is not yet active.", status_code=400)
        if coupon.valid_until and now > coupon.valid_until:
            return error_response(message="This coupon has expired.", status_code=400)

        # Check usage limit
        if coupon.max_uses and coupon.used_count >= coupon.max_uses:
            return error_response(message="This coupon has been fully redeemed.", status_code=400)

        # Check minimum order amount
        if order_total < coupon.min_order:
            return error_response(
                message=f"Minimum order of ₹{coupon.min_order} required for this coupon.",
                status_code=400,
            )

        # Calculate discount
        if coupon.discount_type == "percentage":
            discount_amount = round(order_total * coupon.discount_value / Decimal("100"), 2)
        else:  # fixed
            discount_amount = min(coupon.discount_value, order_total)

        return success_response(
            data={
                "code": coupon.code,
                "discount_type": coupon.discount_type,
                "discount_value": str(coupon.discount_value),
                "discount_amount": str(discount_amount),
                "min_order": str(coupon.min_order),
                "message": (
                    f"{coupon.discount_value}% off applied!"
                    if coupon.discount_type == "percentage"
                    else f"₹{coupon.discount_value} off applied!"
                ),
            },
            message="Coupon applied successfully.",
        )
