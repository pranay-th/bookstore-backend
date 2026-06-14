"""
Tests for the scheduled message feature.
"""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import User
from .models import ScheduledMessage


@override_settings(CRON_SECRET_KEY="test-secret")
class ScheduledMessageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="Admin@123",
            first_name="Ad",
            last_name="Min",
            role="ADMIN",
            is_staff=True,
            is_superuser=True,
            is_email_verified=True,
        )

    def _future(self, minutes=60):
        return (timezone.now() + timedelta(minutes=minutes)).isoformat()

    def _past(self, minutes=60):
        return timezone.now() - timedelta(minutes=minutes)

    # ── creation / validation ────────────────────────────────────────────
    def test_admin_can_schedule_message(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(
            "/api/scheduled-messages/",
            {
                "recipient": "user@example.com",
                "subject": "Hello",
                "body": "A scheduled note.",
                "scheduled_for": self._future(),
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(ScheduledMessage.objects.count(), 1)
        msg = ScheduledMessage.objects.first()
        self.assertEqual(msg.status, "pending")
        self.assertEqual(msg.created_by, self.admin)

    def test_cannot_schedule_in_the_past(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(
            "/api/scheduled-messages/",
            {
                "recipient": "user@example.com",
                "subject": "Late",
                "body": "Too late.",
                "scheduled_for": (timezone.now() - timedelta(minutes=5)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(res.status_code, 400)

    def test_non_admin_cannot_access(self):
        customer = User.objects.create_user(
            email="cust@example.com", password="Cust@123",
            first_name="C", last_name="U", is_email_verified=True,
        )
        self.client.force_authenticate(customer)
        res = self.client.get("/api/scheduled-messages/")
        self.assertEqual(res.status_code, 403)

    # ── cancel ────────────────────────────────────────────────────────────
    def test_cancel_pending_message(self):
        self.client.force_authenticate(self.admin)
        msg = ScheduledMessage.objects.create(
            recipient="user@example.com", subject="S", body="B",
            scheduled_for=timezone.now() + timedelta(hours=1),
        )
        res = self.client.post(f"/api/scheduled-messages/{msg.id}/cancel/")
        self.assertEqual(res.status_code, 200)
        msg.refresh_from_db()
        self.assertEqual(msg.status, "canceled")

    # ── cron dispatch ─────────────────────────────────────────────────────
    @patch("apps.notifications.views.send_reminder_email")
    def test_cron_dispatches_due_messages_only(self, mock_send):
        due = ScheduledMessage.objects.create(
            recipient="due@example.com", subject="Due", body="B",
            scheduled_for=self._past(),
        )
        future = ScheduledMessage.objects.create(
            recipient="future@example.com", subject="Future", body="B",
            scheduled_for=timezone.now() + timedelta(hours=2),
        )

        res = self.client.post(
            "/api/cron/dispatch-scheduled/",
            HTTP_X_CRON_SECRET="test-secret",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["data"], {"sent": 1, "failed": 0})

        due.refresh_from_db()
        future.refresh_from_db()
        self.assertEqual(due.status, "sent")
        self.assertIsNotNone(due.sent_at)
        self.assertEqual(future.status, "pending")
        mock_send.assert_called_once()

    def test_cron_rejects_bad_secret(self):
        res = self.client.post(
            "/api/cron/dispatch-scheduled/",
            HTTP_X_CRON_SECRET="wrong",
        )
        self.assertEqual(res.status_code, 401)

    @patch(
        "apps.notifications.views.send_reminder_email",
        side_effect=Exception("smtp down"),
    )
    def test_failed_dispatch_stays_pending_until_max_attempts(self, mock_send):
        msg = ScheduledMessage.objects.create(
            recipient="x@example.com", subject="S", body="B",
            scheduled_for=self._past(),
        )
        # First two attempts: still pending (will retry next run)
        for expected_attempts in (1, 2):
            self.client.post(
                "/api/cron/dispatch-scheduled/", HTTP_X_CRON_SECRET="test-secret"
            )
            msg.refresh_from_db()
            self.assertEqual(msg.attempts, expected_attempts)
            self.assertEqual(msg.status, "pending")

        # Third attempt: permanently failed
        self.client.post(
            "/api/cron/dispatch-scheduled/", HTTP_X_CRON_SECRET="test-secret"
        )
        msg.refresh_from_db()
        self.assertEqual(msg.attempts, 3)
        self.assertEqual(msg.status, "failed")
        self.assertIn("smtp down", msg.error)
