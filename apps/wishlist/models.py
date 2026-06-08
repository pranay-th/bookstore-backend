"""
wishlist/models.py — Phase 0 placeholder.
TODO: Implement Wishlist with named lists and book sharing.
"""
import uuid
from django.db import models
from django.conf import settings


class Wishlist(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlists')
    name       = models.CharField(max_length=200, default='My Wishlist')
    is_public  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # TODO: Add share_token for public sharing

    class Meta:
        db_table = 'wishlists'

    def __str__(self):
        return f'{self.name} ({self.user.email})'


class WishlistItem(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist   = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    book       = models.ForeignKey('books.Book', on_delete=models.CASCADE)
    added_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wishlist_items'
        unique_together = ('wishlist', 'book')
