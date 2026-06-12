"""
apps/users/emails.py

All transactional email sends for the users module.

Backends:
  - development : console (stdout) — no real email sent
  - production  : anymail / SendGrid

Every function logs what it is about to send, logs success, and on failure
logs the full exception traceback before re-raising EmailDeliveryError so
callers get a clean, typed exception instead of a bare Exception.
"""
import logging
from datetime import datetime, timezone

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string, TemplateDoesNotExist

from apps.core.exceptions import EmailDeliveryError
from .tokens import make_verification_link

logger = logging.getLogger(__name__)


# ============================================================================
# Public API
# ============================================================================

def send_verification_email(user):
    """
    Send the email verification link to a newly registered user.

    Raises:
        EmailDeliveryError: if the email backend fails to dispatch.
    """
    logger.info(
        "Sending verification email to '%s' (user_id=%s)",
        user.email, user.id,
    )

    try:
        verification_url = make_verification_link(user)
    except Exception as exc:
        logger.error(
            "Failed to generate verification link for user_id=%s: %s",
            user.id, exc, exc_info=True,
        )
        raise EmailDeliveryError(
            "Could not generate verification link. Please try again."
        ) from exc

    expiry_hours = settings.EMAIL_VERIFICATION_EXPIRY_MINUTES // 60

    context = {
        "first_name": user.first_name,
        "verification_url": verification_url,
        "expiry_hours": expiry_hours,
        "year": datetime.now(timezone.utc).year,
    }

    _dispatch(
        subject="Verify your email — Enterprise Book Store",
        plain_body=(
            f"Hi {user.first_name},\n\n"
            f"Please verify your email by visiting:\n{verification_url}\n\n"
            f"This link expires in {expiry_hours} hours."
        ),
        template="emails/verification_email.html",
        context=context,
        to_email=user.email,
    )


def send_otp_email(user, otp: str):
    """
    Send the login OTP to the user.

    Raises:
        EmailDeliveryError: if the email backend fails to dispatch.
    """
    logger.info(
        "Sending OTP email to '%s' (user_id=%s)",
        user.email, user.id,
    )

    context = {
        "first_name": user.first_name,
        "otp": otp,
        "expiry_minutes": settings.OTP_EXPIRY_MINUTES,
        "year": datetime.now(timezone.utc).year,
    }

    _dispatch(
        subject="Your login OTP — Enterprise Book Store",
        plain_body=(
            f"Hi {user.first_name},\n\n"
            f"Your login OTP is: {otp}\n"
            f"It expires in {settings.OTP_EXPIRY_MINUTES} minutes.\n\n"
            "Never share this code with anyone."
        ),
        template="emails/otp_email.html",
        context=context,
        to_email=user.email,
    )


def send_reminder_email(to_email: str, subject: str, body: str):
    """
    Generic reminder email triggered by the cron endpoint.

    Raises:
        EmailDeliveryError: if the email backend fails to dispatch.
    """
    logger.info("Sending reminder email to '%s' subject='%s'", to_email, subject)

    context = {
        "subject": subject,
        "body": body,
        "year": datetime.now(timezone.utc).year,
    }

    _dispatch(
        subject=subject,
        plain_body=body,
        template="emails/reminder_email.html",
        context=context,
        to_email=to_email,
    )


# ============================================================================
# Internal helper
# ============================================================================

def _dispatch(
    subject: str,
    plain_body: str,
    template: str,
    context: dict,
    to_email: str,
):
    """
    Render the HTML template and dispatch the email.

    Logs the full exception traceback on failure and raises EmailDeliveryError.
    """
    # Render HTML — log clearly if the template is missing
    try:
        html_body = render_to_string(template, context)
    except TemplateDoesNotExist:
        logger.error(
            "Email template not found: '%s'. Falling back to plain text.", template,
        )
        html_body = f"<pre>{plain_body}</pre>"
    except Exception as exc:
        logger.error(
            "Failed to render email template '%s': %s",
            template, exc, exc_info=True,
        )
        html_body = f"<pre>{plain_body}</pre>"

    # Dispatch
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send()

        logger.info(
            "Email dispatched | subject='%s' to='%s' backend=%s",
            subject, to_email, settings.EMAIL_BACKEND,
        )

    except Exception as exc:
        logger.error(
            "Email dispatch FAILED | subject='%s' to='%s' backend=%s | error: %s",
            subject, to_email, settings.EMAIL_BACKEND, exc,
            exc_info=True,
        )
        raise EmailDeliveryError(
            f"Failed to send email to {to_email}. Please try again later."
        ) from exc
