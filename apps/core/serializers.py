"""
core/serializers.py
Placeholder base serializers.
TODO: Add shared mixin fields (e.g., created_at formatting).
"""
from rest_framework import serializers


class BaseModelSerializer(serializers.ModelSerializer):
    """Base serializer — add shared read-only fields here."""
    # TODO: Add created_at, updated_at as formatted read-only fields
    pass
