"""
books/test_author_studio.py

Tests for the author studio endpoints (/api/author/...).

Covers:
  - Role gating (only AUTHOR / staff may access)
  - Owner-scoping (authors only see/manage their own books)
  - Publish / update / unpublish / remove lifecycle
  - Aggregate stats (sales from orders, ratings from reviews)
  - Recent reviews feed
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.books.models import Book
from apps.orders.models import Order, OrderItem
from apps.reviews.models import Review

User = get_user_model()


class AuthorStudioTestCase(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email="author@example.com",
            password="Passw0rd!",
            first_name="Ava",
            last_name="Writer",
            role="AUTHOR",
            is_email_verified=True,
        )
        self.other_author = User.objects.create_user(
            email="other@example.com",
            password="Passw0rd!",
            first_name="Otto",
            last_name="Other",
            role="AUTHOR",
            is_email_verified=True,
        )
        self.customer = User.objects.create_user(
            email="customer@example.com",
            password="Passw0rd!",
            first_name="Cara",
            last_name="Reader",
            role="CUSTOMER",
            is_email_verified=True,
        )

        # A book owned by the main author, and one owned by someone else.
        self.my_book = Book.objects.create(
            title="My Great Novel", price=Decimal("10.00"), stock=100, owner=self.author
        )
        self.their_book = Book.objects.create(
            title="Rival Novel", price=Decimal("12.00"), stock=100, owner=self.other_author
        )

    # ----------------------------------------------------------------- access
    def test_customer_is_forbidden(self):
        self.client.force_authenticate(self.customer)
        res = self.client.get("/api/author/books/")
        self.assertEqual(res.status_code, 403)

    def test_anonymous_is_unauthorized(self):
        res = self.client.get("/api/author/books/")
        self.assertIn(res.status_code, (401, 403))

    # ----------------------------------------------------------------- listing
    def test_author_only_sees_own_books(self):
        self.client.force_authenticate(self.author)
        res = self.client.get("/api/author/books/")
        self.assertEqual(res.status_code, 200)
        results = res.data["data"]["results"]
        titles = [b["title"] for b in results]
        self.assertIn("My Great Novel", titles)
        self.assertNotIn("Rival Novel", titles)

    # ----------------------------------------------------------------- create
    def test_publish_new_book_sets_owner(self):
        self.client.force_authenticate(self.author)
        res = self.client.post(
            "/api/author/books/",
            {"title": "Brand New Book", "price": "9.99", "stock": 5},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        book = Book.objects.get(title="Brand New Book")
        self.assertEqual(book.owner, self.author)
        self.assertTrue(book.is_active)
        # Author display name defaults to the owner's full name.
        self.assertEqual(book.author, "Ava Writer")

    # ----------------------------------------------------------------- update
    def test_cannot_update_someone_elses_book(self):
        self.client.force_authenticate(self.author)
        res = self.client.patch(
            f"/api/author/books/{self.their_book.id}/",
            {"price": "1.00"},
            format="json",
        )
        self.assertEqual(res.status_code, 404)
        self.their_book.refresh_from_db()
        self.assertEqual(self.their_book.price, Decimal("12.00"))

    def test_update_own_book(self):
        self.client.force_authenticate(self.author)
        res = self.client.patch(
            f"/api/author/books/{self.my_book.id}/",
            {"price": "19.99"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.my_book.refresh_from_db()
        self.assertEqual(self.my_book.price, Decimal("19.99"))

    # ------------------------------------------------------------- publish flow
    def test_unpublish_and_publish(self):
        self.client.force_authenticate(self.author)

        res = self.client.post(f"/api/author/books/{self.my_book.id}/unpublish/")
        self.assertEqual(res.status_code, 200)
        self.my_book.refresh_from_db()
        self.assertFalse(self.my_book.is_active)

        res = self.client.post(f"/api/author/books/{self.my_book.id}/publish/")
        self.assertEqual(res.status_code, 200)
        self.my_book.refresh_from_db()
        self.assertTrue(self.my_book.is_active)

    # ----------------------------------------------------------------- destroy
    def test_remove_soft_deletes(self):
        self.client.force_authenticate(self.author)
        res = self.client.delete(f"/api/author/books/{self.my_book.id}/")
        self.assertEqual(res.status_code, 200)
        self.my_book.refresh_from_db()
        self.assertFalse(self.my_book.is_active)

    # ------------------------------------------------------------------- stats
    def test_stats_reflect_sales_and_reviews(self):
        # One delivered order: 3 copies of my_book at 10.00
        order = Order.objects.create(user=self.customer, status="delivered")
        OrderItem.objects.create(
            order=order, book=self.my_book, quantity=3, unit_price=Decimal("10.00")
        )
        # A cancelled order should NOT count toward sales.
        cancelled = Order.objects.create(user=self.customer, status="cancelled")
        OrderItem.objects.create(
            order=cancelled, book=self.my_book, quantity=5, unit_price=Decimal("10.00")
        )
        # An approved review.
        Review.objects.create(
            book=self.my_book, user=self.customer, rating=4, body="Solid read.",
            is_approved=True,
        )

        self.client.force_authenticate(self.author)
        res = self.client.get("/api/author/stats/")
        self.assertEqual(res.status_code, 200)
        data = res.data["data"]
        self.assertEqual(data["units_sold"], 3)
        self.assertEqual(data["gross_revenue"], 30.0)
        self.assertEqual(data["royalties"], 21.0)  # 70% of 30
        self.assertEqual(data["avg_rating"], 4.0)
        self.assertEqual(data["review_count"], 1)
        self.assertEqual(data["total_titles"], 1)

    # ----------------------------------------------------------------- reviews
    def test_recent_reviews_only_for_own_books(self):
        Review.objects.create(
            book=self.my_book, user=self.customer, rating=5, body="Loved it.",
            is_approved=True,
        )
        Review.objects.create(
            book=self.their_book, user=self.customer, rating=2, body="Not for me.",
            is_approved=True,
        )
        self.client.force_authenticate(self.author)
        res = self.client.get("/api/author/reviews/")
        self.assertEqual(res.status_code, 200)
        results = res.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["book_title"], "My Great Novel")
        self.assertEqual(results[0]["rating"], 5)


class AuthorAnalyticsTestCase(APITestCase):
    """Tests for the author analytics endpoints, which proxy to the
    FastAPI analytics microservice. The microservice itself is mocked so these
    tests never make a real network call."""

    def setUp(self):
        self.author = User.objects.create_user(
            email="ana@example.com",
            password="Passw0rd!",
            first_name="Ana",
            last_name="Lytics",
            role="AUTHOR",
            is_email_verified=True,
        )
        self.other_author = User.objects.create_user(
            email="rival@example.com",
            password="Passw0rd!",
            role="AUTHOR",
            is_email_verified=True,
        )
        self.customer = User.objects.create_user(
            email="reader@example.com",
            password="Passw0rd!",
            role="CUSTOMER",
            is_email_verified=True,
        )
        self.my_book = Book.objects.create(
            title="Owned Book", price=Decimal("10.00"), stock=50, owner=self.author
        )
        self.their_book = Book.objects.create(
            title="Rival Book", price=Decimal("10.00"), stock=50, owner=self.other_author
        )

    # ----------------------------------------------------------------- access
    def test_customer_forbidden_from_analytics(self):
        self.client.force_authenticate(self.customer)
        res = self.client.get("/api/author/analytics/")
        self.assertEqual(res.status_code, 403)

    # ------------------------------------------------------- catalogue analytics
    def test_analytics_proxies_owned_book_ids(self):
        from unittest.mock import patch

        captured = {}

        def fake_get(path, params=None):
            captured.setdefault("calls", []).append((path, params))
            if path.endswith("/summary"):
                return {"total_revenue": 100.0, "total_orders": 5}
            return [{"period": "2026-06-01", "revenue": 20.0, "orders": 1, "items_sold": 2}]

        self.client.force_authenticate(self.author)
        with patch("apps.books.author_views.analytics_client.get", side_effect=fake_get):
            res = self.client.get("/api/author/analytics/")

        self.assertEqual(res.status_code, 200)
        data = res.data["data"]
        self.assertEqual(data["summary"]["total_revenue"], 100.0)
        self.assertEqual(len(data["daily"]), 1)
        # The owned book id must be forwarded, and the rival's must not.
        summary_call = next(c for c in captured["calls"] if c[0].endswith("/summary"))
        forwarded_ids = summary_call[1]["book_ids"]
        self.assertIn(str(self.my_book.id), forwarded_ids)
        self.assertNotIn(str(self.their_book.id), forwarded_ids)

    def test_analytics_zero_state_without_books(self):
        # Author with no books gets a clean empty payload, no service call.
        empty_author = User.objects.create_user(
            email="empty@example.com", password="Passw0rd!", role="AUTHOR",
            is_email_verified=True,
        )
        self.client.force_authenticate(empty_author)
        res = self.client.get("/api/author/analytics/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["summary"]["total_revenue"], 0)
        self.assertEqual(res.data["data"]["daily"], [])

    def test_analytics_service_unavailable(self):
        from unittest.mock import patch

        from apps.core.analytics_client import AnalyticsServiceError

        self.client.force_authenticate(self.author)
        with patch(
            "apps.books.author_views.analytics_client.get",
            side_effect=AnalyticsServiceError("down", status_code=503),
        ):
            res = self.client.get("/api/author/analytics/")
        self.assertEqual(res.status_code, 503)
        self.assertFalse(res.data["status"]["success"])

    # ----------------------------------------------------------- book analytics
    def test_book_analytics_ownership_enforced(self):
        self.client.force_authenticate(self.author)
        # Asking for a book the author does not own -> 404, no service call.
        res = self.client.get(f"/api/author/analytics/book/{self.their_book.id}/")
        self.assertEqual(res.status_code, 404)

    def test_book_analytics_proxies_for_owned_book(self):
        from unittest.mock import patch

        self.client.force_authenticate(self.author)
        payload = {"book_id": str(self.my_book.id), "units_sold": 7, "revenue": 70.0}
        with patch(
            "apps.books.author_views.analytics_client.get", return_value=payload
        ) as mock_get:
            res = self.client.get(f"/api/author/analytics/book/{self.my_book.id}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["units_sold"], 7)
        called_path = mock_get.call_args[0][0]
        self.assertEqual(called_path, f"/analytics/sales/book/{self.my_book.id}")
