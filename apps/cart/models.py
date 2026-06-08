"""
cart/models.py — Phase 0 placeholder.
TODO: Implement Cart and CartItem with quantity, subtotal, coupon application.
"""
import uuid
from django.db import models
from django.conf import settings


class Cart(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # TODO: Add coupon FK once coupons app is implemented

    class Meta:
        db_table = 'carts'

    def __str__(self):
        return f'Cart of {self.user.email}'


class CartItem(models.Model):
    id       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart     = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    book     = models.ForeignKey('books.Book', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    # TODO: Add unit_price snapshot at time of adding to cart

    class Meta:
        db_table = 'cart_items'
        unique_together = ('cart', 'book')

    def __str__(self):
        return f'{self.quantity}x {self.book.title}'
