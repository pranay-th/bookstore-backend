"""
coupons/models.py — Phase 0 placeholder.
TODO: Implement percentage/fixed discount, usage limits, expiry, min order amount.
"""
import uuid
from django.db import models


class Coupon(models.Model):
    DISCOUNT_TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed',      'Fixed Amount'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code           = models.CharField(max_length=50, unique=True)
    discount_type  = models.CharField(max_length=20, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    min_order      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses       = models.PositiveIntegerField(null=True, blank=True)
    used_count     = models.PositiveIntegerField(default=0)
    is_active      = models.BooleanField(default=True)
    valid_from     = models.DateTimeField()
    valid_until    = models.DateTimeField(null=True, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coupons'

    def __str__(self):
        return self.code
