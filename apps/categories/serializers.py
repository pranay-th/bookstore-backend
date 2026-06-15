from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "parent",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "slug", "created_at"]
