"""
apps/users/emails.py

All transactional email sends for the users module.
Uses Django's template system for HTML bodies.
Sending is handled by the configured EMAIL_BACKEND:
  - development : console (printed to stdout)
  - production  : anymail SendGrid
"""

import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .tokens import make_verification_link

logger = logging.getLogger(__name__)


def send_verification_email(user):
    """
    Send the email verification link to a newly registered user.
    """
    verification_url = make_verification_link(user)
    expiry_hours     = settings.EMAIL_VERIFICATION_EXPIRY_MINUTES // 60

    context = {
        "first_name":       user.first_name,
        "verification_url": verification_url,
        "expiry_hours":     expiry_hours,
        "year":             datetime.utcnow().year,
    }

    html_body  = render_to_string("emails/verification_email.html", context)
    plain_body = (
        f"Hi {user.first_name},\n\n"
        f"Please verify your email by visiting:\n{verification_url}\n\n"
        f"This link expires in {expiry_hours} hours."
    )

    _send(
        subject="Verify your email — Enterprise Book Store",
        plain_body=plain_body,
        html_body=html_body,
        to_email=user.email,
    )


def send_otp_email(user, otp: str):
    """
    Send the login OTP code to the user.
    """
    context = {
        "first_name":     user.first_name,
        "otp":            otp,
        "expiry_minutes": settings.OTP_EXPIRY_MINUTES,
        "year":           datetime.utcnow().year,
    }

    html_body  = render_to_string("emails/otp_email.html", context)
    plain_body = (
        f"Hi {user.first_name},\n\n"
        f"Your login OTP is: {otp}\n"
        f"It expires in {settings.OTP_EXPIRY_MINUTES} minutes.\n\n"
        f"Never share this code with anyone."
    )

    _send(
        subject="Your login OTP — Enterprise Book Store",
        plain_body=plain_body,
        html_body=html_body,
        to_email=user.email,
    )


def send_reminder_email(to_email: str, subject: str, body: str):
    """
    Generic reminder email triggered by the cron endpoint.

    Args:
        to_email : recipient address
        subject  : email subject line
        body     : plain-text or simple HTML body
    """
    context = {
        "subject": subject,
        "body":    body,
        "year":    datetime.utcnow().year,
    }

    html_body = render_to_string("emails/reminder_email.html", context)

    _send(
        subject=subject,
        plain_body=body,
        html_body=html_body,
        to_email=to_email,
    )


# ============================================================================
# Internal helper
# ============================================================================

def _send(subject: str, plain_body: str, html_body: str, to_email: str):
    """
    Build and dispatch an EmailMultiAlternatives message.
    Logs errors but does not raise — callers handle the UX separately.
    """
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()
        logger.info("Email sent: subject='%s' to='%s'", subject, to_email)
    except Exception as exc:
        logger.error(
            "Failed to send email: subject='%s' to='%s' error=%s",
            subject, to_email, exc,
        )
        raise
