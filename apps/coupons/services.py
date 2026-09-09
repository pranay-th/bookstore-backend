"""
coupons/services.py

Shared coupon validation used by both the public validate endpoint and the
checkout / order-creation flow, so the rules live in exactly one place and
the discount applied to the charge is always re-derived server-side.
"""
from decimal import Decimal

from django.utils import timezone

from .models import Coupon


class CouponError(Exception):
    """Raised when a coupon is invalid for the given order total."""


def validate_coupon(code: str, order_total) -> tuple[Coupon, Decimal]:
    """
    Validate ``code`` against ``order_total`` and return (coupon, discount_amount).

    Raises CouponError(message) if the coupon is missing, inactive, expired,
    fully redeemed, or the order does not meet the minimum.
    """
    if not code:
        raise CouponError("Please enter a coupon code.")

    order_total = Decimal(str(order_total))
    normalized = code.strip()

    try:
        coupon = Coupon.objects.get(code__iexact=normalized, is_active=True)
    except Coupon.DoesNotExist:
        raise CouponError("Invalid coupon code.")

    now = timezone.now()
    if coupon.valid_from and now < coupon.valid_from:
        raise CouponError("This coupon is not yet active.")
    if coupon.valid_until and now > coupon.valid_until:
        raise CouponError("This coupon has expired.")
    if coupon.max_uses and coupon.used_count >= coupon.max_uses:
        raise CouponError("This coupon has been fully redeemed.")
    if order_total < coupon.min_order:
        raise CouponError(
            f"Minimum order of ₹{coupon.min_order} required for this coupon."
        )

    if coupon.discount_type == "percentage":
        discount_amount = round(order_total * coupon.discount_value / Decimal("100"), 2)
    else:  # fixed
        discount_amount = min(coupon.discount_value, order_total)

    return coupon, discount_amount
