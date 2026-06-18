"""
analytics/views.py

Store-wide analytics — thin proxy to the FastAPI analytics microservice
(``bookstore-microservices``). Heavy aggregation lives in the microservice,
which reads the same PostgreSQL database; Django just authorises the request
and forwards it.

All endpoints here are admin-only (IsAdminUser). Author-scoped analytics live
in the author studio (apps.books.author_views).

Endpoints (mounted under /api/analytics/):
  GET /api/analytics/sales/        Headline sales summary
  GET /api/analytics/sales/daily/  Daily revenue time series
  GET /api/analytics/sales/monthly/  Monthly revenue time series
  GET /api/analytics/sales/top-books/  Best-selling books
  GET /api/analytics/sales/by-author/  Revenue grouped by author
  GET /api/analytics/sales/by-category/  Revenue grouped by category
  GET /api/analytics/inventory/    Inventory health snapshot
  GET /api/analytics/customers/    Customer lifetime-value overview
  POST /api/analytics/reports/     Generate a report (pdf/csv/xlsx)
"""
import logging

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser

from apps.core import analytics_client
from apps.core.analytics_client import AnalyticsServiceError
from apps.core.responses import error_response, success_response
from apps.core.serializers import ErrorResponseSerializer, SuccessResponseSerializer

logger = logging.getLogger(__name__)

# Common date-range query params reused across the proxy endpoints.
_DATE_PARAMS = [
    OpenApiParameter(name="start_date", required=False, type=str),
    OpenApiParameter(name="end_date", required=False, type=str),
]


def _date_params(request) -> dict:
    return {
        "start_date": request.query_params.get("start_date"),
        "end_date": request.query_params.get("end_date"),
    }


def _proxy(request, path, params=None, message="Analytics retrieved."):
    """Forward a GET to the analytics service and wrap the result/error."""
    try:
        data = analytics_client.get(path, params=params)
    except AnalyticsServiceError as exc:
        return error_response(exc.message, status_code=exc.status_code)
    return success_response(data=data, message=message)


@extend_schema(
    summary="Store-wide sales summary (admin)",
    parameters=_DATE_PARAMS,
    responses={
        200: OpenApiResponse(response=SuccessResponseSerializer),
        503: OpenApiResponse(response=ErrorResponseSerializer),
    },
)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def sales_summary(request):
    return _proxy(
        request,
        "/analytics/sales/summary",
        params=_date_params(request),
        message="Sales summary retrieved.",
    )


@extend_schema(summary="Daily sales series (admin)", parameters=_DATE_PARAMS)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def sales_daily(request):
    return _proxy(
        request,
        "/analytics/sales/daily",
        params=_date_params(request),
        message="Daily sales retrieved.",
    )


@extend_schema(summary="Monthly sales series (admin)", parameters=_DATE_PARAMS)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def sales_monthly(request):
    return _proxy(
        request,
        "/analytics/sales/monthly",
        params=_date_params(request),
        message="Monthly sales retrieved.",
    )


@extend_schema(
    summary="Best-selling books (admin)",
    parameters=_DATE_PARAMS
    + [OpenApiParameter(name="limit", required=False, type=int)],
)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def sales_top_books(request):
    params = _date_params(request)
    params["limit"] = request.query_params.get("limit")
    return _proxy(
        request,
        "/analytics/sales/top-books",
        params=params,
        message="Top-selling books retrieved.",
    )


@extend_schema(summary="Revenue by author (admin)", parameters=_DATE_PARAMS)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def sales_by_author(request):
    return _proxy(
        request,
        "/analytics/sales/by-author",
        params=_date_params(request),
        message="Revenue by author retrieved.",
    )


@extend_schema(summary="Revenue by category (admin)", parameters=_DATE_PARAMS)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def sales_by_category(request):
    return _proxy(
        request,
        "/analytics/sales/by-category",
        params=_date_params(request),
        message="Revenue by category retrieved.",
    )


@extend_schema(summary="Inventory health snapshot (admin)")
@api_view(["GET"])
@permission_classes([IsAdminUser])
def inventory_health(request):
    return _proxy(
        request,
        "/analytics/inventory/health",
        message="Inventory health retrieved.",
    )


@extend_schema(
    summary="Customer lifetime-value overview (admin)",
    parameters=[OpenApiParameter(name="limit", required=False, type=int)],
)
@api_view(["GET"])
@permission_classes([IsAdminUser])
def customers_overview(request):
    return _proxy(
        request,
        "/analytics/customers/ltv",
        params={"limit": request.query_params.get("limit")},
        message="Customer overview retrieved.",
    )


@extend_schema(
    summary="Generate a report (admin)",
    description=(
        "Delegates report generation to the analytics microservice. Body: "
        "`{report_type: sales|inventory|customers, file_format: pdf|csv|xlsx, "
        "start_date?, end_date?}`. Returns the report job metadata including a "
        "download URL on the microservice."
    ),
    responses={
        201: OpenApiResponse(response=SuccessResponseSerializer),
        503: OpenApiResponse(response=ErrorResponseSerializer),
    },
)
@api_view(["POST"])
@permission_classes([IsAdminUser])
def generate_report(request):
    payload = {
        "report_type": request.data.get("report_type", "sales"),
        "file_format": request.data.get("file_format", "pdf"),
        "start_date": request.data.get("start_date"),
        "end_date": request.data.get("end_date"),
    }
    try:
        data = analytics_client.post("/reports/generate", json=payload)
    except AnalyticsServiceError as exc:
        return error_response(exc.message, status_code=exc.status_code)
    return success_response(
        data=data, message="Report generation requested.", status_code=201
    )
