"""
Production settings — security-hardened, PostgreSQL, Render hosting.
"""
from .base import *  # noqa: F401, F403
import os

DEBUG = False

SECURE_BROWSER_XSS_FILTER   = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS             = 'DENY'

# TODO: Uncomment once HTTPS is confirmed active on Render
# SECURE_SSL_REDIRECT            = True
# SECURE_HSTS_SECONDS            = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD            = True

# ---------------------------------------------------------------------------
# Email — SendGrid via django-anymail (production only)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = 'anymail.backends.sendgrid.EmailBackend'

# Render injects PORT automatically
PORT = os.environ.get('PORT', 8000)
