"""
apps/core/responses.py

Standardised API response helpers.

Every response — success or error — follows the same shape:
    {
        "status": { "success": true|false, "message": "<str>" },
        "data":   { ... } | null
    }
"""
from rest_framework.response import Response


def success_response(data=None, message="Request was successful.", status_code=200):
    """
    Return a standardised success envelope.

    Args:
        data        : Response payload (dict or list). Defaults to None.
        message     : Short human-readable description.
        status_code : HTTP status code (default 200).
    """
    return Response(
        {
            "status": {
                "success": True,
                "message": message,
            },
            "data": data,
        },
        status=status_code,
    )


def error_response(message="An error occurred.", status_code=400):
    """
    Return a standardised error envelope.

    Args:
        message     : Short human-readable description of what went wrong.
        status_code : HTTP status code (default 400).
    """
    return Response(
        {
            "status": {
                "success": False,
                "message": message,
            },
            "data": None,
        },
        status=status_code,
    )
