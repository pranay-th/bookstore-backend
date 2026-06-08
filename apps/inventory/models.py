"""
inventory/models.py — Phase 0 placeholder.
TODO: Implement stock tracking, warehouse location, reorder levels.
"""
import uuid
from django.db import models


class InventoryItem(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book          = models.OneToOneField('books.Book', on_delete=models.CASCADE, related_name='inventory')
    quantity      = models.PositiveIntegerField(default=0)
    reserved      = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    # TODO: Add warehouse / location FK
    # TODO: Add last_restocked_at timestamp
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_items'

    def __str__(self):
        return f'Inventory: {self.book.title} ({self.quantity} in stock)'

    @property
    def available_quantity(self):
        return max(0, self.quantity - self.reserved)
