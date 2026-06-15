"""
apps/core/exceptions.py

Global DRF exception handler + custom exception classes.

Every error response follows the standard envelope:
    {
        "status": { "success": false, "message": "<str>" },
        "data":   null
    }

Custom exception classes defined here:
    BookstoreAPIError       — base for all custom exceptions
    AuthenticationError     — 401
    PermissionDeniedError   — 403
    NotFoundError           — 404
    ConflictError           — 409  (e.g. duplicate email)
    UnprocessableError      — 422  (semantic validation failure)
    ServiceUnavailableError — 503  (Redis down, email service down, etc.)
    RateLimitError          — 429
"""
import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# ============================================================================
# Custom exception classes
# ============================================================================

class BookstoreAPIError(APIException):
    """Base class for all custom Bookstore API exceptions."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A request error occurred."
    default_code = "error"


class AuthenticationError(BookstoreAPIError):
    """Raised when a user is not authenticated or credentials are invalid."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Authentication credentials were not provided or are invalid."
    default_code = "authentication_error"


class PermissionDeniedError(BookstoreAPIError):
    """Raised when a user does not have permission to perform an action."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class NotFoundError(BookstoreAPIError):
    """Raised when a requested resource does not exist."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "The requested resource was not found."
    default_code = "not_found"


class ConflictError(BookstoreAPIError):
    """Raised when a request conflicts with existing data (e.g. duplicate email)."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflict occurred with the current state of the resource."
    default_code = "conflict"


class UnprocessableError(BookstoreAPIError):
    """Raised when the request is well-formed but semantically invalid."""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The request could not be processed."
    default_code = "unprocessable"


class ServiceUnavailableError(BookstoreAPIError):
    """
    Raised when a downstream service (Redis, SendGrid, Neon) is unavailable.
    Returns 503 so the client knows to retry.
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "A required service is temporarily unavailable. Please try again."
    default_code = "service_unavailable"


class RateLimitError(BookstoreAPIError):
    """Raised when a client exceeds request limits."""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Too many requests. Please slow down."
    default_code = "rate_limit_exceeded"


class EmailDeliveryError(ServiceUnavailableError):
    """Raised specifically when an email cannot be dispatched."""
    default_detail = "Email could not be sent. Please try again later."
    default_code = "email_delivery_failed"


class OTPError(BookstoreAPIError):
    """Raised when OTP generation or verification fails."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "OTP operation failed."
    default_code = "otp_error"


class TokenError(BookstoreAPIError):
    """Raised when a JWT or verification token is invalid or expired."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Token is invalid or expired."
    default_code = "token_invalid"


class AccountDisabledError(BookstoreAPIError):
    """Raised when a user account has been deactivated."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This account has been disabled. Please contact support."
    default_code = "account_disabled"


class EmailNotVerifiedError(BookstoreAPIError):
    """Raised when a user tries to log in before verifying their email."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Email not verified. Please check your inbox for the verification link."
    default_code = "email_not_verified"


# ============================================================================
# Message map — maps HTTP codes to user-friendly fallback messages
# ============================================================================

_FALLBACK_MESSAGES = {
    400: "Invalid request data.",
    401: "Authentication required.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource was not found.",
    405: "Method not allowed.",
    409: "A conflict occurred with the current state of the resource.",
    422: "The request could not be processed due to semantic errors.",
    429: "Too many requests. Please slow down.",
    500: "An unexpected server error occurred. Please try again later.",
    502: "Bad gateway. Please try again.",
    503: "Service temporarily unavailable. Please try again later.",
}


# ============================================================================
# Global exception handler
# ============================================================================

def custom_exception_handler(exc, context):
    """
    Intercepts every exception DRF handles and wraps it in the standard envelope.

    Also logs:
      - 4xx at WARNING level with the view name and message
      - 5xx at ERROR level with full traceback
      - Unhandled exceptions at CRITICAL level
    """
    view_name = _get_view_name(context)

    # ── Let DRF build the default response first ──────────────────────────
    response = exception_handler(exc, context)

    if response is None:
        # DRF didn't handle it — this is an unhandled Python exception (500)
        logger.critical(
            "Unhandled exception in view '%s': %s",
            view_name,
            exc,
            exc_info=True,
        )
        return None

    http_code = response.status_code
    message = _extract_message(response.data, http_code)

    # ── Log based on severity ─────────────────────────────────────────────
    if http_code >= 500:
        logger.error(
            "Server error %s in '%s': %s",
            http_code, view_name, message,
            exc_info=exc,
        )
    elif http_code == 401:
        # 401s are noisy; log at debug
        logger.debug("Auth failure in '%s': %s", view_name, message)
    elif http_code >= 400:
        logger.warning(
            "Client error %s in '%s': %s",
            http_code, view_name, message,
        )

    response.data = {
        "status": {
            "success": False,
            "message": message,
        },
        "data": None,
    }

    return response


# ============================================================================
# Helpers
# ============================================================================

def _get_view_name(context):
    """Extract a readable view name from the exception context."""
    view = context.get("view")
    if view:
        return type(view).__name__
    return "unknown_view"


def _extract_message(data, http_code):
    """
    Extract a clean, user-readable message from DRF's raw error data.

    Priority:
        1. 'detail' key  — single string from most DRF exceptions
        2. 'non_field_errors' — validation errors not tied to a field
        3. Field-level errors — formatted as "field: message"
        4. Plain string / list
        5. Fallback by HTTP code
    """
    message = None

    if isinstance(data, dict):
        if "detail" in data:
            message = str(data["detail"])

        elif "non_field_errors" in data:
            errs = data["non_field_errors"]
            if isinstance(errs, list) and errs:
                message = str(errs[0])
            else:
                message = str(errs)

        else:
            # Field-level errors — show all fields so the client knows exactly what's wrong
            parts = []
            for field, errs in data.items():
                if isinstance(errs, list):
                    for err in errs:
                        parts.append(f"{field}: {err}")
                else:
                    parts.append(f"{field}: {errs}")
            if parts:
                message = " | ".join(parts)

    elif isinstance(data, list):
        message = str(data[0]) if data else None
    elif data is not None:
        message = str(data)

    # Apply fallback if message is empty or generic
    if not message or message.strip() in ("", "null", "None"):
        message = _FALLBACK_MESSAGES.get(http_code, "An error occurred.")

    return message
