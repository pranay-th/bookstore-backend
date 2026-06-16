"""
Management command to populate the database with 10,000 books.

Fetches real book data from Open Library Search API in batches,
stores everything locally in PostgreSQL.

Usage:
    python manage.py populate_books
    python manage.py populate_books --count 5000
    python manage.py populate_books --clear
"""
import random
import time
from decimal import Decimal

import httpx
from django.core.management.base import BaseCommand

from apps.books.models import Book

# Diverse search queries to get variety
SEARCH_QUERIES = [
    "fiction", "science", "history", "fantasy", "mystery",
    "romance", "adventure", "philosophy", "biography", "poetry",
    "python programming", "javascript", "machine learning",
    "economics", "psychology", "art", "cooking", "travel",
    "horror", "thriller", "detective", "war", "love",
    "children", "young adult", "classic", "modern", "space",
    "ocean", "mountain", "music", "film", "architecture",
    "mathematics", "physics", "chemistry", "biology", "medicine",
    "law", "politics", "religion", "mythology", "sports",
]

OL_SEARCH_URL = "https://openlibrary.org/search.json"


def build_cover_url(cover_id):
    if cover_id:
        return f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
    return ""


class Command(BaseCommand):
    help = "Populate database with books from Open Library"

    def add_arguments(self, parser):
        parser.add_argument(
            "--count", type=int, default=10000,
            help="Number of books to create (default: 10000)",
        )
        parser.add_argument(
            "--clear", action="store_true",
            help="Delete all existing books before populating",
        )

    def handle(self, *args, **options):
        count = options["count"]

        if options["clear"]:
            deleted, _ = Book.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing books."))

        existing_count = Book.objects.count()
        self.stdout.write(f"Current books in database: {existing_count}")
        self.stdout.write(f"Target: {count} new books from Open Library...\n")

        books_to_create = []
        seen_isbns = set(
            Book.objects.values_list("isbn", flat=True).exclude(isbn__isnull=True)
        )
        created_total = 0
        batch_size = 500
        per_query_limit = 200  # Max per Open Library search call

        query_index = 0

        while created_total + len(books_to_create) < count:
            query = SEARCH_QUERIES[query_index % len(SEARCH_QUERIES)]
            offset = (query_index // len(SEARCH_QUERIES)) * per_query_limit
            query_index += 1

            self.stdout.write(f"  Fetching: q='{query}' offset={offset}...")

            try:
                resp = httpx.get(
                    OL_SEARCH_URL,
                    params={
                        "q": query,
                        "limit": per_query_limit,
                        "offset": offset,
                        "fields": "title,author_name,isbn,cover_i,first_publish_year,language,subject",
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                self.stdout.write(self.style.ERROR(f"  API error: {exc}"))
                time.sleep(2)
                continue

            docs = data.get("docs", [])
            if not docs:
                self.stdout.write(f"  No results for '{query}', skipping.")
                continue

            for doc in docs:
                if created_total + len(books_to_create) >= count:
                    break

                # Get ISBN (skip if duplicate)
                isbns = doc.get("isbn") or []
                isbn = None
                for candidate in isbns[:3]:
                    if candidate not in seen_isbns:
                        isbn = candidate
                        break
                if isbn and isbn in seen_isbns:
                    isbn = None

                if isbn:
                    seen_isbns.add(isbn)

                title = doc.get("title", "").strip()
                if not title:
                    continue

                authors = doc.get("author_name") or []
                author = ", ".join(authors[:3]) if authors else ""

                languages = doc.get("language") or []
                language = languages[0] if languages else ""

                subjects_list = doc.get("subject") or []
                subjects = ", ".join(subjects_list[:10])

                book = Book(
                    title=title[:255],
                    author=author[:255],
                    isbn=isbn[:20] if isbn else None,
                    description="",  # Search API doesn't return descriptions
                    subjects=subjects[:2000],
                    cover_url=build_cover_url(doc.get("cover_i")),
                    published_year=doc.get("first_publish_year"),
                    language=language[:50],
                    price=Decimal(str(round(random.uniform(99, 1999), 2))),
                    stock=random.randint(0, 500),
                    is_active=True,
                )
                books_to_create.append(book)

                # Batch insert
                if len(books_to_create) >= batch_size:
                    Book.objects.bulk_create(books_to_create, ignore_conflicts=True)
                    created_total += len(books_to_create)
                    books_to_create = []
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ {created_total}/{count} inserted")
                    )

            # Be respectful to Open Library API
            time.sleep(1)

        # Insert remaining
        if books_to_create:
            Book.objects.bulk_create(books_to_create, ignore_conflicts=True)
            created_total += len(books_to_create)

        final_count = Book.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! Inserted {created_total} books.\n"
                f"Total books in database: {final_count}"
            )
        )
