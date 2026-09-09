"""
analytics/views.py

Two surfaces onto the FastAPI analytics microservice (``bookstore-microservices``),
which does the heavy aggregation against the shared PostgreSQL database:

1. REST API (admin-only DRF endpoints, mounted under /api/analytics/) — consumed
   by the frontend. Thin proxy that authorises then forwards.

2. Admin dashboard (staff-only HTML view + JSON proxy, mounted under
   /admin/analytics/) — renders live analytics inside the Django admin.

Author-scoped analytics live separately in the author studio
(apps.books.author_views).

REST endpoints (under /api/analytics/):
  GET  /api/analytics/sales/          Headline sales summary
  GET  /api/analytics/sales/daily/    Daily revenue time series
  GET  /api/analytics/sales/monthly/  Monthly revenue time series
  GET  /api/analytics/sales/top-books/  Best-selling books
  GET  /api/analytics/sales/by-author/  Revenue grouped by author
  GET  /api/analytics/sales/by-category/  Revenue grouped by category
  GET  /api/analytics/inventory/      Inventory health snapshot
  GET  /api/analytics/customers/      Customer lifetime-value overview
  POST /api/analytics/reports/        Generate a report (pdf/csv/xlsx)
"""
import logging

import httpx
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import redirect
import json
from urllib.parse import urlencode
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken

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


# ===========================================================================
# REST API (DRF, admin-only) — mounted under /api/analytics/
# ===========================================================================
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


# ===========================================================================
# Admin dashboard (staff-only HTML + JSON proxy) — mounted under /admin/analytics/
# ===========================================================================
def _service_url():
    return getattr(settings, 'ANALYTICS_SERVICE_URL', 'http://localhost:8001')


def _fetch(path: str, timeout: float = None):
    """Fetch JSON from the analytics microservice. Returns None on failure.

    Defaults to ANALYTICS_SERVICE_TIMEOUT (or 30s) so a cold-starting Render
    free-tier service has time to wake up before we give up.
    """
    if timeout is None:
        timeout = getattr(settings, 'ANALYTICS_SERVICE_TIMEOUT', 30)
    url = f"{_service_url()}{path}"
    try:
        resp = httpx.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Analytics fetch failed (%s): %s", url, exc)
        return None


@staff_member_required
def analytics_dashboard(request):
    """Single sign-on into the frontend analytics dashboard.

    The rich dashboard lives in the React app at ``<FRONTEND_URL>/admin``. Since
    the Django admin session and the frontend JWT auth are separate systems, we
    mint a short-lived JWT for the logged-in staff user and hand it to the
    frontend via a dedicated SSO route, so the admin lands straight on the
    dashboard without logging in again.

    Tokens are passed in the URL fragment (``#``) which browsers never send to
    servers, and the frontend strips it from history immediately after reading.
    """
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000').rstrip('/')
    user = request.user

    refresh = RefreshToken.for_user(user)
    user_payload = {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "full_name": user.full_name,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }
    fragment = urlencode({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": json.dumps(user_payload),
    })
    return redirect(f"{base}/admin/sso#{fragment}")


@staff_member_required
def analytics_api_proxy(request):
    """
    Proxy endpoint: GET /admin/analytics/api/?path=<path>
    Forwards requests to the microservice so admin JS widgets can fetch data
    without CORS issues.
    """
    path = request.GET.get('path', '/analytics/sales/summary')
    data = _fetch(path)
    if data is None:
        return JsonResponse({'error': 'Analytics service unreachable'}, status=503)
    return JsonResponse(data, safe=False)
