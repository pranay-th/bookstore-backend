"""
Base settings shared across all environments.
"""
import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import config
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = config('SECRET_KEY', default='change-me-in-production')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
    cast=lambda v: [h.strip() for h in v.split(',')],
)

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'anymail',
]

LOCAL_APPS = [
    'apps.core',
    'apps.users',
    'apps.authors',
    'apps.categories',
    'apps.books',
    'apps.inventory',
    'apps.cart',
    'apps.wishlist',
    'apps.orders',
    'apps.payments',
    'apps.coupons',
    'apps.reviews',
    'apps.notifications',
    'apps.analytics',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # ThrottleMiddleware must come AFTER AuthenticationMiddleware so that
    # request.user is populated and auth vs. anon limits are applied correctly.
    'apps.core.middleware.ThrottleMiddleware',
    # ResponseCacheMiddleware must come AFTER ThrottleMiddleware so throttled
    # requests are blocked before we even check the cache.
    'apps.core.middleware.ResponseCacheMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# ---------------------------------------------------------------------------
# Database — Neon PostgreSQL (pooled, SSL required)
# DATABASE_URL must be set in the environment. No SQLite fallback.
# ---------------------------------------------------------------------------
_database_url = config('DATABASE_URL', default='')
if not _database_url:
    raise ImproperlyConfigured(
        'DATABASE_URL environment variable is not set. '
        'This project requires PostgreSQL — set DATABASE_URL to your Neon connection string.'
    )

DATABASES = {
    'default': dj_database_url.parse(
        _database_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Neon requires SSL and channel_binding on every connection.
DATABASES['default'].setdefault('OPTIONS', {})
DATABASES['default']['OPTIONS'].update({
    'sslmode': 'require',
    'channel_binding': 'require',
})

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = 'users.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'mediafiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # Global throttle defaults — individual views override with throttle_classes
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.core.throttles.AuthenticatedUserThrottle',
        'apps.core.throttles.AnonUserThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user':                '10000/day',
        'anon':                '1000/day',
        'login':               '20/minute',
        'signup':              '10/hour',
        'otp_generate':        '10/hour',
        'otp_verify':          '30/hour',
        'resend_verification': '5/hour',
        'password_reset':      '5/hour',
        'search':              '300/minute',
    },
}

# ---------------------------------------------------------------------------
# drf-spectacular (Swagger)
# No SERVERS list — drf-spectacular uses the incoming request host automatically.
# This means Swagger UI on Render will call the Render URL, not localhost.
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    'TITLE': 'Bookstore API',
    'DESCRIPTION': 'Bookstore backend API documentation',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

# ---------------------------------------------------------------------------
# JWT — djangorestframework-simplejwt
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(
        minutes=config('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=60, cast=int)
    ),
    'REFRESH_TOKEN_LIFETIME': timedelta(
        days=config('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)
    ),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': config('SECRET_KEY', default='change-me'),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ---------------------------------------------------------------------------
# Redis — OTP storage + throttle cache
# ---------------------------------------------------------------------------
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379')

# Django cache backend — used by DRF throttle classes and the throttle middleware.
# Falls back to in-memory cache if Redis is unavailable (development only).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
    'throttle': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'socket_connect_timeout': 1,
            'socket_timeout': 1,
        },
        'KEY_PREFIX': 'bookstore_throttle',
    },
    # Response cache — stores anonymous GET responses for 15 minutes.
    # Uses Redis when available; Django falls back to LocMemCache on error.
    'response_cache': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'socket_connect_timeout': 1,
            'socket_timeout': 1,
        },
        'KEY_PREFIX': 'bookstore_response',
    },
}

# ---------------------------------------------------------------------------
# Response cache settings
# ---------------------------------------------------------------------------
RESPONSE_CACHE_ENABLED  = config('RESPONSE_CACHE_ENABLED', default=True, cast=bool)
RESPONSE_CACHE_TIMEOUT  = config('RESPONSE_CACHE_TIMEOUT', default=900,  cast=int)   # 15 min
RESPONSE_CACHE_ALIAS    = 'response_cache'
RESPONSE_CACHE_MAX_SIZE = config('RESPONSE_CACHE_MAX_SIZE', default=1_048_576, cast=int)  # 1 MB

