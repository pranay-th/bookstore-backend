"""
apps/core/exceptions.py

Global DRF exception handler.

Catches ALL exceptions — validation errors, auth errors, 404s, 500s, etc. —
and wraps them in the standard envelope.

Success envelope:
    {
        "status": { "success": true,  "code": 200, "message": "..." },
        "data":   { ... }
    }

Error envelope:
    {
        "status": { "success": false, "code": 400, "message": "..." },
        "data":   null,
        "errors": { "field": ["msg", ...] } | null
    }
"""

from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    # Let DRF build its default response first
    response = exception_handler(exc, context)

    if response is None:
        return None

    http_code = response.status_code
    data = response.data
    message = None
    errors = None

    if isinstance(data, dict):
        if "detail" in data:
            # AuthenticationFailed, PermissionDenied, NotFound, etc.
            message = str(data["detail"])

        elif "non_field_errors" in data:
            # Non-field ValidationError (e.g. invalid credentials)
            non_field = data["non_field_errors"]
            message = non_field[0] if len(non_field) == 1 else " ".join(str(e) for e in non_field)

        else:
            # Field-level ValidationError — preserve as errors dict
            message = "Validation failed."
            errors = {
                field: [str(e) for e in errs] if isinstance(errs, list) else [str(errs)]
                for field, errs in data.items()
            }

    elif isinstance(data, list):
        message = data[0] if len(data) == 1 else " ".join(str(e) for e in data)

    else:
        message = str(data)

    # Fallback for empty/generic messages
    fallback_messages = {
        400: "Bad request.",
        401: "Authentication required.",
        403: "You do not have permission to perform this action.",
        404: "The requested resource was not found.",
        405: "Method not allowed.",
        429: "Too many requests. Please slow down.",
        500: "An unexpected error occurred. Please try again later.",
    }

    if not message or message in ("", "null", "None"):
        message = fallback_messages.get(http_code, "An error occurred.")

    response.data = {
        "status": {
            "success": False,
            "code":    http_code,
            "message": message,
        },
        "data":   None,
        "errors": errors,
    }

    return response
