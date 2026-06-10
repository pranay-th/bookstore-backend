"""
Development settings — verbose errors, no security hardening.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

# ---------------------------------------------------------------------------
# Email — print to console in development instead of sending via SendGrid
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
