"""
notifications/views.py

Endpoints:
  GET/POST/PATCH/DELETE  /api/scheduled-messages/        Admin-managed scheduled messages
  POST                   /api/scheduled-messages/:id/cancel/   Cancel a pending message
  POST                   /api/cron/dispatch-scheduled/   Cron: send all due messages
"""
import hmac
import logging

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from apps.core.responses import error_response, success_response
from apps.users.emails import send_reminder_email

from .models import Notification, ScheduledMessage
from .personalization import personalize_message
from .serializers import NotificationSerializer, ScheduledMessageSerializer

logger = logging.getLogger(__name__)

# How many times to retry a failing message before giving up
MAX_DISPATCH_ATTEMPTS = 3


class NotificationViewSet(ModelViewSet):
    """A user's own in-app notifications."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data,
            message="Notifications retrieved successfully.",
        )

    @action(detail=True, methods=["patch"])
    def read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return success_response(
            data=NotificationSerializer(notif).data,
            message="Notification marked as read.",
        )

    @action(detail=False, methods=["patch"], url_path="read-all")
    def read_all(self, request):
        count = self.get_queryset().filter(is_read=False).update(is_read=True)
        return success_response(
            data={"updated": count},
            message=f"{count} notification(s) marked as read.",
        )


class ScheduledMessageViewSet(ModelViewSet):
    """
    Admin-only management of scheduled email messages.

    Create a message with a future `scheduled_for`; a cron job dispatches it
    once that time passes. Pending messages can be canceled before they send.
    """
    serializer_class = ScheduledMessageSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        queryset = ScheduledMessage.objects.all()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @extend_schema(
        summary="Cancel a pending scheduled message",
        responses={200: OpenApiResponse(description="Message canceled")},
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        message = self.get_object()
        if message.status != "pending":
            return error_response(
                f"Only pending messages can be canceled (current status: {message.status}).",
                status_code=400,
            )
        message.status = "canceled"
        message.save(update_fields=["status", "updated_at"])
        logger.info("Scheduled message %s canceled by user_id=%s", message.id, request.user.id)
        return success_response(
            data=ScheduledMessageSerializer(message).data,
            message="Scheduled message canceled.",
        )


class CronDispatchScheduledView(APIView):
    """
    Cron endpoint — dispatches every pending message whose scheduled time
    has passed. Authenticated via the X-Cron-Secret header.
    """
    permission_classes = [AllowAny]  # Auth via X-Cron-Secret header

    @extend_schema(
        summary="Cron — dispatch due scheduled messages",
        description=(
            "Sends all pending messages whose `scheduled_for` is in the past.\n\n"
            "**Authentication:** `X-Cron-Secret` header must match `CRON_SECRET_KEY`."
        ),
        responses={200: OpenApiResponse(description="Dispatch run complete")},
    )
    def post(self, request):
        secret = request.headers.get("X-Cron-Secret", "")
        if not settings.CRON_SECRET_KEY or not hmac.compare_digest(
            secret, settings.CRON_SECRET_KEY
        ):
            logger.warning(
                "Scheduled-dispatch cron called with invalid secret from IP=%s",
                request.META.get("REMOTE_ADDR"),
            )
            return error_response("Unauthorized.", status_code=401)

        now = timezone.now()
        due = ScheduledMessage.objects.filter(
            status="pending",
            scheduled_for__lte=now,
        )

        sent = 0
        failed = 0

        for message in due:
            message.attempts += 1
            try:
                # Personalize subject + body per recipient before sending
                subject, body = personalize_message(message)
                send_reminder_email(
                    to_email=message.recipient,
                    subject=subject,
                    body=body,
                )
                message.status = "sent"
                message.sent_at = timezone.now()
                message.error = ""
                message.save(update_fields=["status", "sent_at", "error", "attempts", "updated_at"])
                sent += 1
            except Exception as exc:  # noqa: BLE001
                # Mark failed only after exhausting retries; otherwise leave
                # pending so the next cron run tries again.
                message.error = str(exc)
                if message.attempts >= MAX_DISPATCH_ATTEMPTS:
                    message.status = "failed"
                    logger.error(
                        "Scheduled message %s permanently failed after %d attempts: %s",
                        message.id, message.attempts, exc,
                    )
                else:
                    logger.warning(
                        "Scheduled message %s dispatch attempt %d failed: %s",
                        message.id, message.attempts, exc,
                    )
                message.save(update_fields=["status", "error", "attempts", "updated_at"])
                failed += 1

        logger.info("Scheduled dispatch run complete: sent=%d failed=%d", sent, failed)
        return success_response(
            data={"sent": sent, "failed": failed},
            message=f"{sent} message(s) sent, {failed} failed.",
        )
