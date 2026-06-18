from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.CharField(source='book.author', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'book', 'book_title', 'book_author',
            'quantity', 'unit_price', 'subtotal',
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total_amount', 'notes',
            'created_at', 'updated_at', 'items',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CheckoutItemSerializer(serializers.Serializer):
    """A single line item in the checkout payload."""
    book_id = serializers.CharField(max_length=36)
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    """
    Input for the checkout endpoint.

    Accepts the cart contents (book_id + quantity per item) and an optional
    payment_method (purely cosmetic — no real payment is processed).
    """
    items = CheckoutItemSerializer(many=True, allow_empty=False)
    payment_method = serializers.ChoiceField(
        choices=['card', 'paypal', 'bank_transfer'],
        default='card',
        required=False,
    )
