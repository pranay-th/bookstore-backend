"""
orders/models.py — Phase 0 placeholder.
TODO: Implement full order lifecycle: pending → confirmed → shipped → delivered → cancelled.
"""
import uuid
from django.db import models
from django.conf import settings


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('confirmed',  'Confirmed'),
        ('failed',     'Failed'),
        ('processing', 'Processing'),
        ('shipped',    'Shipped'),
        ('delivered',  'Delivered'),
        ('cancelled',  'Cancelled'),
        ('refunded',   'Refunded'),
    ]

    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_amount   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon         = models.ForeignKey(
        'coupons.Coupon', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='orders',
    )
    shipping_address = models.ForeignKey(
        'users.UserAddress', null=True, blank=True, on_delete=models.SET_NULL, related_name='orders'
    )
    # TODO: Add tracking number field
    # TODO: Add shipped_at / delivered_at timestamps
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return f'Order {self.id} — {self.status}'


class OrderItem(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    book       = models.ForeignKey('books.Book', on_delete=models.CASCADE)
    quantity   = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'order_items'

    def __str__(self):
        return f'{self.quantity}x {self.book.title}'

    @property
    def subtotal(self):
        return self.quantity * self.unit_price


class OrderDelivery(models.Model):
    """Delivery contact + shipping address captured for a single order.

    Stored as a snapshot on the order (rather than only a FK to UserAddress)
    so the shipping details are preserved exactly as entered at checkout, even
    if the user later edits or deletes their saved address.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order       = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='delivery'
    )

    # Contact
    full_name   = models.CharField(max_length=255)
    email       = models.EmailField()
    phone       = models.CharField(max_length=20, blank=True)

    # Shipping address (snapshot)
    line1       = models.CharField(max_length=255)
    line2       = models.CharField(max_length=255, blank=True)
    city        = models.CharField(max_length=100)
    state       = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country     = models.CharField(max_length=2, default='IN', help_text='ISO 3166-1 alpha-2')

    notes       = models.TextField(blank=True, help_text='Delivery instructions')

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'order_deliveries'

    def __str__(self):
        return f'Delivery for order {self.order_id} → {self.full_name}, {self.city}'
