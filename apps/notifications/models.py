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
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    # TODO: Add action_url for deep-linking

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.notif_type} → {self.user.email}'
