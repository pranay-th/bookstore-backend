"""
apps/core/middleware.py

Two middleware classes for the Bookstore API:

  1. ThrottleMiddleware       — IP-level rate limiting via Redis
  2. ResponseCacheMiddleware  — Cache anonymous GET responses via Django cache

Both classes live here to keep the middleware layer in one place.
"""

import hashlib
import logging
import urllib.parse

from django.conf import settings
from django.core.cache import caches
from django.http import JsonResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Shared helpers
# ============================================================================

_EXCLUDED_PATHS = [
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
    'hour':   3600,
    'day':    86400,
}


def _get_client_ip(request) -> str:
    """Return the real client IP, honouring X-Forwarded-For."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _parse_rate(rate_string: str) -> tuple[int, int]:
    """
    Parse '20/minute' → (20, 60).  Raises ValueError on bad input.
    """
    try:
        count_str, period = rate_string.split('/')
        count = int(count_str.strip())
        period = period.strip().rstrip('s')
        seconds = _PERIOD_SECONDS.get(period)
        if seconds is None:
            raise ValueError(f"Unknown period '{period}'")
        return count, seconds
    except Exception as exc:
        raise ValueError(f"Invalid rate '{rate_string}': {exc}") from exc


def _get_redis():
    """Return a short-timeout Redis client from the project REDIS_URL."""
    import redis as _redis
    return _redis.from_url(
        getattr(settings, 'REDIS_URL', 'redis://localhost:6379'),
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


# ============================================================================
# 1. ThrottleMiddleware
# ============================================================================

class ThrottleMiddleware:
    """
    Global IP-level rate limiter using Redis.

    Runs before the view — cheap and catches all paths.
    Fine-grained per-endpoint limits are handled by DRF throttle classes.

    Settings (all optional):
        MIDDLEWARE_THROTTLE_ENABLED   bool   default True
        MIDDLEWARE_THROTTLE_ANON_RATE str    default '1000/day'
        MIDDLEWARE_THROTTLE_AUTH_RATE str    default '10000/day'

    Must be placed AFTER AuthenticationMiddleware in settings.MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._redis = None

        anon_rate = getattr(settings, 'MIDDLEWARE_THROTTLE_ANON_RATE', '1000/day')
        auth_rate = getattr(settings, 'MIDDLEWARE_THROTTLE_AUTH_RATE', '10000/day')

        try:
            self.anon_limit, self.anon_period = _parse_rate(anon_rate)
            self.auth_limit, self.auth_period = _parse_rate(auth_rate)
        except ValueError as exc:
            logger.error('ThrottleMiddleware: bad config — %s. Throttling disabled.', exc)
            self.anon_limit = self.auth_limit = None

    def __call__(self, request):
        if self._is_excluded(request):
            return self.get_response(request)

        if not getattr(settings, 'MIDDLEWARE_THROTTLE_ENABLED', True):
            return self.get_response(request)

        if self.anon_limit is None:
            return self.get_response(request)

        throttled, detail = self._check(request)
        if throttled:
            logger.warning(
                'ThrottleMiddleware: 429 — %s on %s',
                _get_client_ip(request), request.path,
            )
            return self._429(detail)

        return self.get_response(request)

    def _is_excluded(self, request) -> bool:
        path = request.path
        excluded = getattr(settings, 'MIDDLEWARE_THROTTLE_EXCLUDED_PATHS', _EXCLUDED_PATHS)
        return any(path.startswith(p) for p in excluded)

    def _check(self, request) -> tuple[bool, str]:
        is_auth = hasattr(request, 'user') and request.user.is_authenticated
        if is_auth:
            ident  = f'user:{request.user.id}'
            limit  = self.auth_limit
            period = self.auth_period
        else:
            ident  = f'ip:{_get_client_ip(request)}'
            limit  = self.anon_limit
            period = self.anon_period

        key = f'throttle:middleware:{ident}'
        try:
            redis = self._redis or _get_redis()
            self._redis = redis
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, period)
            if count > limit:
                ttl = redis.ttl(key)
                return True, (
                    f'Rate limit exceeded ({count}/{limit}). '
                    f'Try again in {ttl}s.'
                )
        except Exception as exc:
            logger.warning('ThrottleMiddleware: Redis error — failing open. %s', exc)

        return False, ''

    @staticmethod
    def _429(detail: str) -> JsonResponse:
        return JsonResponse(
            {
                'status': {'success': False, 'code': 429, 'message': detail},
                'data':   None,
            },
            status=429,
            headers={'Retry-After': '60'},
        )


