"""orders/views.py — Phase 0 placeholder."""
import logging

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.core.events import ORDER_CREATED, publish_event

from .models import Order
from .serializers import OrderSerializer

logger = logging.getLogger(__name__)


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
        order = serializer.save(user=self.request.user)
        # Notify the analytics microservice (fire-and-forget, fails open).
        publish_event(
            ORDER_CREATED,
            {
                "order_id": str(order.id),
                "user_id": str(self.request.user.id),
                "total_amount": str(order.total_amount),
                "status": order.status,
                "item_count": order.items.count(),
            },
        )
