"""
books/author_serializers.py

Serializers used by the author studio (author-scoped catalogue management).

These are distinct from the public BookSerializer:
  - AuthorBookSerializer    : a book as the owning author sees it, with
                              computed sales/revenue/rating annotations.
  - AuthorBookWriteSerializer: create/update payload for an author's own book.
"""
from rest_framework import serializers

from .models import Book


class AuthorBookSerializer(serializers.ModelSerializer):
    """Read serializer for an author's own book, with performance metrics.

    The `units_sold`, `revenue` and `avg_rating` / `review_count` values are
    expected to be annotated onto the queryset by the view. They default to 0
    when absent so the serializer is safe to use on un-annotated instances.
    """

    units_sold = serializers.SerializerMethodField()
    revenue = serializers.SerializerMethodField()
    avg_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

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
            "units_sold",
            "revenue",
            "avg_rating",
            "review_count",
        ]
        read_only_fields = fields

    def get_units_sold(self, obj):
        return int(getattr(obj, "units_sold", 0) or 0)

    def get_revenue(self, obj):
        return float(getattr(obj, "revenue", 0) or 0)

    def get_avg_rating(self, obj):
        value = getattr(obj, "avg_rating", None)
        return round(float(value), 1) if value is not None else None

    def get_review_count(self, obj):
        return int(getattr(obj, "review_count", 0) or 0)


class AuthorBookWriteSerializer(serializers.ModelSerializer):
    """Create/update serializer for an author's own book.

    `author`, `is_active` and `owner` are managed by the view, not the client:
    `author` defaults to the owner's display name, `owner` is always the
    request user, and `is_active` is controlled via the publish/unpublish
    actions.
    """

    class Meta:
        model = Book
        fields = [
            "title",
            "author",
            "isbn",
            "description",
            "cover_url",
            "published_year",
            "language",
            "price",
            "stock",
        ]
        extra_kwargs = {
            "author": {"required": False},
            "isbn": {"required": False},
            "description": {"required": False},
            "cover_url": {"required": False},
            "published_year": {"required": False},
            "language": {"required": False},
            "stock": {"required": False},
        }

    def validate_price(self, value):
        if value is None or value < 0:
            raise serializers.ValidationError("Price must be zero or greater.")
        return value
