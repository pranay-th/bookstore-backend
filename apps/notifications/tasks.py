"""
apps/notifications/tasks.py

Celery tasks for the notifications domain.

Autodiscovered by config/celery.py. Tasks here run in the Celery worker (not
the request/response cycle), so slow or scheduled work — scheduled-message
dispatch, and later the delivery-automation bots — doesn't block the web app.

Use @shared_task so these don't import the Celery app directly (keeps the app
decoupled and testable). Results are ignored by default (see CELERY settings);
opt in with ignore_result=False only when a return value is actually consumed.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="apps.notifications.dispatch_due_scheduled_messages",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def dispatch_due_scheduled_messages(self):
    """Send every pending ScheduledMessage whose time has passed.

    Mirrors the logic of the cron HTTP endpoint (CronDispatchScheduledView) but
    runs in the worker so it can be triggered by Celery beat instead of an
    external pinger. Safe to run alongside the HTTP cron — both operate on the
    same 'pending + due' filter and mark rows as they go.
    """
    from django.utils import timezone

    from .models import ScheduledMessage
    from .personalization import personalize_message
    from apps.users.emails import send_reminder_email

    now = timezone.now()
    due = ScheduledMessage.objects.filter(status="pending", scheduled_for__lte=now)

    sent = 0
    failed = 0
    for message in due:
        message.attempts += 1
        try:
            subject, body = personalize_message(message)
            send_reminder_email(to_email=message.recipient, subject=subject, body=body)
            message.status = "sent"
            message.sent_at = timezone.now()
            message.error = ""
            message.save(
                update_fields=["status", "sent_at", "error", "attempts", "updated_at"]
            )
            sent += 1
        except Exception as exc:  # noqa: BLE001
            message.error = str(exc)
            # Mark failed only after 3 attempts; otherwise leave pending to retry.
            if message.attempts >= 3:
                message.status = "failed"
                logger.error("ScheduledMessage %s permanently failed: %s", message.id, exc)
            message.save(update_fields=["status", "error", "attempts", "updated_at"])
            failed += 1

    logger.info("dispatch_due_scheduled_messages: sent=%d failed=%d", sent, failed)
    return {"sent": sent, "failed": failed}
