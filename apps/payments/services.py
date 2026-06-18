"""
payments/services.py

Thin wrapper around the Razorpay SDK. Centralises client creation, order
creation and signature verification so the views stay focused on request
handling and the standard response envelope.

All failures surface as ``PaymentServiceError`` so callers can translate them
into a clean response instead of leaking SDK exceptions.

Configuration (settings):
    RAZORPAY_KEY_ID
    RAZORPAY_KEY_SECRET
    RAZORPAY_CURRENCY   (default 'INR')
"""
import logging

import razorpay
from django.conf import settings

logger = logging.getLogger(__name__)


class PaymentServiceError(Exception):
    """Raised when Razorpay is misconfigured or an API call fails."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def is_configured() -> bool:
    """True when both Razorpay keys are present."""
    return bool(
        getattr(settings, "RAZORPAY_KEY_ID", "")
        and getattr(settings, "RAZORPAY_KEY_SECRET", "")
    )


def _client() -> razorpay.Client:
    if not is_configured():
        raise PaymentServiceError(
            "Payments are not configured (Razorpay keys missing).",
            status_code=503,
        )
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def to_paise(amount) -> int:
    """Convert a rupee Decimal/float to integer paise (Razorpay's unit)."""
    return int(round(float(amount) * 100))


def create_order(amount, receipt: str, notes: dict | None = None) -> dict:
    """
    Create a Razorpay order.

    Args:
        amount:  Amount in rupees (Decimal/float). Converted to paise here.
        receipt: A short receipt identifier (e.g. the bookstore order id).
        notes:   Optional metadata dict stored on the Razorpay order.

    Returns the Razorpay order dict (contains 'id', 'amount', 'currency', ...).
    """
    client = _client()
    currency = getattr(settings, "RAZORPAY_CURRENCY", "INR")
    try:
        return client.order.create({
            "amount": to_paise(amount),
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,  # auto-capture on success
            "notes": notes or {},
        })
    except Exception as exc:  # razorpay raises various error types
        logger.exception("Razorpay order creation failed: %s", exc)
        raise PaymentServiceError(
            "Could not initiate payment. Please try again.",
            status_code=502,
        ) from exc


def verify_signature(razorpay_order_id: str, razorpay_payment_id: str,
                     razorpay_signature: str) -> bool:
    """
    Verify the payment signature returned by Razorpay Checkout.

    Returns True if the signature is valid, False otherwise. Never raises for
    a bad signature — only for a misconfigured client.
    """
    client = _client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    except Exception as exc:  # pragma: no cover - resilience path
        logger.warning("Razorpay signature verification error: %s", exc)
        return False
