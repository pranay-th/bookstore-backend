from django.contrib import admin
from .models import Notification, ScheduledMessage


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'notif_type', 'title', 'is_read', 'created_at')
    list_filter   = ('notif_type', 'is_read')
    search_fields = ('user__email', 'title')


@admin.register(ScheduledMessage)
class ScheduledMessageAdmin(admin.ModelAdmin):
    list_display  = ('subject', 'recipient', 'scheduled_for', 'status', 'attempts', 'sent_at')
    list_filter   = ('status',)
    search_fields = ('recipient', 'subject')
    readonly_fields = ('attempts', 'error', 'sent_at', 'created_at', 'updated_at')
    ordering = ('scheduled_for',)
