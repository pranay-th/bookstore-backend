from rest_framework import serializers
from .models import Category

class CategorySerializer(serializers.ModelSerializer):
    # TODO: Add children serializer for nested category tree
    class Meta:
        model  = Category
        fields = '__all__'
