from rest_framework import serializers
from .models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """Read serializer — never exposes the key secret, only Razorpay refs."""
    order_id = serializers.UUIDField(source='order.id', read_only=True)
    order_status = serializers.CharField(source='order.status', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'order_id', 'order_status', 'amount', 'currency', 'status',
            'razorpay_order_id', 'razorpay_payment_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class CreateOrderSerializer(serializers.Serializer):
    """
    Input for create-order. Accepts the cart contents; the amount is computed
    server-side from the books, never trusted from the client. An optional
    coupon code is re-validated server-side before any discount is applied.
    """
    items = serializers.ListField(
        child=serializers.DictField(), allow_empty=False
    )
    coupon_code = serializers.CharField(
        required=False, allow_blank=True, max_length=50
    )

    def validate_items(self, value):
        cleaned = []
        for item in value:
            book_id = item.get('book_id')
            quantity = item.get('quantity', 1)
            if not book_id:
                raise serializers.ValidationError("Each item needs a book_id.")
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                raise serializers.ValidationError("Quantity must be an integer.")
            if quantity < 1:
                raise serializers.ValidationError("Quantity must be at least 1.")
            cleaned.append({'book_id': str(book_id), 'quantity': quantity})
        return cleaned


class VerifyPaymentSerializer(serializers.Serializer):
    """Input for the verify endpoint — the three values Razorpay returns."""
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
