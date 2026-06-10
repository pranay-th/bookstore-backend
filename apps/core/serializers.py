"""
core/serializers.py

Shared serializers including:
- BaseModelSerializer       : common base for model serializers.
- StatusObjectSerializer    : schema for the nested `status` object.
- SuccessResponseSerializer : schema for successful API envelopes.
- ErrorResponseSerializer   : schema for error API envelopes.

Every response follows the same shape:
    {
        "status": { "success": true|false, "code": <int>, "message": "<str>" },
        "data":   { ... } | null
    }
"""
from rest_framework import serializers


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseModelSerializer(serializers.ModelSerializer):
    """Base serializer — add shared read-only fields here."""
    pass


# ---------------------------------------------------------------------------
# Nested status object
# ---------------------------------------------------------------------------

class StatusObjectSerializer(serializers.Serializer):
    """
    The nested `status` object present in every response.

        {
            "success": true | false,
            "code":    200,
            "message": "Login successful."
        }
    """
    success = serializers.BooleanField(
        help_text="true for 2xx responses, false for 4xx/5xx.",
    )
    code = serializers.IntegerField(
        help_text="Mirrors the HTTP status code.",
    )
    message = serializers.CharField(
        help_text="Human-readable description of the result or error.",
    )


# ---------------------------------------------------------------------------
# Envelope schemas  (used by drf-spectacular @extend_schema responses=...)
# ---------------------------------------------------------------------------

class SuccessResponseSerializer(serializers.Serializer):
    """
    Schema for a successful API response envelope.

    Shape::

        {
            "status": { "success": true, "code": 200, "message": "Login successful." },
            "data":   { ... } | null
        }
    """
    status = StatusObjectSerializer()
    data = serializers.JSONField(
        allow_null=True,
        help_text="Response payload. null when there is no data to return.",
    )


class ErrorResponseSerializer(serializers.Serializer):
    """
    Schema for an error API response envelope.

    Shape::

        {
            "status": { "success": false, "code": 400, "message": "Invalid credentials." },
            "data":   null
        }
    """
    status = StatusObjectSerializer()
    data = serializers.JSONField(
        allow_null=True,
        default=None,
        help_text="Always null for error responses.",
    )
