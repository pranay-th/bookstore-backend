"""
categories/views.py

Endpoints:
  GET    /api/categories/         List all active categories
  GET    /api/categories/<id>/    Category detail
  POST   /api/categories/         Create a category (admin)
  PATCH  /api/categories/<id>/    Update a category (admin)
  DELETE /api/categories/<id>/    Soft-delete a category (admin)
"""
import logging

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.viewsets import ModelViewSet

from apps.core.responses import success_response
from apps.core.serializers import ErrorResponseSerializer, SuccessResponseSerializer

from .models import Category
from .serializers import CategorySerializer

logger = logging.getLogger(__name__)


class CategoryViewSet(ModelViewSet):
    serializer_class = CategorySerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        return Category.objects.filter(is_active=True)

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------
    @extend_schema(
        summary="List all categories",
        description="Returns all active categories from the database.",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="List of categories",
                examples=[
                    OpenApiExample(
                        "Categories list",
                        value={
                            "status": {
                                "success": True,
                                "message": "Categories retrieved.",
                            },
                            "data": [
                                {
                                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                    "name": "Fiction",
                                    "slug": "fiction",
                                    "description": "Novels, short stories & literary works",
                                    "icon": "BookOpen",
                                    "parent": None,
                                    "is_active": True,
                                    "created_at": "2026-06-13T10:00:00Z",
                                }
                            ],
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = CategorySerializer(queryset, many=True)
        return success_response(data=serializer.data, message="Categories retrieved.")

    # ------------------------------------------------------------------
    # RETRIEVE
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Get category details",
        description="Returns full category detail from the database.",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Category detail",
                examples=[
                    OpenApiExample(
                        "Category detail",
                        value={
                            "status": {
                                "success": True,
                                "message": "Category details retrieved.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "name": "Fiction",
                                "slug": "fiction",
                                "description": "Novels, short stories & literary works",
                                "icon": "BookOpen",
                                "parent": None,
                                "is_active": True,
                                "created_at": "2026-06-13T10:00:00Z",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Category not found",
                examples=[
                    OpenApiExample(
                        "Not found",
                        value={
                            "status": {
                                "success": False,
                                "message": "Not found.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = CategorySerializer(category)
        return success_response(
            data=serializer.data, message="Category details retrieved."
        )

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Create a category",
        description="Add a new category (admin only).",
        request=CategorySerializer,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Category created",
                examples=[
                    OpenApiExample(
                        "Category created",
                        value={
                            "status": {
                                "success": True,
                                "message": "Category created.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "name": "Fiction",
                                "slug": "fiction",
                                "description": "Novels, short stories & literary works",
                                "icon": "BookOpen",
                                "parent": None,
                                "is_active": True,
                                "created_at": "2026-06-13T10:00:00Z",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error",
                examples=[
                    OpenApiExample(
                        "Validation error",
                        value={
                            "status": {
                                "success": False,
                                "message": "name: This field is required.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Create a category",
                value={
                    "name": "Fiction",
                    "description": "Novels, short stories & literary works",
                    "icon": "BookOpen",
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = CategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message="Category created.",
            status_code=201,
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Update a category",
        description="Update category fields (admin only). Partial updates supported.",
        request=CategorySerializer,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Category updated",
                examples=[
                    OpenApiExample(
                        "Category updated",
                        value={
                            "status": {
                                "success": True,
                                "message": "Category updated.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "name": "Fiction",
                                "slug": "fiction",
                                "description": "Updated description",
                                "icon": "BookOpen",
                                "parent": None,
                                "is_active": True,
                                "created_at": "2026-06-13T10:00:00Z",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        category = self.get_object()
        serializer = CategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Category updated.")

    # ------------------------------------------------------------------
    # DESTROY (soft delete)
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Remove a category (soft delete)",
        description="Sets `is_active` to False. The category won't appear in listings.",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Category removed",
                examples=[
                    OpenApiExample(
                        "Category removed",
                        value={
                            "status": {
                                "success": True,
                                "message": "Category removed.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def destroy(self, request, *args, **kwargs):
        category = self.get_object()
        category.is_active = False
        category.save(update_fields=["is_active"])
        return success_response(message="Category removed.")
