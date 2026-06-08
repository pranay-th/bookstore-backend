"""
analytics/models.py — Phase 0 placeholder.
Heavy analytics delegated to FastAPI microservice.
This model stores lightweight event stubs only.
TODO: Forward to FastAPI analytics service via async task.
"""
import uuid
from django.db import models
from django.conf import settings


class PageView(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    path       = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # TODO: Add referrer, session_id, book_id for richer analytics

    class Meta:
        db_table = 'analytics_pageviews'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.path} @ {self.created_at}'
