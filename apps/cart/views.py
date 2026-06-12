"""cart/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer


class CartViewSet(viewsets.ModelViewSet):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only ever expose the authenticated user's own cart
        return Cart.objects.filter(user=self.request.user).prefetch_related('items__book')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only items belonging to the authenticated user's cart
        # TODO: Validate quantity against inventory before adding
        return CartItem.objects.filter(
            cart__user=self.request.user
        ).select_related('book')
