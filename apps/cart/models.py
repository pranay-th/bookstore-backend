"""
cart/models.py

A per-user shopping cart and its line items.

Each user has exactly one Cart (OneToOne). A CartItem links a Book to that
cart with a quantity and a unit_price snapshot captured at the time the book
was first added, so later price changes don't silently alter an active cart.
"""
import uuid
from decimal import Decimal

from django.db import models
from django.conf import settings


class Cart(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # TODO: Add coupon FK once coupons app is implemented

    class Meta:
        db_table = 'carts'

    def __str__(self):
        return f'Cart of {self.user.email}'

    @property
    def total_quantity(self) -> int:
        """Total number of book copies across all items."""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self) -> Decimal:
        """Sum of every line item's subtotal."""
        return sum((item.subtotal for item in self.items.all()), Decimal('0.00'))


class CartItem(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart       = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    book       = models.ForeignKey('books.Book', on_delete=models.CASCADE)
    quantity   = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Price of the book captured when first added to the cart.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_items'
        unique_together = ('cart', 'book')
        ordering = ['created_at', 'id']

    def __str__(self):
        return f'{self.quantity}x {self.book.title}'

    @property
    def subtotal(self) -> Decimal:
        """unit_price * quantity for this line item."""
        return self.unit_price * self.quantity
