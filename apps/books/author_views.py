"""
books/author_views.py

The author studio — author-scoped catalogue management.

Every endpoint here is scoped to request.user: an author can only ever see and
manage the books they own (Book.owner == request.user). Access is restricted to
users with the AUTHOR role (admins are also allowed).

Endpoints:
  GET    /api/author/books/                 List the author's own books (+ metrics)
  POST   /api/author/books/                 Publish a new book
  GET    /api/author/books/<id>/            Retrieve one of the author's books
  PATCH  /api/author/books/<id>/            Update one of the author's books
  DELETE /api/author/books/<id>/            Soft-delete (remove) the book
  POST   /api/author/books/<id>/publish/    Make the book live (is_active=True)
  POST   /api/author/books/<id>/unpublish/  Move the book to draft (is_active=False)
  GET    /api/author/stats/                 Aggregate performance stats
  GET    /api/author/reviews/               Recent reviews across the author's books
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from django.db.models import Avg, Count, DecimalField, F, Sum
from django.db.models.functions import Coalesce
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.viewsets import GenericViewSet, ViewSet

from apps.core import analytics_client
from apps.core.analytics_client import AnalyticsServiceError
from apps.core.pagination import StandardResultsSetPagination
from apps.core.responses import error_response, success_response
from apps.core.serializers import ErrorResponseSerializer, SuccessResponseSerializer

from .author_serializers import AuthorBookSerializer, AuthorBookWriteSerializer
from .models import Book

logger = logging.getLogger(__name__)


class IsAuthor(permissions.BasePermission):
    """Allow access only to authenticated users with the AUTHOR role.

    Admins (is_staff) are also permitted so support staff can use the studio.
    """

    message = "Only authors can access the author studio."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (getattr(user, "role", None) == "AUTHOR" or user.is_staff)
        )


# Sum of order-item quantities whose parent order has progressed past
# cancellation, treated as "units sold".
_SOLD_STATUSES = ("confirmed", "processing", "shipped", "delivered")


class AuthorBookViewSet(GenericViewSet):
    """Author-scoped CRUD for the owner's own books."""

    permission_classes = [IsAuthor]
    pagination_class = StandardResultsSetPagination
    # Declared for schema generation + router basename inference; real access
    # is always owner-scoped through get_queryset below.
    queryset = Book.objects.none()

    def get_serializer_class(self):
        if self.action in ("create", "partial_update", "update"):
            return AuthorBookWriteSerializer
        return AuthorBookSerializer

    def get_queryset(self):
        """Books owned by the current user, annotated with performance metrics."""
        from django.db.models import Q

        # drf-spectacular introspects the view with an AnonymousUser; short-circuit.
        if getattr(self, "swagger_fake_view", False):
            return Book.objects.none()

        return (
            Book.objects.filter(owner=self.request.user)
            .annotate(
                units_sold=Coalesce(
                    Sum(
                        "orderitem__quantity",
                        filter=Q(orderitem__order__status__in=_SOLD_STATUSES),
                    ),
                    0,
                ),
                revenue=Coalesce(
                    Sum(
                        F("orderitem__quantity") * F("orderitem__unit_price"),
                        filter=Q(orderitem__order__status__in=_SOLD_STATUSES),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    ),
                    0,
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                avg_rating=Avg(
                    "reviews__rating",
                    filter=Q(reviews__is_approved=True),
                ),
                review_count=Coalesce(
                    Count(
                        "reviews",
                        filter=Q(reviews__is_approved=True),
                        distinct=True,
                    ),
                    0,
                ),
            )
            .order_by("-created_at", "id")
        )

    def _get_owned(self, pk):
        """Fetch one annotated, owner-scoped book or None."""
        return self.get_queryset().filter(pk=pk).first()

    # ------------------------------------------------------------------
    # LIST — GET /api/author/books/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="List my books",
        description="Returns the authenticated author's own books with sales, "
        "revenue and rating metrics. Paginated.",
        responses={200: OpenApiResponse(response=SuccessResponseSerializer)},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AuthorBookSerializer(page, many=True)
        payload = {
            "results": serializer.data,
            "count": paginator.page.paginator.count,
            "num_pages": paginator.page.paginator.num_pages,
            "current_page": paginator.page.number,
            "page_size": paginator.get_page_size(request),
            "has_next": paginator.page.has_next(),
            "has_previous": paginator.page.has_previous(),
        }
        return success_response(data=payload, message="Your books retrieved.")

    # ------------------------------------------------------------------
    # RETRIEVE — GET /api/author/books/<id>/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Get one of my books",
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer),
            404: OpenApiResponse(response=ErrorResponseSerializer),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        book = self._get_owned(kwargs.get("pk"))
        if book is None:
            return error_response("Book not found.", status_code=404)
        return success_response(
            data=AuthorBookSerializer(book).data,
            message="Book retrieved.",
        )

    # ------------------------------------------------------------------
    # CREATE — POST /api/author/books/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Publish a new book",
        description="Creates a new book owned by the authenticated author. "
        "The book goes live immediately (is_active=True).",
        request=AuthorBookWriteSerializer,
        responses={
            201: OpenApiResponse(response=SuccessResponseSerializer),
            400: OpenApiResponse(response=ErrorResponseSerializer),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = AuthorBookWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Default the display author to the owner's name when not supplied.
        author_name = serializer.validated_data.get("author") or getattr(
            request.user, "full_name", ""
        )
        book = serializer.save(
            owner=request.user,
            author=author_name,
            is_active=True,
        )
        logger.info(
            "Author publish | user_id=%s book_id=%s title=%r",
            request.user.id, book.id, book.title,
        )
        # Re-fetch through the annotated queryset for a consistent payload.
        book = self._get_owned(book.id) or book
        return success_response(
            data=AuthorBookSerializer(book).data,
            message="Book published.",
            status_code=201,
        )

    # ------------------------------------------------------------------
    # UPDATE — PATCH /api/author/books/<id>/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Update one of my books",
        description="Partial update of a book owned by the author.",
        request=AuthorBookWriteSerializer,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer),
            400: OpenApiResponse(response=ErrorResponseSerializer),
            404: OpenApiResponse(response=ErrorResponseSerializer),
        },
    )
    def partial_update(self, request, *args, **kwargs):
        book = self._get_owned(kwargs.get("pk"))
        if book is None:
            return error_response("Book not found.", status_code=404)
        serializer = AuthorBookWriteSerializer(book, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("Author update | user_id=%s book_id=%s", request.user.id, book.id)
        book = self._get_owned(book.id) or book
        return success_response(
            data=AuthorBookSerializer(book).data,
            message="Book updated.",
        )

    # ------------------------------------------------------------------
    # DESTROY — DELETE /api/author/books/<id>/  (soft delete)
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Remove one of my books",
        description="Soft-deletes the book (is_active=False). It stops appearing "
        "in public listings but remains in the author's catalogue history.",
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer),
            404: OpenApiResponse(response=ErrorResponseSerializer),
        },
    )
    def destroy(self, request, *args, **kwargs):
        book = self._get_owned(kwargs.get("pk"))
        if book is None:
            return error_response("Book not found.", status_code=404)
        book.is_active = False
        book.save(update_fields=["is_active", "updated_at"])
        logger.info("Author remove | user_id=%s book_id=%s", request.user.id, book.id)
        return success_response(message="Book removed.")

    # ------------------------------------------------------------------
    # PUBLISH — POST /api/author/books/<id>/publish/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Publish (make live) a book",
        request=None,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer),
            404: OpenApiResponse(response=ErrorResponseSerializer),
        },
    )
    @action(detail=True, methods=["post"], url_path="publish")
    def publish(self, request, pk=None):
        return self._set_active(pk, True, "Book published.")

    # ------------------------------------------------------------------
    # UNPUBLISH — POST /api/author/books/<id>/unpublish/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Unpublish (move to draft) a book",
        request=None,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer),
            404: OpenApiResponse(response=ErrorResponseSerializer),
        },
    )
    @action(detail=True, methods=["post"], url_path="unpublish")
    def unpublish(self, request, pk=None):
        return self._set_active(pk, False, "Book moved to draft.")

    def _set_active(self, pk, value, message):
        book = self._get_owned(pk)
        if book is None:
            return error_response("Book not found.", status_code=404)
        book.is_active = value
        book.save(update_fields=["is_active", "updated_at"])
        logger.info(
            "Author set-active | user_id=%s book_id=%s active=%s",
            self.request.user.id, book.id, value,
        )
        book = self._get_owned(book.id) or book
        return success_response(
            data=AuthorBookSerializer(book).data,
            message=message,
        )


