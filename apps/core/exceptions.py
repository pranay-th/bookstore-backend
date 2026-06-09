"""
apps/core/exceptions.py

Global DRF exception handler.

Catches ALL exceptions — validation errors, auth errors, 404s, 500s, etc. —
and wraps them in the standard envelope:

    {
        "status":      "failed",
        "details":     <message or list of messages>,
        "data":        {},
        "status_code": <http status code>
    }
"""

from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from rest_framework import status


def custom_exception_handler(exc, context):
    # Let DRF build its default response first
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled server error — return 500
        return None

    http_code = response.status_code
    data = response.data

    # --- Flatten the error message into a clean string or list ---
    if isinstance(data, dict):
        # ValidationError with field errors e.g. {"email": ["already exists"]}
        # or non-field errors e.g. {"non_field_errors": ["Invalid credentials"]}
        if "detail" in data:
            # AuthenticationFailed, PermissionDenied, NotFound, etc.
            details = str(data["detail"])
        elif "non_field_errors" in data:
            errors = data["non_field_errors"]
            details = errors[0] if len(errors) == 1 else list(errors)
        else:
            # Field-level validation errors — collect all messages
            messages = []
            for field, errors in data.items():
                if isinstance(errors, list):
                    for err in errors:
                        messages.append(f"{field}: {err}")
                else:
                    messages.append(f"{field}: {errors}")
            details = messages[0] if len(messages) == 1 else messages
    elif isinstance(data, list):
        details = data[0] if len(data) == 1 else data
    else:
        details = str(data)

    # --- Map common HTTP codes to friendly messages when details is generic ---
    fallback_messages = {
        400: "Bad request.",
        401: "Authentication required.",
        403: "You do not have permission to perform this action.",
        404: "The requested resource was not found.",
        405: "Method not allowed.",
        429: "Too many requests. Please slow down.",
        500: "An unexpected error occurred. Please try again later.",
    }

    if not details or details in ("", "null", "None"):
        details = fallback_messages.get(http_code, "An error occurred.")

    response.data = {
        "status":      "failed",
        "details":     details,
        "data":        {},
        "status_code": http_code,
    }

    return response
