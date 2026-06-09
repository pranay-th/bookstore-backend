"""
apps/users/tokens.py

Email verification tokens and OTP management.

Email verification:
    Uses Django's PasswordResetTokenGenerator to create a signed,
    time-limited token bound to the user's current state.
    Token is included in the verification link sent via email.

OTP (Login second-factor):
    6-digit (or configured length) TOTP-style code stored in Redis
    with a configurable TTL (default 10 minutes).
    Key pattern: otp:<user_id>
"""

import random
import string
import logging

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str

import redis
from django.conf import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Email verification token
# ============================================================================

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Extends Django's PasswordResetTokenGenerator so the token is
    invalidated as soon as is_email_verified becomes True.
    """

    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk)
            + str(timestamp)
            + str(user.is_email_verified)
        )


email_verification_token = EmailVerificationTokenGenerator()


def make_verification_link(user, request=None):
    """
    Build the full email verification URL to send to the user.

    Returns a URL like:
        https://yourapp.vercel.app/verify-email?uid=<uid>&token=<token>
    """
    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    base  = settings.FRONTEND_URL.rstrip('/')
    return f"{base}/verify-email?uid={uid}&token={token}"


def verify_email_token(uidb64, token):
    """
    Validate a verification link.

    Returns the User on success, None on failure.
    """
    from apps.users.models import User

    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None

    if not email_verification_token.check_token(user, token):
        return None

    return user


# ============================================================================
# Redis client (lazy singleton)
# ============================================================================

_redis_client = None


def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
    return _redis_client


# ============================================================================
# OTP helpers
# ============================================================================

def _otp_key(user_id: str) -> str:
    return f"otp:{user_id}"


def generate_otp(user) -> str:
    """
    Generate a random numeric OTP, store it in Redis with TTL, and return it.
    Any previous OTP for the same user is overwritten.
    """
    length  = settings.OTP_LENGTH
    expiry  = settings.OTP_EXPIRY_MINUTES * 60  # seconds

    otp = "".join(random.choices(string.digits, k=length))

    try:
        r = get_redis()
        r.setex(_otp_key(str(user.id)), expiry, otp)
    except redis.RedisError as exc:
        logger.error("Redis error generating OTP for user %s: %s", user.id, exc)
        raise

    return otp


def verify_otp(user, otp: str) -> bool:
    """
    Check the OTP against the value stored in Redis.
    Deletes the key on a successful match (single-use).

    Returns True if valid, False otherwise.
    """
    try:
        r   = get_redis()
        key = _otp_key(str(user.id))
        stored = r.get(key)
    except redis.RedisError as exc:
        logger.error("Redis error verifying OTP for user %s: %s", user.id, exc)
        return False

    if stored is None:
        return False  # expired or never generated

    if stored == otp:
        r.delete(key)  # single-use
        return True

    return False
