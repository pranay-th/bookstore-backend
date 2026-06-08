from rest_framework import serializers
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    # TODO: Add book title, cover, price as nested read-only fields
    class Meta:
        model  = CartItem
        fields = '__all__'


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    # TODO: Add computed total field
    class Meta:
        model  = Cart
        fields = '__all__'
