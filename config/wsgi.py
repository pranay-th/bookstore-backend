"""WSGI config for bookstore-backend project."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

application = get_wsgi_application()

# Set up loguru after Django is fully loaded
from django.conf import settings  # noqa: E402
from apps.core.logging import setup_loguru  # noqa: E402

setup_loguru(log_level=settings.LOG_LEVEL, base_dir=settings.BASE_DIR)
