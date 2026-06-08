from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    # TODO: Add user full_name as read-only field
    class Meta:
        model  = Review
        fields = '__all__'