# ============================================================================
# 2. ResponseCacheMiddleware
# ============================================================================

_CACHE_EXCLUDED_PATHS = _EXCLUDED_PATHS + [
    '/user/',    # auth endpoints — never cache
]

_WRITE_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}


def _cache_key(request) -> str:
    """
    Build a short, deterministic cache key from path + sorted query params.
    Format: rc:GET:<path>:<first16_of_sha256>
    """
    raw_qs = request.META.get('QUERY_STRING', '')
    if raw_qs:
        sorted_qs = urllib.parse.urlencode(
            sorted(urllib.parse.parse_qsl(raw_qs))
        )
    else:
        sorted_qs = ''

    digest = hashlib.sha256(f'{request.path}:{sorted_qs}'.encode()).hexdigest()[:16]
    return f'rc:GET:{request.path}:{digest}'


def _should_cache_request(request) -> bool:
    """Return True only for anonymous GET requests to non-excluded paths."""
    if request.method in _WRITE_METHODS:
        return False
    if request.method != 'GET':
        return False
    if hasattr(request, 'user') and request.user.is_authenticated:
        return False
    path = request.path
    excluded = getattr(settings, 'RESPONSE_CACHE_EXCLUDE_PATHS', _CACHE_EXCLUDED_PATHS)
    return not any(path.startswith(p) for p in excluded)


def _should_cache_response(response) -> bool:
    """Return True only for 200 responses under the size limit."""
    if response.status_code != 200:
        return False
    cc = response.get('Cache-Control', '')
    if 'no-store' in cc or 'private' in cc:
        return False
    max_size = getattr(settings, 'RESPONSE_CACHE_MAX_SIZE', 1_048_576)  # 1 MB
    return len(getattr(response, 'content', b'')) <= max_size


class ResponseCacheMiddleware:
    """
    Caches anonymous GET responses using Django's cache framework.

    On a HIT  — serves the cached response immediately (no view/DB hit).
    On a MISS — calls the view, stores the response, returns it.

    Settings (all optional):
        RESPONSE_CACHE_ENABLED       bool   default True
        RESPONSE_CACHE_TIMEOUT       int    default 900  (15 min)
        RESPONSE_CACHE_ALIAS         str    default 'response_cache'
        RESPONSE_CACHE_MAX_SIZE      int    default 1_048_576 (1 MB)
        RESPONSE_CACHE_EXCLUDE_PATHS list   additional excluded prefixes

    Must be placed AFTER ThrottleMiddleware in settings.MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'RESPONSE_CACHE_ENABLED', True):
            return self.get_response(request)

        if not _should_cache_request(request):
            return self.get_response(request)

        alias   = getattr(settings, 'RESPONSE_CACHE_ALIAS', 'response_cache')
        timeout = getattr(settings, 'RESPONSE_CACHE_TIMEOUT', 900)
        cache   = caches[alias]
        key     = _cache_key(request)

        # ── Cache lookup ──────────────────────────────────────────────────
        try:
            cached = cache.get(key)
        except Exception as exc:
            logger.warning('ResponseCacheMiddleware: cache.get failed — %s', exc)
            cached = None

        if cached is not None:
            logger.debug('Cache HIT  %s', request.path)
            cached['X-Cache'] = 'HIT'
            return cached

        logger.debug('Cache MISS %s', request.path)

        # ── Call the view ─────────────────────────────────────────────────
        response = self.get_response(request)

        # ── Store on the way out ──────────────────────────────────────────
        if _should_cache_response(response):
            try:
                cache.set(key, response, timeout)
            except Exception as exc:
                logger.warning('ResponseCacheMiddleware: cache.set failed — %s', exc)

        response['X-Cache'] = 'MISS'
        return response

    # ── Cache invalidation ────────────────────────────────────────────────

    @staticmethod
    def invalidate(path: str) -> None:
        """
        Delete the cached response for a path (no query string).
        Call this after any write that changes the resource at `path`.

        Usage:
            ResponseCacheMiddleware.invalidate('/api/books/')
        """
        alias = getattr(settings, 'RESPONSE_CACHE_ALIAS', 'response_cache')

        class _Req:
            method = 'GET'
            def __init__(self, p):
                self.path = p
                self.META = {'QUERY_STRING': ''}
                self.user = type('u', (), {'is_authenticated': False})()

        key = _cache_key(_Req(path))
        try:
            caches[alias].delete(key)
            logger.info('Cache INVALIDATED %s', path)
        except Exception as exc:
            logger.warning('ResponseCacheMiddleware.invalidate error — %s', exc)
