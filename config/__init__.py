"""
config package.

Import the Celery app eagerly so the @shared_task decorator and the
`app.config_from_object` wiring are available as soon as Django starts. This is
the standard Celery + Django integration pattern.
"""
from .celery import app as celery_app

__all__ = ("celery_app",)
