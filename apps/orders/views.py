"""orders/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Order
from .serializers import OrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    # TODO: Restrict to orders owned by the authenticated user
    # TODO: Add cancel action (PATCH /orders/:id/cancel/)
    # TODO: Integrate with payments and inventory on order create
    queryset         = Order.objects.prefetch_related('items__book')
    serializer_class = OrderSerializer