class AuthorStudioViewSet(ViewSet):
    """Aggregate read-only endpoints for the author dashboard."""

    permission_classes = [IsAuthor]

    # ------------------------------------------------------------------
    # STATS — GET /api/author/stats/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Author performance stats",
        description="Aggregate metrics across all of the author's books: "
        "published title count, total copies sold, gross + royalty revenue, "
        "and average rating.",
        responses={200: OpenApiResponse(response=SuccessResponseSerializer)},
    )
    def list(self, request, *args, **kwargs):
        from django.db.models import Q

        owned = Book.objects.filter(owner=request.user)

        sales = owned.aggregate(
            units_sold=Coalesce(
                Sum(
                    "orderitem__quantity",
                    filter=Q(orderitem__order__status__in=_SOLD_STATUSES),
                ),
                0,
            ),
            revenue=Coalesce(
                Sum(
                    F("orderitem__quantity") * F("orderitem__unit_price"),
                    filter=Q(orderitem__order__status__in=_SOLD_STATUSES),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                0,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )

        ratings = owned.aggregate(
            avg_rating=Avg("reviews__rating", filter=Q(reviews__is_approved=True)),
            review_count=Coalesce(
                Count("reviews", filter=Q(reviews__is_approved=True), distinct=True),
                0,
            ),
        )

        gross = float(sales["revenue"] or 0)
        # Authors keep a 70% royalty share — matches the frontend display.
        royalty_rate = 0.70
        payload = {
            "published_titles": owned.filter(is_active=True).count(),
            "draft_titles": owned.filter(is_active=False).count(),
            "total_titles": owned.count(),
            "units_sold": int(sales["units_sold"] or 0),
            "gross_revenue": round(gross, 2),
            "royalties": round(gross * royalty_rate, 2),
            "royalty_rate": royalty_rate,
            "avg_rating": round(float(ratings["avg_rating"]), 1)
            if ratings["avg_rating"] is not None
            else None,
            "review_count": int(ratings["review_count"] or 0),
        }
        return success_response(data=payload, message="Author stats retrieved.")

    # ------------------------------------------------------------------
    # REVIEWS — GET /api/author/reviews/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Recent reviews on my books",
        description="Returns the most recent approved reviews left on any of "
        "the author's books.",
        responses={200: OpenApiResponse(response=SuccessResponseSerializer)},
    )
    @action(detail=False, methods=["get"], url_path="reviews")
    def reviews(self, request):
        from apps.reviews.models import Review

        qs = (
            Review.objects.filter(
                book__owner=request.user,
                is_approved=True,
            )
            .select_related("user", "book")
            .order_by("-created_at")[:10]
        )
        data = [
            {
                "id": str(r.id),
                "book_id": str(r.book_id),
                "book_title": r.book.title,
                "reader": r.user.full_name or r.user.email.split("@")[0],
                "rating": r.rating,
                "title": r.title,
                "body": r.body,
                "created_at": r.created_at,
            }
            for r in qs
        ]
        return success_response(data={"results": data}, message="Reviews retrieved.")

    # ------------------------------------------------------------------
    # SALES ANALYTICS — GET /api/author/analytics/
    # ------------------------------------------------------------------
    def _owned_book_ids(self, request) -> "list[str]":
        """UUID strings for every book the current author owns."""
        return [
            str(pk)
            for pk in Book.objects.filter(owner=request.user).values_list(
                "id", flat=True
            )
        ]

    @extend_schema(
        summary="Sales analytics for my catalogue",
        description=(
            "Proxies to the analytics microservice, scoped to the books this "
            "author owns. Returns the headline sales summary (revenue, units "
            "sold, orders, top titles) plus a daily revenue series.\n\n"
            "Optional `start_date` / `end_date` (YYYY-MM-DD) narrow the window."
        ),
        parameters=[
            OpenApiParameter(name="start_date", required=False, type=str),
            OpenApiParameter(name="end_date", required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer),
            503: OpenApiResponse(response=ErrorResponseSerializer),
        },
    )
    @action(detail=False, methods=["get"], url_path="analytics")
    def analytics(self, request):
        book_ids = self._owned_book_ids(request)
        if not book_ids:
            # No catalogue yet — return a well-formed empty payload so the UI
            # can render zero-state cards without a microservice round-trip.
            return success_response(
                data={
                    "summary": {
                        "total_revenue": 0,
                        "total_orders": 0,
                        "total_items_sold": 0,
                        "average_order_value": 0,
                        "monthly_revenue": 0,
                        "top_selling_books": [],
                    },
                    "daily": [],
                },
                message="No books yet — analytics will appear once you publish.",
            )

        params = {
            "book_ids": ",".join(book_ids),
            "start_date": request.query_params.get("start_date"),
            "end_date": request.query_params.get("end_date"),
        }

        # Fetch the summary and daily series concurrently to halve the wall-clock
        # latency (each is an independent round-trip to the analytics service).
        # The summary is the critical payload; the daily series is best-effort,
        # so a slow/failed daily call still returns a usable dashboard.
        with ThreadPoolExecutor(max_workers=2) as pool:
            summary_future = pool.submit(
                analytics_client.get, "/analytics/sales/summary", params
            )
            daily_future = pool.submit(
                analytics_client.get, "/analytics/sales/daily", params
            )

            try:
                summary = summary_future.result()
            except AnalyticsServiceError as exc:
                return error_response(exc.message, status_code=exc.status_code)

            try:
                daily = daily_future.result()
            except AnalyticsServiceError as exc:
                # Non-fatal: return the summary with an empty series and flag it.
                logger.warning("Author analytics: daily series unavailable: %s", exc.message)
                daily = []

        return success_response(
            data={"summary": summary, "daily": daily},
            message="Author sales analytics retrieved.",
        )

    # ------------------------------------------------------------------
    # PER-BOOK SALES — GET /api/author/books/<id>/analytics/
    # ------------------------------------------------------------------
    @extend_schema(
        summary="Sales analytics for one of my books",
        description=(
            "Proxies to the analytics microservice for a single book the author "
            "owns. Returns totals (units, revenue, orders) and a daily series.\n\n"
            "Returns 404 if the book is not part of the author's catalogue."
        ),
        parameters=[
            OpenApiParameter(name="start_date", required=False, type=str),
            OpenApiParameter(name="end_date", required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer),
            404: OpenApiResponse(response=ErrorResponseSerializer),
            503: OpenApiResponse(response=ErrorResponseSerializer),
        },
    )
    @action(detail=False, methods=["get"], url_path=r"analytics/book/(?P<book_id>[^/.]+)")
    def book_analytics(self, request, book_id=None):
        # Ownership check — authors may only see their own books' analytics.
        if not Book.objects.filter(owner=request.user, pk=book_id).exists():
            return error_response("Book not found.", status_code=404)

        params = {
            "start_date": request.query_params.get("start_date"),
            "end_date": request.query_params.get("end_date"),
        }
        try:
            data = analytics_client.get(
                f"/analytics/sales/book/{book_id}", params=params
            )
        except AnalyticsServiceError as exc:
            return error_response(exc.message, status_code=exc.status_code)

        return success_response(data=data, message="Book analytics retrieved.")
