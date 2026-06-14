from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet,
    ScheduledMessageViewSet,
    CronDispatchScheduledView,
)

router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notification')
router.register('scheduled-messages', ScheduledMessageViewSet, basename='scheduled-message')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'cron/dispatch-scheduled/',
        CronDispatchScheduledView.as_view(),
        name='cron-dispatch-scheduled',
    ),
]
