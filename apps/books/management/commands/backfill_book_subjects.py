"""
Backfill the `subjects` field on existing books from Open Library.

Re-runs the same subject search queries used by `populate_books`, then
updates existing books (matched by ISBN) with the subjects from the
matching Open Library document. Books are updated in place so their IDs
are preserved (cart/wishlist references stay valid).

Usage:
    python manage.py backfill_book_subjects
    python manage.py backfill_book_subjects --pages 3
"""
import time

import httpx
from django.core.management.base import BaseCommand

from apps.books.models import Book
from apps.books.management.commands.populate_books import SEARCH_QUERIES, OL_SEARCH_URL


class Command(BaseCommand):
    help = "Backfill book subjects from Open Library (matched by ISBN)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pages", type=int, default=2,
            help="How many 200-result pages to scan per query (default: 2)",
        )
        parser.add_argument(
            "--overwrite", action="store_true",
            help="Overwrite subjects even if a book already has some.",
        )

    def handle(self, *args, **options):
        pages = options["pages"]
        overwrite = options["overwrite"]
        per_query_limit = 200

        # Map ISBN -> book for quick lookup. Only books with an ISBN can be matched.
        isbn_to_book = {}
        qs = Book.objects.exclude(isbn__isnull=True).exclude(isbn="")
        if not overwrite:
            qs = qs.filter(subjects="")
        for book in qs.only("id", "isbn", "subjects"):
            isbn_to_book[book.isbn] = book

        self.stdout.write(f"Books eligible for backfill: {len(isbn_to_book)}")
        if not isbn_to_book:
            self.stdout.write(self.style.SUCCESS("Nothing to backfill."))
            return

        updated = 0
        to_update = []

        for page in range(pages):
            for query in SEARCH_QUERIES:
                offset = page * per_query_limit
                self.stdout.write(f"  q='{query}' offset={offset}...")
                try:
                    resp = httpx.get(
                        OL_SEARCH_URL,
                        params={
                            "q": query,
                            "limit": per_query_limit,
                            "offset": offset,
                            "fields": "isbn,subject",
                        },
                        timeout=30,
                    )
                    resp.raise_for_status()
                    docs = resp.json().get("docs", [])
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    self.stdout.write(self.style.ERROR(f"  API error: {exc}"))
                    time.sleep(2)
                    continue

                for doc in docs:
                    subjects_list = doc.get("subject") or []
                    if not subjects_list:
                        continue
                    subjects = ", ".join(subjects_list[:10])[:2000]
                    for candidate in (doc.get("isbn") or []):
                        book = isbn_to_book.get(candidate)
                        if book and (overwrite or not book.subjects):
                            book.subjects = subjects
                            to_update.append(book)
                            del isbn_to_book[candidate]
                            break

                if len(to_update) >= 500:
                    Book.objects.bulk_update(to_update, ["subjects"])
                    updated += len(to_update)
                    to_update = []
                    self.stdout.write(self.style.SUCCESS(f"  ✓ {updated} updated"))

                time.sleep(1)

        if to_update:
            Book.objects.bulk_update(to_update, ["subjects"])
            updated += len(to_update)

        self.stdout.write(
            self.style.SUCCESS(f"\nDone! Backfilled subjects for {updated} books.")
        )
