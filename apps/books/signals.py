"""
books/signals.py

Invalidate the response cache whenever a Book is saved (price change, stock
change, etc.) so the API immediately serves fresh data to the frontend.
"""
import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Book

logger = logging.getLogger(__name__)


def _invalidate_books_cache(**kwargs):
    """Clear ALL cached responses when any Book is modified.

    The response cache keys include query params (pagination, search), so
    invalidating just '/api/books/' wouldn't clear '/api/books/?page=2' or
    individual book detail pages. For a small-scale app, flushing the entire
    response cache on save is the simplest correct approach. The cache refills
    naturally on the next request.
    """
    try:
        from django.core.cache import caches
        from django.conf import settings

        alias = getattr(settings, 'RESPONSE_CACHE_ALIAS', 'response_cache')
        caches[alias].clear()
        logger.debug("Response cache cleared (book save/delete signal)")
    except Exception as exc:
        # Cache invalidation is best-effort — don't break the save.
        logger.warning("Could not clear response cache: %s", exc)


@receiver(post_save, sender=Book)
def book_post_save(sender, instance, **kwargs):
    _invalidate_books_cache()


@receiver(post_delete, sender=Book)
def book_post_delete(sender, instance, **kwargs):
    _invalidate_books_cache()
