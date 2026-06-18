"""
analytics/tests.py

Tests for the store-wide (admin) analytics endpoints, which proxy to the
FastAPI analytics microservice. The microservice is mocked so no real network
call is made.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.core.analytics_client import AnalyticsServiceError

User = get_user_model()


class AdminAnalyticsTestCase(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="Passw0rd!",
            role="ADMIN",
            is_email_verified=True,
            is_staff=True,
        )
        self.customer = User.objects.create_user(
            email="user@example.com",
            password="Passw0rd!",
            role="CUSTOMER",
            is_email_verified=True,
        )

    def test_non_admin_forbidden(self):
        self.client.force_authenticate(self.customer)
        res = self.client.get("/api/analytics/sales/")
        self.assertEqual(res.status_code, 403)

    def test_sales_summary_proxies(self):
        self.client.force_authenticate(self.admin)
        payload = {"total_revenue": 999.0, "total_orders": 42}
        with patch(
            "apps.analytics.views.analytics_client.get", return_value=payload
        ) as mock_get:
            res = self.client.get("/api/analytics/sales/?start_date=2026-01-01")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["data"]["total_revenue"], 999.0)
        path, = mock_get.call_args[0]
        self.assertEqual(path, "/analytics/sales/summary")
        self.assertEqual(mock_get.call_args[1]["params"]["start_date"], "2026-01-01")

    def test_service_unavailable_returns_503(self):
        self.client.force_authenticate(self.admin)
        with patch(
            "apps.analytics.views.analytics_client.get",
            side_effect=AnalyticsServiceError("down", status_code=503),
        ):
            res = self.client.get("/api/analytics/inventory/")
        self.assertEqual(res.status_code, 503)
        self.assertFalse(res.data["status"]["success"])

    def test_generate_report_proxies_post(self):
        self.client.force_authenticate(self.admin)
        payload = {"id": "abc", "status": "ready", "download_url": "/reports/abc/download"}
        with patch(
            "apps.analytics.views.analytics_client.post", return_value=payload
        ) as mock_post:
            res = self.client.post(
                "/api/analytics/reports/",
                {"report_type": "sales", "file_format": "csv"},
                format="json",
            )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["data"]["status"], "ready")
        path, = mock_post.call_args[0]
        self.assertEqual(path, "/reports/generate")
        self.assertEqual(mock_post.call_args[1]["json"]["report_type"], "sales")
