"""
Local-only test settings — SQLite in-memory.

Used to run the test suite on a developer machine that cannot reach the Neon
PostgreSQL instance. CI still runs against a throwaway Postgres container
(see .github/workflows/ci.yml). This file is safe to keep: it is never used in
CI or production.
"""
import os

# Provide a dummy DATABASE_URL so base.py import-time check passes before we
# override DATABASES below.
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")

from .base import *  # noqa: F401, F403, E402

DEBUG = True
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Use the local-memory cache for throttling/response cache so tests need no Redis.
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "throttle": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "response_cache": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
