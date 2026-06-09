"""
apps/core/responses.py

Standardised API response helpers.

Every endpoint returns:
    {
        "status":      "success" | "failed",
        "details":     "human-readable message",
        "data":        { ... } or [ ... },
        "status_code": <http status code>
    }
"""

from rest_framework.response import Response


def success_response(data=None, message="Request was successful.", status_code=200):
    """
    Return a standardised success envelope.

    Args:
        data        : The response payload (dict or list). Defaults to {}.
        message     : A short human-readable description.
        status_code : HTTP status code (default 200).

    Example:
        return success_response(
            data=serializer.data,
            message="User created successfully.",
            status_code=201,
        )
    """
    return Response(
        {
            "status":      "success",
            "details":     message,
            "data":        data if data is not None else {},
            "status_code": status_code,
        },
        status=status_code,
    )


def error_response(message="An error occurred.", status_code=400, data=None):
    """
    Return a standardised error envelope.

    Args:
        message     : A short human-readable description of what went wrong.
                      Can also be a list of error strings.
        status_code : HTTP status code (default 400).
        data        : Optional extra payload. Defaults to {}.

    Example:
        return error_response(
            message="Email already registered.",
            status_code=409,
        )
    """
    return Response(
        {
            "status":      "failed",
            "details":     message,
            "data":        data if data is not None else {},
            "status_code": status_code,
        },
        status=status_code,
    )
