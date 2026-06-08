"""
users/serializers.py — Phase 0 placeholders.
TODO: Implement full CRUD serializers in Phase 1.
"""
from rest_framework import serializers
from .models import User, UserProfile, UserAddress


class UserAddressSerializer(serializers.ModelSerializer):
    # TODO: Add validation for country ISO code
    class Meta:
        model  = UserAddress
        fields = '__all__'


class UserProfileSerializer(serializers.ModelSerializer):
    # TODO: Add nested address serializer
    class Meta:
        model  = UserProfile
        fields = '__all__'


class UserSerializer(serializers.ModelSerializer):
    profile   = UserProfileSerializer(read_only=True)
    addresses = UserAddressSerializer(many=True, read_only=True)

    # TODO: Add write methods for creating profile on user create
    class Meta:
        model  = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'date_joined', 'profile', 'addresses']
        read_only_fields = ['id', 'date_joined']
