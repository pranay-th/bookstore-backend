"""
ASGI config for bookstore-backend project.

Routes HTTP traffic through Django and WebSocket traffic through Channels.
"""
import os
import re

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

# Initialize Django ASGI application early to populate AppRegistry.
django_asgi_app = get_asgi_application()

# Import after Django setup so apps + settings are loaded.
from django.conf import settings  # noqa: E402
from apps.discussions.routing import websocket_urlpatterns  # noqa: E402


class CorsOriginValidator(OriginValidator):
    """
    Allow WebSocket connections from the same origins permitted by CORS.

    The default AllowedHostsOriginValidator checks the Origin against
    ALLOWED_HOSTS, which breaks cross-origin setups (frontend on Vercel,
    backend on Render). This validator instead reuses CORS_ALLOWED_ORIGINS
    and CORS_ALLOWED_ORIGIN_REGEXES so the deployed frontend can connect.
    Actual authentication is still enforced by the JWT check in the consumer.
    """

    def __init__(self, application):
        super().__init__(application, [])
        self._allowed = set(getattr(settings, 'CORS_ALLOWED_ORIGINS', []) or [])
        self._regexes = [
            re.compile(p)
            for p in getattr(settings, 'CORS_ALLOWED_ORIGIN_REGEXES', []) or []
        ]

    def validate_origin(self, parsed_origin):
        # No Origin header (native/non-browser client) — allow; JWT still gates.
        if parsed_origin is None:
            return True
        origin = f'{parsed_origin.scheme}://{parsed_origin.netloc}'
        if origin in self._allowed:
            return True
        return any(rx.match(origin) for rx in self._regexes)


application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': CorsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    ),
})
