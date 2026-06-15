"""
authors/views.py

Endpoints:
  GET /api/authors/                List all authors (extracted from books)
  GET /api/authors/<name>/books/   Get books by a specific author
"""
import logging

from django.db.models import Count
from django.db.models.functions import Trim
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from apps.books.models import Book
from apps.books.serializers import BookSerializer
from apps.core.responses import success_response
from apps.core.serializers import SuccessResponseSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    summary="List all authors",
    description=(
        "Returns a list of unique authors extracted from the books catalog.\n\n"
        "Each entry includes the author name and the number of books they have.\n\n"
        "Supports `?search=` to filter by author name."
    ),
    parameters=[
        OpenApiParameter(
            name="search",
            description="Filter authors by name (case-insensitive)",
            required=False,
            type=str,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=SuccessResponseSerializer,
            description="List of authors",
            examples=[
                OpenApiExample(
                    "Authors list",
                    value={
                        "status": {
                            "success": True,
                            "message": "Authors retrieved.",
                        },
                        "data": [
                            {"name": "J.K. Rowling", "book_count": 12},
                            {"name": "Stephen King", "book_count": 8},
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def list_authors(request):
    """List unique authors with their book count."""
    search = request.query_params.get("search", "").strip()

    queryset = (
        Book.objects.filter(is_active=True)
        .exclude(author="")
        .annotate(trimmed_author=Trim("author"))
        .values("trimmed_author")
        .annotate(book_count=Count("id"))
        .order_by("-book_count")
    )

    if search:
        queryset = queryset.filter(trimmed_author__icontains=search)

    authors = [
        {"name": entry["trimmed_author"], "book_count": entry["book_count"]}
        for entry in queryset[:200]  # Cap at 200 for performance
    ]

    return success_response(data=authors, message="Authors retrieved.")


@extend_schema(
    summary="Get books by author",
    description="Returns all active books by a specific author name.",
    parameters=[
        OpenApiParameter(
            name="author_name",
            description="Exact or partial author name",
            required=True,
            type=str,
            location=OpenApiParameter.PATH,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=SuccessResponseSerializer,
            description="Books by author",
            examples=[
                OpenApiExample(
                    "Author books",
                    value={
                        "status": {
                            "success": True,
                            "message": "Books by J.K. Rowling retrieved.",
                        },
                        "data": {
                            "author": "J.K. Rowling",
                            "books": [
                                {
                                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                    "title": "Harry Potter",
                                    "price": "499.00",
                                    "cover_url": "https://...",
                                }
                            ],
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def author_books(request, author_name):
    """Get all books by a specific author."""
    books = Book.objects.filter(
        is_active=True,
        author__icontains=author_name,
    )

    serializer = BookSerializer(books, many=True)
    return success_response(
        data={
            "author": author_name,
            "books": serializer.data,
        },
        message=f"Books by {author_name} retrieved.",
    )
