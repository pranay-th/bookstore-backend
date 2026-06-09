"""
apps/core/responses.py

Standardised API response helpers.

Success envelope:
    {
        "status": { "success": true,  "code": 200, "message": "Login successful." },
        "data":   { ... } | null
    }

Error envelope:
    {
        "status": { "success": false, "code": 400, "message": "Validation failed." },
        "data":   null,
        "errors": { "email": ["This field is required."] } | null
    }
"""

from rest_framework.response import Response


def success_response(data=None, message="Request was successful.", status_code=200):
    """
    Return a standardised success envelope.

    Args:
        data        : The response payload (dict or list). Defaults to None.
        message     : A short human-readable description.
        status_code : HTTP status code (default 200).

    Example:
        return success_response(
            data={"id": "abc", "email": "user@example.com"},
            message="Login successful.",
            status_code=200,
        )
    """
    return Response(
        {
            "status": {
                "success": True,
                "code":    status_code,
                "message": message,
            },
            "data": data,
        },
        status=status_code,
    )


def error_response(message="An error occurred.", errors=None, status_code=400):
    """
    Return a standardised error envelope.

    Args:
        message     : A short human-readable description of what went wrong.
        errors      : Dict of field-level errors, or None for non-validation errors.
        status_code : HTTP status code (default 400).

    Example:
        return error_response(
            message="Validation failed.",
            errors={"email": ["This field is required."]},
            status_code=400,
        )
    """
    return Response(
        {
            "status": {
                "success": False,
                "code":    status_code,
                "message": message,
            },
            "data":   None,
            "errors": errors,
        },
        status=status_code,
    )
