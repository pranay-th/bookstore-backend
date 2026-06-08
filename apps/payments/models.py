"""
payments/models.py — Phase 0 placeholder.
TODO: Integrate with Stripe / PayPal; store payment intent IDs, not card details.
"""
import uuid
from django.db import models
from django.conf import settings


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    METHOD_CHOICES = [
        ('card',         'Credit/Debit Card'),
        ('paypal',       'PayPal'),
        ('bank_transfer','Bank Transfer'),
    ]

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order            = models.OneToOneField('orders.Order', on_delete=models.CASCADE, related_name='payment')
    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount           = models.DecimalField(max_digits=12, decimal_places=2)
    currency         = models.CharField(max_length=3, default='USD')
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    method           = models.CharField(max_length=20, choices=METHOD_CHOICES)
    gateway_ref      = models.CharField(max_length=255, blank=True, help_text='Payment gateway transaction ID')
    # TODO: Add refund_amount field
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f'Payment {self.id} — {self.status}'
