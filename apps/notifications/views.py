"""notifications/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Notification
from .serializers import NotificationSerializer

class NotificationViewSet(viewsets.ModelViewSet):
    # TODO: Restrict to the authenticated user's notifications
    # TODO: Add mark_read action: PATCH /notifications/:id/read/
    # TODO: Add mark_all_read action
    queryset         = Notification.objects.all()
    serializer_class = NotificationSerializer
