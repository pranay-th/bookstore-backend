"""
config/celery.py

Celery application for the Bookstore backend.

Used to offload slow / scheduled work off the request path — initially the
delivery-automation bots and the scheduled-message dispatch. The broker and
result backend reuse the existing Render Redis instance (REDIS_URL), so no new
infrastructure is required.

Runs alongside gunicorn inside the single Render web container (supervised by
supervisord), so the configuration below is tuned to be memory-frugal for the
free tier:
  * JSON-only serialisation (no pickle).
  * Results disabled by default (no result backend RAM/Redis churn) — opt in
    per-task with ignore_result=False if a return value is ever needed.
  * Workers acknowledge late + recycle after a bounded number of tasks to cap
    memory creep.

The beat schedule is defined here; the actual periodic tasks live in each
app's tasks.py and are autodiscovered.
"""
import os

from celery import Celery

# Ensure Django settings are importable when Celery boots standalone
# (the worker / beat processes don't go through manage.py).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("bookstore")

# Pull all CELERY_* keys from Django settings (namespace="CELERY").
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover tasks.py modules in every installed app.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Trivial task to verify the worker is wired up: `debug_task.delay()`."""
    print(f"[celery] debug_task request: {self.request!r}")
