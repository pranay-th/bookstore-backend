"""
apps/core/middleware.py

Throttle middleware for the Bookstore API.

This middleware applies IP-level rate limiting at the Django layer —
before requests even reach DRF views. It acts as a first line of
defense, complementing the per-view DRF throttle classes in throttles.py.

Why middleware AND per-view throttles?
    - Middleware blocks at the WSGI/ASGI layer — cheaper, catches all paths
      including non-DRF routes (admin, static, etc. are excluded below).
    - Per-view DRF throttles provide fine-grained control per endpoint.

Architecture:
    Request
        │
        ▼
    ThrottleMiddleware  ← global IP-level guard (1000/day anon, 10000/day auth)
        │
        ▼
    DRF View
        │
        ▼
    Per-view throttle  ← endpoint-specific guard (e.g. 20/min for login)

Redis key format:
    throttle:middleware:<user_id|ip>

Configuration:
    Add to settings.MIDDLEWARE (must come AFTER AuthenticationMiddleware
    so request.user is populated):

        'apps.core.middleware.ThrottleMiddleware',

    Optional settings (override in base.py / environment):
        MIDDLEWARE_THROTTLE_ANON_RATE     default: '1000/day'
        MIDDLEWARE_THROTTLE_AUTH_RATE     default: '10000/day'
        MIDDLEWARE_THROTTLE_ENABLED       default: True

Excluded paths (configurable via MIDDLEWARE_THROTTLE_EXCLUDED_PATHS):
    /admin/, /static/, /media/, /schema/, /swagger/, /redoc/

Response on limit exceeded:
    HTTP 429 — standard envelope via apps.core.exceptions handler
"""

import json
import logging
import time

from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_ANON_RATE = '1000/day'
_DEFAULT_AUTH_RATE = '10000/day'

_EXCLUDED_PATH_PREFIXES = [
    '/admin/',
    '/static/',
    '/media/',
    '/schema/',
    '/swagger/',
    '/redoc/',
    '/favicon.ico',
]

