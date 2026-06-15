"""
apps/core/cache_utils.py

Response caching utilities for the Bookstore API.

Responsibilities:
  - Build deterministic cache keys from request path + query params
  - Store and retrieve cached responses via Django's cache framework
  - Provide cache invalidation helpers for use in views/signals
  - Log cache hits and misses

All cache operations use the dedicated 'response_cache' cache alias
(configured in settings.CACHES).  If Redis is unavailable the Django
cache framework transparently falls back to LocMemCache in development.

Cache key format:
    response_cache:<METHOD>:<path>:<sorted_query_string>
    e.g. response_cache:GET:/api/books/:author=tolkien&page=2

Public API:
    get_cached_response(request)       → HttpResponse | None
    cache_response(request, response)  → None
    invalidate_path(path)              → int  (number of keys deleted)
    invalidate_prefix(prefix)          → None

Configuration (settings.py):
    RESPONSE_CACHE_ENABLED     (bool,  default True)
    RESPONSE_CACHE_TIMEOUT     (int,   default 900  — 15 minutes)
    RESPONSE_CACHE_ALIAS       (str,   default 'response_cache')
    RESPONSE_CACHE_MAX_SIZE    (int,   default 1 MB — skip responses larger than this)
    RESPONSE_CACHE_INCLUDE_PATHS  (list[str] | None — if set, only these prefixes are cached)
    RESPONSE_CACHE_EXCLUDE_PATHS  (list[str]        — always skip these prefixes)
"""

import hashlib
import logging
import urllib.parse

from django.conf import settings
from django.core.cache import caches

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults — all overridable from settings / .env
# ---------------------------------------------------------------------------

_ALIAS      = 'response_cache'
_TIMEOUT    = 900        # 15 minutes
_MAX_BYTES  = 1_048_576  # 1 MB — don't cache very large payloads

