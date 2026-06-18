"""
apps/core/analytics_client.py

Thin HTTP client for the FastAPI analytics microservice
(``bookstore-microservices``).

The microservice reads from the same PostgreSQL database as Django and exposes
read-only analytics under ``/analytics/*`` plus report generation under
``/reports/*``. Django proxies to it rather than recomputing heavy aggregates
itself, keeping the placeholder ``apps.analytics`` promise of "delegate report
generation to the FastAPI microservice".

Configuration:
  settings.ANALYTICS_SERVICE_URL      Base URL (e.g. http://localhost:8001)
  settings.ANALYTICS_SERVICE_TIMEOUT  Per-request timeout in seconds

All failures are surfaced as ``AnalyticsServiceError`` so callers can translate
them into a clean 503/502 response instead of leaking httpx exceptions.
"""
import logging
from typing import Any, Optional

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


class AnalyticsServiceError(Exception):
    """Raised when the analytics microservice is unreachable or errors.

    Attributes:
        status_code: HTTP status Django should respond with (503 unconfigured /
                     unreachable, 502 for an upstream error response).
    """

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def is_configured() -> bool:
    """True when an analytics service base URL is set."""
    return bool(getattr(settings, "ANALYTICS_SERVICE_URL", ""))


def _base_url() -> str:
    url = getattr(settings, "ANALYTICS_SERVICE_URL", "")
    if not url:
        raise AnalyticsServiceError(
            "Analytics service is not configured (ANALYTICS_SERVICE_URL unset).",
            status_code=503,
        )
    return url


def _clean_params(params: Optional[dict]) -> Optional[dict]:
    """Drop None values so we don't send empty query params upstream."""
    if not params:
        return None
    return {k: v for k, v in params.items() if v is not None}


def get(path: str, params: Optional[dict] = None) -> Any:
    """GET ``path`` on the analytics service and return parsed JSON.

    Args:
        path:   Service path beginning with '/', e.g. '/analytics/sales/summary'.
        params: Optional query params (None values are stripped).

    Raises:
        AnalyticsServiceError: on configuration, network or upstream errors.
    """
    base = _base_url()
    timeout = getattr(settings, "ANALYTICS_SERVICE_TIMEOUT", 10)
    url = f"{base}{path}"
    try:
        resp = httpx.get(url, params=_clean_params(params), timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Analytics service returned %s for %s",
            exc.response.status_code,
            path,
        )
        raise AnalyticsServiceError(
            f"Analytics service error ({exc.response.status_code}).",
            status_code=502,
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        logger.warning("Analytics service request failed for %s: %s", path, exc)
        raise AnalyticsServiceError(
            "Analytics service is currently unavailable.",
            status_code=503,
        ) from exc


def post(path: str, json: Optional[dict] = None) -> Any:
    """POST JSON to ``path`` on the analytics service and return parsed JSON."""
    base = _base_url()
    timeout = getattr(settings, "ANALYTICS_SERVICE_TIMEOUT", 10)
    url = f"{base}{path}"
    try:
        resp = httpx.post(url, json=json or {}, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "Analytics service returned %s for POST %s",
            exc.response.status_code,
            path,
        )
        raise AnalyticsServiceError(
            f"Analytics service error ({exc.response.status_code}).",
            status_code=502,
        ) from exc
    except (httpx.RequestError, ValueError) as exc:
        logger.warning("Analytics service POST failed for %s: %s", path, exc)
        raise AnalyticsServiceError(
            "Analytics service is currently unavailable.",
            status_code=503,
        ) from exc
