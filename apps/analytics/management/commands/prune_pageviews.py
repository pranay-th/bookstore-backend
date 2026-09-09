"""
prune_pageviews — delete old analytics.PageView rows.

The PageView table grows quickly (one row per content GET). This command trims
it so the admin list and the table stay manageable.

Usage:
    python manage.py prune_pageviews              # keep the last 30 days
    python manage.py prune_pageviews --days 7     # keep the last 7 days
    python manage.py prune_pageviews --all        # delete everything
    python manage.py prune_pageviews --days 30 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta

from apps.analytics.models import PageView


class Command(BaseCommand):
    help = "Delete old PageView rows (default: keep the last 30 days)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=30,
            help="Keep rows newer than this many days (default 30).",
        )
        parser.add_argument(
            "--all", action="store_true",
            help="Delete ALL page views, ignoring --days.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report how many rows would be deleted without deleting.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        delete_all = options["all"]
        dry_run = options["dry_run"]

        if not delete_all and days < 1:
            raise CommandError("--days must be at least 1 (or use --all).")

        qs = PageView.objects.all()
        if not delete_all:
            cutoff = timezone.now() - timedelta(days=days)
            qs = qs.filter(created_at__lt=cutoff)

        count = qs.count()

        if dry_run:
            scope = "all page views" if delete_all else f"page views older than {days} days"
            self.stdout.write(f"[dry-run] Would delete {count} {scope}.")
            return

        deleted, _ = qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted} page view(s)."))
