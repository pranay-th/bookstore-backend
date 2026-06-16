"""
apps/core/events.py

Lightweight Redis event publisher used to feed the FastAPI analytics
microservice. The analytics service subscribes to these channels and persists
each event for aggregation:

    order_created
    book_viewed
    search_query
    recommendation_clicked

Design notes
------------
- **Fail-open:** publishing must never break a user request. Any Redis error is
  logged and swallowed.
- Reuses ``settings.REDIS_URL`` (the same instance used for OTP / throttling).
- Short socket timeouts so a slow/unavailable Redis can't stall the request.
"""
import json
import logging

import redis as redis_lib
from django.conf import settings

logger = logging.getLogger(__name__)

# Channel name constants (kept in sync with the analytics consumer).
ORDER_CREATED = "order_created"
BOOK_VIEWED = "book_viewed"
SEARCH_QUERY = "search_query"
RECOMMENDATION_CLICKED = "recommendation_clicked"

_client = None


def _get_client():
    """Return a lazily-initialised Redis client with short timeouts."""
    global _client
    if _client is None:
        _client = redis_lib.from_url(
            getattr(settings, "REDIS_URL", "redis://localhost:6379"),
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
    return _client


def publish_event(channel: str, payload: dict) -> bool:
    """
    Publish an analytics event to Redis.

    Returns True if the event was published, False otherwise. Never raises —
    callers can fire-and-forget without wrapping in try/except.
    """
    try:
        client = _get_client()
        client.publish(channel, json.dumps(payload, default=str))
        return True
    except Exception as exc:  # pragma: no cover - resilience path
        # Reset the cached client so the next call can re-establish it.
        global _client
        _client = None
        logger.warning("analytics: failed to publish '%s' event: %s", channel, exc)
        return False
