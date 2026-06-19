from rest_framework import serializers
from .models import Order, OrderItem, OrderDelivery


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()
    book_title = serializers.CharField(source='book.title', read_only=True)
    book_author = serializers.CharField(source='book.author', read_only=True)
    # Current stock for the book, so the delivery bot can detect backorders
    # when classifying an order.
    book_stock = serializers.IntegerField(source='book.stock', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'book', 'book_title', 'book_author', 'book_stock',
            'quantity', 'unit_price', 'subtotal',
        ]


class OrderDeliverySerializer(serializers.ModelSerializer):
    """Read/write serializer for an order's delivery details."""

    class Meta:
        model = OrderDelivery
        fields = [
            'full_name', 'email', 'phone',
            'line1', 'line2', 'city', 'state', 'postal_code', 'country',
            'notes',
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    delivery = OrderDeliverySerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total_amount', 'notes',
            'created_at', 'updated_at', 'items', 'delivery',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CheckoutItemSerializer(serializers.Serializer):
    """A single line item in the checkout payload."""
    book_id = serializers.CharField(max_length=36)
    quantity = serializers.IntegerField(min_value=1)


class DeliveryInputSerializer(serializers.Serializer):
    """Delivery contact + shipping address supplied at checkout."""
    full_name   = serializers.CharField(max_length=255)
    email       = serializers.EmailField()
    phone       = serializers.CharField(max_length=20, required=False, allow_blank=True)
    line1       = serializers.CharField(max_length=255)
    line2       = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city        = serializers.CharField(max_length=100)
    state       = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)
    country     = serializers.CharField(max_length=2, required=False, default='IN')
    notes       = serializers.CharField(required=False, allow_blank=True)


class CheckoutSerializer(serializers.Serializer):
    """
    Input for the checkout endpoint.

    Accepts the cart contents (book_id + quantity per item), an optional
    payment_method (cosmetic — no real payment is processed), and optional
    delivery details. Delivery is optional so existing programmatic callers
    (e.g. the AI assistant) keep working; the storefront always sends it.
    """
    items = CheckoutItemSerializer(many=True, allow_empty=False)
    payment_method = serializers.ChoiceField(
        choices=['card', 'paypal', 'bank_transfer'],
        default='card',
        required=False,
    )
    delivery = DeliveryInputSerializer(required=False)
