"""
notifications/models.py — Phase 0 placeholder.
TODO: Implement in-app + email notifications triggered by order/payment events.
"""
import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('order_confirmed',  'Order Confirmed'),
        ('order_shipped',    'Order Shipped'),
        ('order_delivered',  'Order Delivered'),
        ('payment_received', 'Payment Received'),
        ('review_approved',  'Review Approved'),
        ('general',          'General'),
    ]

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notif_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    link       = models.CharField(max_length=255, blank=True, default='')
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.notif_type} → {self.user.email}'


class ScheduledMessage(models.Model):
    """
    A message queued to be sent (via email) at or after `scheduled_for`.

    Lifecycle:
        pending  → the message is waiting for its scheduled time
        sent     → successfully dispatched
        failed   → dispatch failed (see error field)
        canceled → canceled by an admin before it was sent

    A cron job calls the dispatch endpoint periodically; any pending message
    whose `scheduled_for` is in the past gets sent and marked accordingly.
    """

    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('sent',     'Sent'),
        ('failed',   'Failed'),
        ('canceled', 'Canceled'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient     = models.EmailField(help_text='Destination email address.')
    subject       = models.CharField(
        max_length=255,
        help_text='Supports tokens: {{first_name}}, {{last_name}}, {{full_name}}, {{email}}, {{role}}',
    )
    body          = models.TextField(
        help_text=(
            'Supports tokens: {{first_name}}, {{last_name}}, {{full_name}}, '
            '{{email}}, {{role}}. If no name token is present, a personalized '
            'greeting is prepended automatically.'
        ),
    )
    scheduled_for = models.DateTimeField(
        db_index=True,
        help_text='When the message should be sent (UTC).',
    )
    status        = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True
    )
    attempts      = models.PositiveIntegerField(default=0)
    error         = models.TextField(blank=True, default='')
    sent_at       = models.DateTimeField(null=True, blank=True)

    # Optional link to a user (for reminders targeting a specific account)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scheduled_messages',
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_scheduled_messages',
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scheduled_messages'
        ordering = ['scheduled_for']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
        ]

    def __str__(self):
        return f'{self.subject} → {self.recipient} @ {self.scheduled_for:%Y-%m-%d %H:%M} ({self.status})'
