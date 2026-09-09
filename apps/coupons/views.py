"""
coupons/views.py

Endpoints:
  POST /api/coupons/validate/   Validate a coupon code against an order total
  GET  /api/coupons/            List active coupons (admin only)
"""
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated

from apps.core.responses import error_response, success_response

from .models import Coupon
from .serializers import CouponSerializer
from .services import CouponError, validate_coupon


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

        code = ser.validated_data["code"]
        order_total = ser.validated_data["order_total"]

        try:
            coupon, discount_amount = validate_coupon(code, order_total)
        except CouponError as exc:
            return error_response(message=str(exc), status_code=400)

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