_PERIOD_SECONDS = {
    'second': 1,
    'minute': 60,
    'hour': 3600,
    'day': 86400,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_rate(rate_string: str) -> tuple[int, int]:
    """
    Parse a DRF-style rate string into (num_requests, period_seconds).

    Examples:
        '1000/day'   → (1000, 86400)
        '20/minute'  → (20, 60)
        '300/hour'   → (300, 3600)

    Raises:
        ValueError if the format is unrecognised.
    """
    try:
        count_str, period = rate_string.split('/')
        count = int(count_str.strip())
        period = period.strip().rstrip('s')  # allow 'minutes' or 'minute'
        # Normalise plural
        period = period.rstrip('s') if period.endswith('s') and period != 'seconds' else period
        seconds = _PERIOD_SECONDS.get(period)
        if seconds is None:
            raise ValueError(f"Unknown period '{period}'")
        return count, seconds
    except Exception as exc:
        raise ValueError(f"Invalid throttle rate '{rate_string}': {exc}") from exc


def _get_redis_client():
    """Return a Redis client using the project's REDIS_URL setting."""
    import redis as redis_lib
    return redis_lib.from_url(
        getattr(settings, 'REDIS_URL', 'redis://localhost:6379'),
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def _get_client_ip(request) -> str:
    """
    Extract the real client IP, respecting X-Forwarded-For on Render/Vercel.
    Always returns a non-empty string.
    """
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _make_throttle_response(detail: str = 'Too many requests. Please slow down.') -> JsonResponse:
    """Return a 429 JSON response in the project's standard envelope."""
    body = {
        'status': {
            'success': False,
            'code': 429,
            'message': detail,
        },
        'data': None,
    }
    response = JsonResponse(body, status=429)
    response['Retry-After'] = '60'
    return response


# ---------------------------------------------------------------------------
# Middleware class
# ---------------------------------------------------------------------------

class ThrottleMiddleware:
    """
    Middleware that enforces global IP-level request rate limits using Redis.

    Applies before DRF view throttles as a broad first-line defence.
    Fine-grained per-endpoint throttling is handled by the DRF throttle
    classes in apps.core.throttles.

    Configuration (all optional — set in settings.py or .env):
        MIDDLEWARE_THROTTLE_ENABLED (bool, default True)
        MIDDLEWARE_THROTTLE_ANON_RATE (str, default '1000/day')
        MIDDLEWARE_THROTTLE_AUTH_RATE (str, default '10000/day')
        MIDDLEWARE_THROTTLE_EXCLUDED_PATHS (list[str])
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._redis = None  # lazily initialised

        # Parse rates once at startup
        anon_rate = getattr(settings, 'MIDDLEWARE_THROTTLE_ANON_RATE', _DEFAULT_ANON_RATE)
        auth_rate = getattr(settings, 'MIDDLEWARE_THROTTLE_AUTH_RATE', _DEFAULT_AUTH_RATE)

        try:
            self.anon_limit, self.anon_period = _parse_rate(anon_rate)
            self.auth_limit, self.auth_period = _parse_rate(auth_rate)
        except ValueError as exc:
            logger.error('ThrottleMiddleware: bad rate config — %s. Throttling disabled.', exc)
            self.anon_limit = self.auth_limit = None

        self.excluded_prefixes = (
            getattr(settings, 'MIDDLEWARE_THROTTLE_EXCLUDED_PATHS', None)
            or _EXCLUDED_PATH_PREFIXES
        )

    # ── Public interface ──────────────────────────────────────────────────

    def __call__(self, request):
        if self._should_skip(request):
            return self.get_response(request)

        if not getattr(settings, 'MIDDLEWARE_THROTTLE_ENABLED', True):
            return self.get_response(request)

        if self.anon_limit is None:
            # Config error — fail open
            return self.get_response(request)

        throttled, detail = self._check_throttle(request)
        if throttled:
            logger.warning(
                'ThrottleMiddleware: 429 for %s on %s',
                _get_client_ip(request),
                request.path,
            )
            return _make_throttle_response(detail)

        return self.get_response(request)

    # ── Internals ─────────────────────────────────────────────────────────

    def _should_skip(self, request) -> bool:
        """Return True for paths that should never be throttled."""
        path = request.path
        return any(path.startswith(prefix) for prefix in self.excluded_prefixes)

    def _check_throttle(self, request) -> tuple[bool, str]:
        """
        Increment the Redis counter for this client and check against the limit.

        Returns (throttled: bool, detail_message: str).
        Uses a sliding-window approach: key expires after the full period,
        so the window resets naturally.
        """
        is_auth = hasattr(request, 'user') and request.user.is_authenticated

        if is_auth:
            ident = f'user:{request.user.id}'
            limit = self.auth_limit
            period = self.auth_period
        else:
            ident = f'ip:{_get_client_ip(request)}'
            limit = self.anon_limit
            period = self.anon_period

        cache_key = f'throttle:middleware:{ident}'

        try:
            redis = self._get_redis()
            current = redis.incr(cache_key)
            if current == 1:
                # First request in this window — set the expiry
                redis.expire(cache_key, period)

            if current > limit:
                ttl = redis.ttl(cache_key)
                detail = (
                    f'Rate limit exceeded. You have sent {current} requests '
                    f'in the current window (limit: {limit}). '
                    f'Try again in {ttl} seconds.'
                )
                return True, detail

        except Exception as exc:
            # Redis unavailable — fail open so the API stays usable
            logger.warning(
                'ThrottleMiddleware: Redis error (%s) — failing open for %s',
                exc, ident,
            )

        return False, ''

    def _get_redis(self):
        """Lazily create and cache the Redis client."""
        if self._redis is None:
            self._redis = _get_redis_client()
        return self._redis
