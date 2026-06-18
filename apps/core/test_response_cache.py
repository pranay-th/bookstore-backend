"""
core/test_response_cache.py

Tests for ResponseCacheMiddleware behaviour:
  - Public catalog GETs are cached and tagged for the browser/CDN (Cache-Control + ETag)
  - Conditional requests (If-None-Match) return 304 with no body
  - Health check is never cached
  - Personalised / excluded paths are never cached
  - Non-included paths are not cached even when not explicitly excluded
"""
from django.core.cache import caches
from django.test import TestCase, override_settings
from rest_framework.test import APIClient


@override_settings(
    RESPONSE_CACHE_ENABLED=True,
    RESPONSE_CACHE_INCLUDE_PATHS=['/api/books/', '/api/categories/'],
    RESPONSE_CACHE_EXCLUDE_PATHS=[
        '/admin/', '/static/', '/media/', '/schema/', '/swagger/', '/redoc/',
        '/favicon.ico', '/health/', '/user/', '/api/author/',
    ],
    CACHES={
        'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
        'throttle': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
        'response_cache': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
    },
    MIDDLEWARE_THROTTLE_ENABLED=False,
)
class ResponseCacheTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        caches['response_cache'].clear()

    def test_books_response_is_cached_with_headers(self):
        first = self.client.get('/api/books/?page=1&page_size=1')
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first['X-Cache'], 'MISS')
        self.assertIn('public', first['Cache-Control'])
        self.assertTrue(first.has_header('ETag'))

        second = self.client.get('/api/books/?page=1&page_size=1')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second['X-Cache'], 'HIT')

    def test_conditional_request_returns_304(self):
        first = self.client.get('/api/books/?page=1&page_size=1')
        etag = first['ETag']

        revalidate = self.client.get(
            '/api/books/?page=1&page_size=1',
            HTTP_IF_NONE_MATCH=etag,
        )
        self.assertEqual(revalidate.status_code, 304)
        self.assertEqual(revalidate['X-Cache'], 'HIT')
        self.assertEqual(revalidate.content, b'')

    def test_health_is_never_cached(self):
        resp = self.client.get('/health/')
        self.assertEqual(resp.status_code, 200)
        # No X-Cache header means the middleware skipped this path entirely.
        self.assertFalse(resp.has_header('X-Cache'))

    def test_non_included_path_is_not_cached(self):
        # /api/discussions/ is public + GET but not in the include list.
        resp = self.client.get('/api/discussions/threads/')
        # Either the endpoint 200s without cache headers, or it errors — in
        # both cases it must NOT carry the cache MISS/HIT marker.
        self.assertFalse(resp.has_header('X-Cache'))
