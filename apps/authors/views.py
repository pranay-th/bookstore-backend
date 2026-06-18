"""
authors/views.py

Endpoints:
  GET /api/authors/                List all authors (extracted from books)
  GET /api/authors/<name>/books/   Get books by a specific author
"""
import logging
from urllib.parse import quote

import httpx
from django.core.cache import cache
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

OL_AUTHOR_SEARCH_URL = "https://openlibrary.org/search/authors.json"
# Cache resolved Open Library images for a week. We store "" to remember a
# negative result (no author / no photo) so we don't hammer the API.
_OL_IMAGE_CACHE_TTL = 60 * 60 * 24 * 7


def build_author_image(name):
    """Build a deterministic avatar URL for an author name.

    Used as a fallback when no real Open Library photo is available, so the UI
    always has something to show. The background colour is derived from the
    name, so the avatar is stable between requests.
    """
    encoded = quote(name or "Author")
    return (
        f"https://ui-avatars.com/api/?name={encoded}"
        "&size=256&background=random&bold=true&format=png"
    )


def resolve_openlibrary_author_image(name):
    """Resolve an author's real photo URL from Open Library, or None.

    Looks the author up by name via the Open Library author search, picks the
    match with the most works (most likely the real author), and builds the
    cover URL. ``?default=false`` makes the cover endpoint return 404 when the
    author has no photo, so the client can fall back to a generated avatar.

    Results (including misses) are cached to avoid repeated external calls.
    """
    name = (name or "").strip()
    if not name:
        return None

    cache_key = f"author_ol_image:{name.lower()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached or None  # "" means "looked up, no photo"

    image = None
    try:
        resp = httpx.get(
            OL_AUTHOR_SEARCH_URL,
            params={"q": name, "limit": 5},
            timeout=6,
        )
        resp.raise_for_status()
        docs = [d for d in (resp.json().get("docs") or []) if d.get("key")]
        if docs:
            best = max(docs, key=lambda d: d.get("work_count") or 0)
            olid = best["key"]
            image = (
                f"https://covers.openlibrary.org/a/olid/{olid}-M.jpg?default=false"
            )
    except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
        logger.warning("Open Library image lookup failed for %r: %s", name, exc)

    cache.set(cache_key, image or "", _OL_IMAGE_CACHE_TTL)
    return image


def build_author_bio(name, books):
    """Compose an "about the author" summary from their actual catalogue.

    We have no real biography data, so we describe the author using facts we do
    have: how many books they have, the years they span, and the languages.
    """
    count = len(books)
    if count == 0:
        return f"{name} does not have any books in our catalogue yet."

    years = sorted(b.published_year for b in books if b.published_year)
    languages = sorted({b.language for b in books if b.language})

    book_word = "book" if count == 1 else "books"
    parts = [f"{name} has {count} {book_word} in our catalogue"]

    if years:
        if years[0] == years[-1]:
            parts.append(f"published in {years[0]}")
        else:
            parts.append(f"published between {years[0]} and {years[-1]}")

    sentence = " ".join(parts) + "."

    if languages:
        lang_list = ", ".join(languages[:5])
        sentence += f" Their work is available in: {lang_list}."

    return sentence


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
                            {"name": "J.K. Rowling", "book_count": 12, "image": "https://ui-avatars.com/api/?name=J.K.%20Rowling"},
                            {"name": "Stephen King", "book_count": 8, "image": "https://ui-avatars.com/api/?name=Stephen%20King"},
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
        {
            "name": entry["trimmed_author"],
            "book_count": entry["book_count"],
            "image": build_author_image(entry["trimmed_author"]),
        }
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
                            "author": {
                                "name": "J.K. Rowling",
                                "image": "https://ui-avatars.com/api/?name=J.K.%20Rowling",
                                "bio": "J.K. Rowling has 12 books in our catalogue published between 1997 and 2016.",
                                "book_count": 12,
                            },
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
    """Get all books by a specific author, plus author image and bio."""
    books = list(
        Book.objects.filter(
            is_active=True,
            author__icontains=author_name,
        )
    )

    serializer = BookSerializer(books, many=True)
    return success_response(
        data={
            "author": {
                "name": author_name,
                "image": (
                    resolve_openlibrary_author_image(author_name)
                    or build_author_image(author_name)
                ),
                "bio": build_author_bio(author_name, books),
                "book_count": len(books),
            },
            "books": serializer.data,
        },
        message=f"Books by {author_name} retrieved.",
    )


@extend_schema(
    summary="Resolve an author's photo",
    description=(
        "Returns the best available image URL for an author name.\n\n"
        "Tries to find a real author photo on Open Library; if none exists, "
        "falls back to a generated initials avatar. Designed to be called "
        "lazily per author card so the authors list stays fast."
    ),
    parameters=[
        OpenApiParameter(
            name="name",
            description="Author name to resolve an image for",
            required=True,
            type=str,
        ),
    ],
    responses={
        200: OpenApiResponse(
            response=SuccessResponseSerializer,
            description="Resolved author image",
            examples=[
                OpenApiExample(
                    "Author image",
                    value={
                        "status": {"success": True, "message": "Author image resolved."},
                        "data": {
                            "name": "J. K. Rowling",
                            "image": "https://covers.openlibrary.org/a/olid/OL23919A-M.jpg?default=false",
                            "source": "openlibrary",
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
def author_image(request):
    """Resolve a single author's photo (Open Library, with avatar fallback)."""
    name = request.query_params.get("name", "").strip()

    ol_image = resolve_openlibrary_author_image(name)
    return success_response(
        data={
            "name": name,
            "image": ol_image or build_author_image(name),
            "source": "openlibrary" if ol_image else "avatar",
        },
        message="Author image resolved.",
    )
