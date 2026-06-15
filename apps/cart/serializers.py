"""
cart/serializers.py

Serializers for the shopping cart.

  CartItemSerializer  — a single line item with nested read-only book detail
                        and a computed subtotal.
  CartSerializer      — the full cart with nested items and computed totals.
  AddToCartSerializer — write-only input for adding/incrementing an item.
  UpdateQuantitySerializer — write-only input for setting an item's quantity.
"""
from rest_framework import serializers

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """Read serializer for a cart line item."""
    book_id    = serializers.UUIDField(source='book.id', read_only=True)
    title      = serializers.CharField(source='book.title', read_only=True)
    author     = serializers.CharField(source='book.author', read_only=True)
    cover_url  = serializers.CharField(source='book.cover_url', read_only=True)
    price      = serializers.DecimalField(
        source='book.price', max_digits=10, decimal_places=2, read_only=True
    )
    stock      = serializers.IntegerField(source='book.stock', read_only=True)
    subtotal   = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id',
            'book_id',
            'title',
            'author',
            'cover_url',
            'price',
            'stock',
            'quantity',
            'unit_price',
            'subtotal',
            'created_at',
        ]
        read_only_fields = ['id', 'unit_price', 'created_at']


class CartSerializer(serializers.ModelSerializer):
    """Read serializer for the whole cart."""
    items          = CartItemSerializer(many=True, read_only=True)
    total_quantity = serializers.IntegerField(read_only=True)
    total_price    = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = [
            'id',
            'items',
            'total_quantity',
            'total_price',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class AddToCartSerializer(serializers.Serializer):
    """Input for adding a book to the cart (or incrementing if already present)."""
    book_id  = serializers.UUIDField(help_text="ID of the book to add.")
    quantity = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        help_text="How many copies to add. Defaults to 1.",
    )


class UpdateQuantitySerializer(serializers.Serializer):
    """Input for setting a cart item's quantity to an absolute value."""
    quantity = serializers.IntegerField(
        min_value=1,
        help_text="The new absolute quantity for this item (minimum 1).",
    )
