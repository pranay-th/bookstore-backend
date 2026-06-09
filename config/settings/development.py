"""
Development settings — verbose errors, no security hardening.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

# ---------------------------------------------------------------------------
# drf-spectacular (Swagger)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'Bookstore API',
    'DESCRIPTION': 'Bookstore backend API documentation',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SERVERS': [
        {'url': 'http://127.0.0.1:8000', 'description': 'Local dev server'},
    ],
}

# ---------------------------------------------------------------------------
# Email — print to console in development instead of sending via SendGrid
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
