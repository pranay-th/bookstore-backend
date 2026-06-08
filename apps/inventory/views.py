"""inventory/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import InventoryItem
from .serializers import InventoryItemSerializer

class InventoryItemViewSet(viewsets.ModelViewSet):
    # TODO: Restrict to admin/staff only
    # TODO: Add bulk update action for restocking
    queryset         = InventoryItem.objects.select_related('book')
    serializer_class = InventoryItemSerializer
