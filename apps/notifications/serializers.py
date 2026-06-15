from django.utils import timezone
from rest_framework import serializers
from .models import Notification, ScheduledMessage


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class ScheduledMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledMessage
        fields = [
            'id',
            'recipient',
            'subject',
            'body',
            'scheduled_for',
            'status',
            'attempts',
            'error',
            'sent_at',
            'user',
            'created_by',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'status',
            'attempts',
            'error',
            'sent_at',
            'created_by',
            'created_at',
            'updated_at',
        ]

    def validate_scheduled_for(self, value):
        # Only enforce future-dated scheduling when creating a new message
        if self.instance is None and value <= timezone.now():
            raise serializers.ValidationError(
                'scheduled_for must be a time in the future.'
            )
        return value
