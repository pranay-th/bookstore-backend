"""
payments/models.py — Razorpay payment records.

Each Payment is tied OneToOne to a bookstore Order. The lifecycle mirrors
Razorpay's:

    created   → Razorpay order created, awaiting checkout
    paid      → payment captured and signature verified
    failed    → payment attempted but failed / signature mismatch

The signature (razorpay_signature) is stored only after a successful
server-side verification, which is also what flips the linked Order to
'confirmed'. The razorpay_order_id is unique to guard against duplicate
processing.
"""
import uuid
from django.db import models
from django.conf import settings


class Payment(models.Model):
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('paid',    'Paid'),
        ('failed',  'Failed'),
    ]

    id                 = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order              = models.OneToOneField(
        'orders.Order', on_delete=models.CASCADE, related_name='payment'
    )
    user               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount             = models.DecimalField(max_digits=12, decimal_places=2)
    currency           = models.CharField(max_length=3, default='INR')
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')

    # Razorpay identifiers
    razorpay_order_id   = models.CharField(max_length=255, unique=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, default='')
    razorpay_signature  = models.CharField(max_length=255, blank=True, default='')

    error_description  = models.TextField(blank=True, default='')
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment {self.id} — {self.status} ({self.razorpay_order_id})'
