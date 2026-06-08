"""wishlist/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Wishlist, WishlistItem
from .serializers import WishlistSerializer, WishlistItemSerializer

class WishlistViewSet(viewsets.ModelViewSet):
    # TODO: Restrict to the authenticated user's wishlists
    queryset         = Wishlist.objects.prefetch_related('items__book')
    serializer_class = WishlistSerializer

class WishlistItemViewSet(viewsets.ModelViewSet):
    queryset         = WishlistItem.objects.select_related('book')
    serializer_class = WishlistItemSerializer
