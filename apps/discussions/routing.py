"""
discussions/routing.py — WebSocket URL patterns for real-time discussions.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/discussions/(?P<thread_id>[0-9a-f-]+)/$', consumers.DiscussionConsumer.as_asgi()),
]
