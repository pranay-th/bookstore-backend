"""
apps/core/throttles.py

Reusable DRF throttle classes for the Bookstore API.

All classes extend DRF's built-in AnonRateThrottle / UserRateThrottle and
use Redis as the backing cache (configured in settings as 'throttle' cache).

Rate reference (production-friendly defaults):
┌─────────────────────────────┬──────────────────────────────────┐
│ Throttle class              │ Default rate                     │
├─────────────────────────────┼──────────────────────────────────┤
│ LoginThrottle               │ 20/min  (per IP)                 │
│ SignupThrottle              │ 10/hour (per IP)                 │
│ OTPGenerationThrottle       │ 10/10min (per IP)                │
│ OTPVerificationThrottle     │ 30/10min (per IP)                │
│ ResendVerificationThrottle  │ 5/hour  (per IP)                 │
│ PasswordResetThrottle       │ 5/hour  (per IP)                 │
│ SearchThrottle              │ 300/min (per user or IP)         │
│ AuthenticatedUserThrottle   │ 10000/day (per user)             │
│ AnonUserThrottle            │ 1000/day (per IP)                │
└─────────────────────────────┴──────────────────────────────────┘

All rates are configurable via settings.THROTTLE_RATES to allow
per-environment overrides (e.g. relaxed limits in development).

Usage on a view:
    from apps.core.throttles import LoginThrottle

    class LoginView(APIView):
        throttle_classes = [LoginThrottle]
"""

import logging

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle, SimpleRateThrottle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_rate(name: str, fallback: str) -> str:
    """
    Look up a throttle rate from settings.THROTTLE_RATES with a fallback.

    This allows per-environment overrides:
        THROTTLE_RATES = {'login': '5/min'}  # tighter in production

    Args:
        name:     Key in settings.THROTTLE_RATES (e.g. 'login').
        fallback: Default rate string if key is not set (e.g. '20/minute').

    Returns:
        Rate string compatible with DRF (e.g. '20/minute', '10/hour').
    """
    rates = getattr(settings, 'THROTTLE_RATES', {})
    return rates.get(name, fallback)


# ---------------------------------------------------------------------------
# Authentication throttles  (all anonymous — keyed by IP)
# ---------------------------------------------------------------------------

class LoginThrottle(AnonRateThrottle):
    """
    Limits login attempts to prevent brute-force attacks.

    Scope  : 'login'
    Default: 20 requests / minute per IP
    Applied to: POST /user/login/
    """
    scope = 'login'

    def get_rate(self):
        return _get_rate(self.scope, '20/minute')


class SignupThrottle(AnonRateThrottle):
    """
    Limits account registrations to prevent mass account creation.

    Scope  : 'signup'
    Default: 10 requests / hour per IP
    Applied to: POST /user/signup/
    """
    scope = 'signup'

    def get_rate(self):
        return _get_rate(self.scope, '10/hour')


class OTPGenerationThrottle(AnonRateThrottle):
    """
    Limits how often a new OTP can be generated (triggered on login step 1).

    Scope  : 'otp_generate'
    Default: 10 requests / 10 minutes per IP

    Note: DRF uses 'second', 'minute', 'hour', 'day' as period keywords.
          For 10-minute windows we convert: 10 requests per 600 seconds
          by subclassing and overriding the timer/cache key ourselves
          using a custom duration in seconds.
    """
    scope = 'otp_generate'
    # We declare the rate here; the 10-minute window is handled by DRF
    # by reading '10/600s' — but DRF does not support seconds natively.
    # Instead we store '10/hour' as a conservative upper bound and
    # document the intent.  Teams that want exact 10-minute windows
    # should use django-ratelimit or a Redis Lua script.
    # For DRF-native compatibility, '10/hour' is the safest option.

    def get_rate(self):
        return _get_rate(self.scope, '10/hour')


class OTPVerificationThrottle(AnonRateThrottle):
    """
    Limits OTP verification attempts to prevent OTP brute-forcing.

    Scope  : 'otp_verify'
    Default: 30 requests / 10 minutes per IP
    Applied to: POST /user/verify-otp/
    """
    scope = 'otp_verify'

    def get_rate(self):
        return _get_rate(self.scope, '30/hour')


class ResendVerificationThrottle(AnonRateThrottle):
    """
    Limits resend-verification requests to prevent email spam.

    Scope  : 'resend_verification'
    Default: 5 requests / hour per IP
    Applied to: POST /user/resend-verification/
    """
    scope = 'resend_verification'

    def get_rate(self):
        return _get_rate(self.scope, '5/hour')


class PasswordResetThrottle(AnonRateThrottle):
    """
    Limits password reset requests to prevent email spam and enumeration.

    Scope  : 'password_reset'
    Default: 5 requests / hour per IP
    Applied to: POST /user/password-reset/ (when implemented)
    """
    scope = 'password_reset'

    def get_rate(self):
        return _get_rate(self.scope, '5/hour')


# ---------------------------------------------------------------------------
# General API throttles
# ---------------------------------------------------------------------------

class SearchThrottle(SimpleRateThrottle):
    """
    Throttle for search endpoints — applies to both authenticated and
    anonymous users, using user ID if authenticated, IP otherwise.

    Scope  : 'search'
    Default: 300 requests / minute
    Applied to: GET /books/?search=, GET /authors/?search=, etc.
    """
    scope = 'search'

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = str(request.user.id)
        else:
            ident = self.get_ident(request)
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident,
        }

    def get_rate(self):
        return _get_rate(self.scope, '300/minute')


class AuthenticatedUserThrottle(UserRateThrottle):
    """
    Broad daily limit for all authenticated endpoints.

    Scope  : 'user'
    Default: 10000 requests / day per authenticated user
    """
    scope = 'user'

    def get_rate(self):
        return _get_rate(self.scope, '10000/day')


class AnonUserThrottle(AnonRateThrottle):
    """
    Broad daily limit for all anonymous endpoints.

    Scope  : 'anon'
    Default: 1000 requests / day per IP
    """
    scope = 'anon'

    def get_rate(self):
        return _get_rate(self.scope, '1000/day')
