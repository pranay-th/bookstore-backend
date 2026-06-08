"""coupons/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Coupon
from .serializers import CouponSerializer

class CouponViewSet(viewsets.ModelViewSet):
    # TODO: Add validate action: POST /coupons/validate/ {code, order_total}
    # TODO: Restrict list/create/update to admin only
    queryset         = Coupon.objects.filter(is_active=True)
    serializer_class = CouponSerializer