# Paths that are always excluded from response caching.
# Auth endpoints, write-heavy paths, and personalised routes should be here.
RESPONSE_CACHE_EXCLUDE_PATHS = [
    '/admin/',
    '/static/',
    '/media/',
    '/schema/',
    '/swagger/',
    '/redoc/',
    '/favicon.ico',
    '/user/',       # all auth endpoints — login, signup, OTP, etc.
]

# Optional: set RESPONSE_CACHE_INCLUDE_PATHS to restrict caching to only
# specific path prefixes.  Leave as None to cache all qualifying GET paths.
# Example: ['/api/books/', '/api/authors/', '/api/categories/']
RESPONSE_CACHE_INCLUDE_PATHS = config(
    'RESPONSE_CACHE_INCLUDE_PATHS',
    default='',
    cast=lambda v: [p.strip() for p in v.split(',') if p.strip()] or None,
)

# ---------------------------------------------------------------------------
# Throttle rates — override per environment via settings or THROTTLE_RATES dict
# ---------------------------------------------------------------------------
THROTTLE_RATES = {
    # Auth endpoints (anonymous, per IP)
    'login':               config('THROTTLE_LOGIN',               default='20/minute'),
    'signup':              config('THROTTLE_SIGNUP',              default='10/hour'),
    'otp_generate':        config('THROTTLE_OTP_GENERATE',        default='10/hour'),
    'otp_verify':          config('THROTTLE_OTP_VERIFY',          default='30/hour'),
    'resend_verification': config('THROTTLE_RESEND_VERIFICATION', default='5/hour'),
    'password_reset':      config('THROTTLE_PASSWORD_RESET',      default='5/hour'),
    # General endpoints
    'search':              config('THROTTLE_SEARCH',              default='300/minute'),
    'user':                config('THROTTLE_AUTH_USER',           default='10000/day'),
    'anon':                config('THROTTLE_ANON_USER',           default='1000/day'),
}

# Middleware-level global limits (broader, first-line defence)
MIDDLEWARE_THROTTLE_ENABLED   = config('MIDDLEWARE_THROTTLE_ENABLED', default=True, cast=bool)
MIDDLEWARE_THROTTLE_ANON_RATE = config('MIDDLEWARE_THROTTLE_ANON_RATE', default='1000/day')
MIDDLEWARE_THROTTLE_AUTH_RATE = config('MIDDLEWARE_THROTTLE_AUTH_RATE', default='10000/day')

# ---------------------------------------------------------------------------
# OTP settings
# ---------------------------------------------------------------------------
OTP_LENGTH = config('OTP_LENGTH', default=6, cast=int)
OTP_EXPIRY_MINUTES = config('OTP_EXPIRY_MINUTES', default=10, cast=int)

# ---------------------------------------------------------------------------
# Email verification settings
# ---------------------------------------------------------------------------
EMAIL_VERIFICATION_EXPIRY_MINUTES = config(
    'EMAIL_VERIFICATION_EXPIRY_MINUTES', default=1440, cast=int
)
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:3000')

# ---------------------------------------------------------------------------
# Cron secret — used to authenticate requests from crojob.org
# ---------------------------------------------------------------------------
CRON_SECRET_KEY = config('CRON_SECRET_KEY', default='')

# ---------------------------------------------------------------------------
# SendGrid via django-anymail
# ---------------------------------------------------------------------------
ANYMAIL = {
    'SENDGRID_API_KEY': config('SENDGRID_API_KEY', default=''),
}
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@example.com')

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000',
    cast=lambda v: [o.strip() for o in v.split(',')],
)

# Allow all Vercel preview/production URLs via regex so the free-tier
# changing subdomain never causes a CORS block.
# Matches: https://*.vercel.app and https://*-pranay-thakurs-projects.vercel.app etc.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https://[\w-]+\.vercel\.app$',
]

# ---------------------------------------------------------------------------
# Default primary key
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = config('LOG_LEVEL', default='DEBUG')
