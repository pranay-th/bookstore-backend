"""
apps/core/views.py

Core utility views.
"""
import logging

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class HealthResponseSerializer(serializers.Serializer):
    """Schema for the health check response."""
    status = serializers.CharField()


@extend_schema(
    summary="Health check",
    description=(
        "Returns `{\"status\": \"ok\"}` when the service is running.\n\n"
        "Used by Render's health probe — must return 200 to keep the service live."
    ),
    responses={
        200: OpenApiResponse(
            response=HealthResponseSerializer,
            description="Service is healthy",
            examples=[
                OpenApiExample(
                    "Healthy",
                    value={"status": "ok"},
                    response_only=True,
                ),
            ],
        ),
    },
    tags=["Health"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    GET /health/
    Returns 200 OK — used by Render health probes.
    """
    logger.debug("Health check called")
    return Response({"status": "ok"})
