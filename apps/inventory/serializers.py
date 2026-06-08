from rest_framework import serializers
from .models import InventoryItem

class InventoryItemSerializer(serializers.ModelSerializer):
    available_quantity = serializers.ReadOnlyField()
    # TODO: Add book title as read-only nested field
    class Meta:
        model  = InventoryItem
        fields = '__all__'