_ALWAYS_EXCLUDE = [
    '/admin/',
    '/static/',
    '/media/',
    '/schema/',
    '/swagger/',
    '/redoc/',
    '/favicon.ico',
    '/user/',          # all auth endpoints — never cache
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(key, default):
    return getattr(settings, key, default)


def _get_cache():
    alias = _cfg('RESPONSE_CACHE_ALIAS', _ALIAS)
    return caches[alias]


def _is_cacheable_request(request) -> bool:
    """
    Return True if this request is a candidate for caching.

    Rules (any failing rule → not cacheable):
      1. Method must be GET
      2. User must NOT be authenticated (personalised data is never cached)
      3. Path must not be in the exclude list
      4. Path must be in the include list (if one is configured)
    """
    # Only GET
    if request.method != 'GET':
        return False

    # Never cache authenticated requests — responses may contain personal data
    if hasattr(request, 'user') and request.user.is_authenticated:
        return False

    path = request.path

    # Hard-coded exclusions
    exclude = _cfg('RESPONSE_CACHE_EXCLUDE_PATHS', _ALWAYS_EXCLUDE)
    if any(path.startswith(p) for p in exclude):
        return False

    # Optional inclusion allowlist — if not set, everything passes
    include = _cfg('RESPONSE_CACHE_INCLUDE_PATHS', None)
    if include and not any(path.startswith(p) for p in include):
        return False

    return True


def _is_cacheable_response(response) -> bool:
    """
    Return True if this response should be stored in the cache.

    Rules:
      - Status must be 200
      - Content must not exceed _MAX_BYTES to avoid flooding the cache
      - Cache-Control must not contain 'no-store' or 'private'
    """
    if response.status_code != 200:
        return False

    cc = response.get('Cache-Control', '')
    if 'no-store' in cc or 'private' in cc:
        return False

    content_length = len(getattr(response, 'content', b''))
    max_size = _cfg('RESPONSE_CACHE_MAX_SIZE', _MAX_BYTES)
    if content_length > max_size:
        logger.debug(
            'cache_utils: skipping large response (%d bytes) for %s',
            content_length, 'path',
        )
        return False

    return True


def build_cache_key(request) -> str:
    """
    Build a deterministic cache key from the request path and query string.

    Query parameters are sorted so that ?b=2&a=1 and ?a=1&b=2 map to the
    same key.  The key is SHA-256-truncated to keep Redis key sizes small.

    Format: response_cache:GET:<path>:<sorted_qs_hash>
    """
    path = request.path

    # Sort query params for consistent keys regardless of param order
    raw_qs = request.META.get('QUERY_STRING', '')
    if raw_qs:
        params = sorted(urllib.parse.parse_qsl(raw_qs))
        sorted_qs = urllib.parse.urlencode(params)
    else:
        sorted_qs = ''

    raw = f'GET:{path}:{sorted_qs}'
    digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return f'response_cache:GET:{path}:{digest}'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_cached_response(request):
    """
    Try to return a cached response for the given request.

    Returns the cached HttpResponse if found, or None on a miss / skip.
    Logs HIT / MISS at DEBUG level.
    """
    if not _cfg('RESPONSE_CACHE_ENABLED', True):
        return None

    if not _is_cacheable_request(request):
        return None

    key = build_cache_key(request)
    cached = _get_cache().get(key)

    if cached is not None:
        logger.debug('cache_utils: HIT  %s', request.path)
        return cached

    logger.debug('cache_utils: MISS %s', request.path)
    return None


def cache_response(request, response) -> None:
    """
    Store the response in the cache if it qualifies.

    Does nothing if caching is disabled, the request is not cacheable,
    or the response should not be stored.
    """
    if not _cfg('RESPONSE_CACHE_ENABLED', True):
        return

    if not _is_cacheable_request(request):
        return

    if not _is_cacheable_response(response):
        return

    key     = build_cache_key(request)
    timeout = _cfg('RESPONSE_CACHE_TIMEOUT', _TIMEOUT)

    try:
        _get_cache().set(key, response, timeout)
        logger.debug(
            'cache_utils: STORED %s (timeout=%ds)', request.path, timeout
        )
    except Exception as exc:
        # Cache store failure must never break the response
        logger.warning('cache_utils: failed to store cache — %s', exc)


def invalidate_path(path: str) -> None:
    """
    Delete all cached responses for an exact path (all query variants).

    Because we hash the query string into the key we cannot enumerate
    all variants — this deletes the zero-query-param variant only.
    For full invalidation use invalidate_prefix().

    Use after write operations that modify a specific resource:
        from apps.core.cache_utils import invalidate_path
        invalidate_path('/api/books/')
    """
    # Build a key for the path with no query string
    class _FakeRequest:
        method = 'GET'
        def __init__(self, p):
            self.path = p
            self.META = {'QUERY_STRING': ''}
            self.user = type('u', (), {'is_authenticated': False})()

    key = build_cache_key(_FakeRequest(path))
    try:
        _get_cache().delete(key)
        logger.info('cache_utils: INVALIDATED key for %s', path)
    except Exception as exc:
        logger.warning('cache_utils: invalidate_path error — %s', exc)


def invalidate_prefix(prefix: str) -> None:
    """
    Attempt to delete all cache entries whose key starts with the prefix.

    Only works when the cache backend supports key iteration (e.g. Redis
    via django-redis).  Silently skips on backends that don't support it.

    Use for broad invalidation after bulk writes:
        from apps.core.cache_utils import invalidate_prefix
        invalidate_prefix('response_cache:GET:/api/books/')
    """
    try:
        cache = _get_cache()
        # django-redis exposes delete_pattern; standard Django does not
        if hasattr(cache, 'delete_pattern'):
            count = cache.delete_pattern(f'{prefix}*')
            logger.info(
                'cache_utils: INVALIDATED ~%s keys matching prefix %s',
                count, prefix,
            )
        else:
            logger.debug(
                'cache_utils: invalidate_prefix — backend does not support pattern delete'
            )
    except Exception as exc:
        logger.warning('cache_utils: invalidate_prefix error — %s', exc)
