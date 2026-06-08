from django.contrib import admin
from .models import InventoryItem

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display  = ('book', 'quantity', 'reserved', 'available_quantity', 'reorder_level')
    search_fields = ('book__title',)
