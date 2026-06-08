"""
Production settings — security-hardened, PostgreSQL, Render hosting.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# TODO: Set SECURE_SSL_REDIRECT = True once HTTPS is confirmed on Render
SECURE_BROWSER_XSS_FILTER       = True
SECURE_CONTENT_TYPE_NOSNIFF     = True
X_FRAME_OPTIONS                 = 'DENY'

# TODO: Uncomment HSTS headers once SSL is active
# SECURE_HSTS_SECONDS            = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD            = True

# TODO: Configure email backend (SendGrid / SES) for production
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Render injects PORT automatically
import os
PORT = os.environ.get('PORT', 8000)
