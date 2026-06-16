"""
books/views.py

All data served from PostgreSQL — no external API calls at runtime.

Endpoints:
  GET    /api/books/              List books (with ?search= filter)
  GET    /api/books/<id>/         Book detail
  POST   /api/books/              Add a book (admin)
  PATCH  /api/books/<id>/         Update a book (admin)
  DELETE /api/books/<id>/         Soft-delete a book (admin)
"""
import logging

from django.db.models import Q
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.viewsets import ModelViewSet

from apps.core.responses import success_response
from apps.core.serializers import SuccessResponseSerializer, ErrorResponseSerializer
from apps.core.pagination import StandardResultsSetPagination

from .models import Book
from .serializers import BookSerializer

logger = logging.getLogger(__name__)


class BookViewSet(ModelViewSet):
    serializer_class = BookSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdminUser()]
        return [AllowAny()]

    def get_queryset(self):
        queryset = Book.objects.filter(is_active=True)
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(author__icontains=search)
                | Q(subjects__icontains=search)
            )
        # Filter by category/subject (e.g. ?category=fantasy). Matches against
        # the comma-separated `subjects` field populated from Open Library.
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(subjects__icontains=category)
        return queryset

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------
    @extend_schema(
        summary="List all books",
        description=(
            "Returns active books from the database, paginated.\n\n"
            "Supports `?search=` to filter by title or author and "
            "`?page=` / `?page_size=` for pagination."
        ),
        parameters=[
            OpenApiParameter(
                name="search",
                description="Search by title or author (case-insensitive)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="category",
                description="Filter by subject/category (e.g. fantasy, history)",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="page",
                description="Page number (default 1)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="page_size",
                description="Results per page (default 20, max 100)",
                required=False,
                type=int,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Paginated list of books",
                examples=[
                    OpenApiExample(
                        "Books list",
                        value={
                            "status": {
                                "success": True,
                                "message": "Books retrieved.",
                            },
                            "data": {
                                "results": [
                                    {
                                        "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                        "title": "Harry Potter and the Philosopher's Stone",
                                        "author": "J.K. Rowling",
                                        "isbn": "9780747532699",
                                        "description": "A young wizard's journey begins.",
                                        "cover_url": "https://covers.openlibrary.org/b/id/10110415-M.jpg",
                                        "published_year": 1997,
                                        "language": "English",
                                        "price": "499.00",
                                        "stock": 50,
                                        "is_active": True,
                                        "created_at": "2026-06-12T10:00:00Z",
                                    }
                                ],
                                "count": 10000,
                                "num_pages": 500,
                                "current_page": 1,
                                "page_size": 20,
                                "has_next": True,
                                "has_previous": False,
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = BookSerializer(page, many=True)
        payload = {
            "results": serializer.data,
            "count": paginator.page.paginator.count,
            "num_pages": paginator.page.paginator.num_pages,
            "current_page": paginator.page.number,
            "page_size": paginator.get_page_size(request),
            "has_next": paginator.page.has_next(),
            "has_previous": paginator.page.has_previous(),
        }
        return success_response(data=payload, message="Books retrieved.")

    # ------------------------------------------------------------------
    # RETRIEVE
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Get book details",
        description="Returns full book detail from the database.",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Book detail",
                examples=[
                    OpenApiExample(
                        "Book detail",
                        value={
                            "status": {
                                "success": True,
                                "message": "Book details retrieved.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "title": "Harry Potter and the Philosopher's Stone",
                                "author": "J.K. Rowling",
                                "isbn": "9780747532699",
                                "description": "A young wizard's journey begins.",
                                "cover_url": "https://covers.openlibrary.org/b/id/10110415-M.jpg",
                                "published_year": 1997,
                                "language": "English",
                                "price": "499.00",
                                "stock": 50,
                                "is_active": True,
                                "created_at": "2026-06-12T10:00:00Z",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            404: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Book not found",
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
        book = self.get_object()
        serializer = BookSerializer(book)
        return success_response(data=serializer.data, message="Book details retrieved.")

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Add a book",
        description="Add a new book to the store (admin only).",
        request=BookSerializer,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Book created",
                examples=[
                    OpenApiExample(
                        "Book created",
                        value={
                            "status": {
                                "success": True,
                                "message": "Book added to store.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "title": "Harry Potter and the Philosopher's Stone",
                                "author": "J.K. Rowling",
                                "isbn": "9780747532699",
                                "description": "A young wizard's journey begins.",
                                "cover_url": "https://covers.openlibrary.org/b/id/10110415-M.jpg",
                                "published_year": 1997,
                                "language": "English",
                                "price": "499.00",
                                "stock": 50,
                                "is_active": True,
                                "created_at": "2026-06-12T10:00:00Z",
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
                                "message": "title: This field is required.",
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
                "Add a book",
                value={
                    "title": "Harry Potter and the Philosopher's Stone",
                    "author": "J.K. Rowling",
                    "isbn": "9780747532699",
                    "description": "A young wizard's journey begins.",
                    "cover_url": "https://covers.openlibrary.org/b/id/10110415-M.jpg",
                    "published_year": 1997,
                    "language": "English",
                    "price": "499.00",
                    "stock": 50,
                },
                request_only=True,
            ),
        ],
    )
    def create(self, request, *args, **kwargs):
        serializer = BookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(
            data=serializer.data,
            message="Book added to store.",
            status_code=201,
        )

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Update a book",
        description="Update book fields (admin only). Partial updates supported.",
        request=BookSerializer,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Book updated",
                examples=[
                    OpenApiExample(
                        "Book updated",
                        value={
                            "status": {
                                "success": True,
                                "message": "Book updated.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "title": "Harry Potter and the Philosopher's Stone",
                                "author": "J.K. Rowling",
                                "isbn": "9780747532699",
                                "price": "399.00",
                                "stock": 100,
                                "is_active": True,
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        book = self.get_object()
        serializer = BookSerializer(book, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Book updated.")

    # ------------------------------------------------------------------
    # DESTROY (soft delete)
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Remove a book (soft delete)",
        description="Sets `is_active` to False. The book won't appear in listings.",
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Book removed",
                examples=[
                    OpenApiExample(
                        "Book removed",
                        value={
                            "status": {
                                "success": True,
                                "message": "Book removed from store.",
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
        book = self.get_object()
        book.is_active = False
        book.save(update_fields=["is_active"])
        return success_response(message="Book removed from store.")
