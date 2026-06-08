"""
Development settings — verbose errors, SQLite fallback, no security hardening.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

CORS_ALLOW_ALL_ORIGINS = True

# TODO: Add django-debug-toolbar for development profiling
# INSTALLED_APPS += ['debug_toolbar']

# Email — print to console in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
