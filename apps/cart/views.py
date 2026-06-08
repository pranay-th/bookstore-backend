"""cart/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class CartViewSet(viewsets.ModelViewSet):
    # TODO: Restrict to the authenticated user's cart
    queryset         = Cart.objects.prefetch_related('items__book')
    serializer_class = CartSerializer


class CartItemViewSet(viewsets.ModelViewSet):
    # TODO: Validate quantity against inventory before adding
    queryset         = CartItem.objects.select_related('book')
    serializer_class = CartItemSerializer
