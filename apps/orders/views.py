"""orders/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Order
from .serializers import OrderSerializer


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Only orders owned by the authenticated user
        # TODO: Add cancel action (PATCH /orders/:id/cancel/)
        # TODO: Integrate with payments and inventory on order create
        return Order.objects.filter(
            user=self.request.user
        ).prefetch_related('items__book')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
