"""
apps/users/tokens.py

Email verification tokens and OTP management.

Email verification:
    Uses Django's PasswordResetTokenGenerator — signed, time-limited,
    invalidated the moment is_email_verified flips to True.

OTP:
    Random numeric code stored in Redis with a TTL.
    Key: otp:<user_id>
    Single-use — deleted from Redis on first successful verify.

Errors:
    All Redis failures raise ServiceUnavailableError so the API returns 503
    instead of a generic 500, telling the client the issue is temporary.
"""
import logging
import random
import string

import redis as redis_lib
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.core.exceptions import ServiceUnavailableError, TokenError as BookstoreTokenError

logger = logging.getLogger(__name__)


# ============================================================================
# Email verification token
# ============================================================================

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token is invalidated as soon as is_email_verified becomes True.
    Inherits Django's timeout from PASSWORD_RESET_TIMEOUT (default 3 days).
    """

    def _make_hash_value(self, user, timestamp):
        return (
            str(user.pk)
            + str(timestamp)
            + str(user.is_email_verified)
        )


_email_verification_token = EmailVerificationTokenGenerator()


def make_verification_link(user) -> str:
    """
    Build the full email verification URL.

    Returns:
        str: URL like https://app.vercel.app/verify-email?uid=<b64>&token=<token>
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = _email_verification_token.make_token(user)
    base = settings.FRONTEND_URL.rstrip("/")

    url = f"{base}/verify-email?uid={uid}&token={token}"
    logger.debug(
        "Generated verification link for user_id=%s (uid=%s)", user.id, uid
    )
    return url


def verify_email_token(uidb64: str, token: str):
    """
    Validate a verification link.

    Returns:
        User: the user whose token matched.

    Raises:
        BookstoreTokenError: if the uid is invalid or the token is expired/wrong.
    """
    from apps.users.models import User

    # Decode uid
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError) as exc:
        logger.warning(
            "Email verification failed — invalid uid='%s': %s", uidb64, exc
        )
        raise BookstoreTokenError("Invalid verification link.") from exc

    # Check token validity
    if not _email_verification_token.check_token(user, token):
        logger.warning(
            "Email verification failed — invalid/expired token for user_id=%s", user.id
        )
        raise BookstoreTokenError("Verification link has expired or is invalid.")

    logger.info("Email verification token valid for user_id=%s", user.id)
    return user


# ============================================================================
# Redis client (lazy singleton)
# ============================================================================

_redis_client = None


def _get_redis():
    """
    Return a lazily initialised Redis client.

    Raises:
        ServiceUnavailableError: if Redis cannot be reached.
    """
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = redis_lib.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Ping to validate the connection on first use
            _redis_client.ping()
            logger.info("Redis connection established at %s", settings.REDIS_URL)
        except redis_lib.RedisError as exc:
            _redis_client = None  # don't cache a broken client
            logger.error(
                "Redis connection failed at '%s': %s",
                settings.REDIS_URL, exc, exc_info=True,
            )
            raise ServiceUnavailableError(
                "OTP service is temporarily unavailable. Please try again."
            ) from exc

    return _redis_client


def _otp_redis_key(user_id: str) -> str:
    return f"otp:{user_id}"


# ============================================================================
# OTP helpers
# ============================================================================

def generate_otp(user) -> str:
    """
    Generate a random numeric OTP, store it in Redis with TTL, and return it.
    Any existing OTP for this user is overwritten.

    Returns:
        str: the generated OTP code.

    Raises:
        ServiceUnavailableError: if Redis is unreachable.
    """
    length = settings.OTP_LENGTH
    expiry = settings.OTP_EXPIRY_MINUTES * 60  # convert to seconds

    otp = "".join(random.choices(string.digits, k=length))
    key = _otp_redis_key(str(user.id))

    try:
        r = _get_redis()
        r.setex(key, expiry, otp)
        logger.info(
            "OTP generated for user_id=%s (ttl=%ds)", user.id, expiry
        )
    except ServiceUnavailableError:
        raise
    except redis_lib.RedisError as exc:
        logger.error(
            "Redis write failed for OTP user_id=%s: %s",
            user.id, exc, exc_info=True,
        )
        raise ServiceUnavailableError(
            "OTP service is temporarily unavailable. Please try again."
        ) from exc

    return otp


def verify_otp(user, otp: str) -> bool:
    """
    Validate OTP against Redis. Deletes the key on success (single-use).

    Returns:
        True if the OTP matches, False if wrong or expired.

    Raises:
        ServiceUnavailableError: if Redis is unreachable.
    """
    key = _otp_redis_key(str(user.id))

    try:
        r = _get_redis()
        stored = r.get(key)
    except ServiceUnavailableError:
        raise
    except redis_lib.RedisError as exc:
        logger.error(
            "Redis read failed for OTP user_id=%s: %s",
            user.id, exc, exc_info=True,
        )
        raise ServiceUnavailableError(
            "OTP service is temporarily unavailable. Please try again."
        ) from exc

    if stored is None:
        logger.info("OTP expired or not found for user_id=%s", user.id)
        return False

    if stored == otp:
        try:
            r.delete(key)
        except redis_lib.RedisError:
            # Non-critical — OTP will expire naturally via TTL
            logger.warning("Could not delete OTP key after verification user_id=%s", user.id)

        logger.info("OTP verified successfully for user_id=%s", user.id)
        return True

    logger.warning("Incorrect OTP attempt for user_id=%s", user.id)
    return False
