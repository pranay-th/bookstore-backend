"""
books/serializers.py
"""
from rest_framework import serializers
from .models import Book


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "isbn",
            "description",
            "cover_url",
            "published_year",
            "language",
            "price",
            "stock",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
