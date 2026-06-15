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
