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

# Default read budget (seconds). Analytics aggregates run against a shared
# (possibly cold-starting) Postgres, so reads can be slow on the first hit.
_DEFAULT_TIMEOUT = 20
# Connecting should always be fast; a slow connect means the service is down.
_CONNECT_TIMEOUT = 5


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


def _timeout() -> httpx.Timeout:
    """Build a split connect/read timeout.

    A short connect timeout fails fast when the service is down, while a longer
    read timeout tolerates slow aggregation queries (e.g. a cold Postgres).
    """
    read = getattr(settings, "ANALYTICS_SERVICE_TIMEOUT", _DEFAULT_TIMEOUT)
    return httpx.Timeout(read, connect=_CONNECT_TIMEOUT)


def _clean_params(params: Optional[dict]) -> Optional[dict]:
    """Drop None values so we don't send empty query params upstream."""
    if not params:
        return None
    return {k: v for k, v in params.items() if v is not None}


def get(path: str, params: Optional[dict] = None) -> Any:
    """GET ``path`` on the analytics service and return parsed JSON.

    Retries once on a timeout/connection error to absorb cold starts, then
    surfaces an ``AnalyticsServiceError`` so callers can return a clean 503/502.

    Args:
        path:   Service path beginning with '/', e.g. '/analytics/sales/summary'.
        params: Optional query params (None values are stripped).

    Raises:
        AnalyticsServiceError: on configuration, network or upstream errors.
    """
    base = _base_url()
    url = f"{base}{path}"
    cleaned = _clean_params(params)
    last_exc: Optional[Exception] = None

    for attempt in (1, 2):
        try:
            resp = httpx.get(url, params=cleaned, timeout=_timeout())
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            # An HTTP error response is deterministic — do not retry.
            logger.warning(
                "Analytics service returned %s for %s",
                exc.response.status_code,
                path,
            )
            raise AnalyticsServiceError(
                f"Analytics service error ({exc.response.status_code}).",
                status_code=502,
            ) from exc
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            # Transient — retry once (cold start / warm-up) before giving up.
            last_exc = exc
            logger.warning(
                "Analytics service request failed for %s (attempt %s/2): %s",
                path, attempt, exc,
            )
            continue
        except ValueError as exc:
            # Bad JSON body — not worth retrying.
            logger.warning("Analytics service returned invalid JSON for %s: %s", path, exc)
            raise AnalyticsServiceError(
                "Analytics service returned an invalid response.",
                status_code=502,
            ) from exc

    raise AnalyticsServiceError(
        "Analytics service is currently unavailable (timed out).",
        status_code=503,
    ) from last_exc


def post(path: str, json: Optional[dict] = None) -> Any:
    """POST JSON to ``path`` on the analytics service and return parsed JSON.

    Report generation is not idempotent, so this does NOT retry.
    """
    base = _base_url()
    url = f"{base}{path}"
    try:
        resp = httpx.post(url, json=json or {}, timeout=_timeout())
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
