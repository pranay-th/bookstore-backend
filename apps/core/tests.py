from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class HealthCheckTestCase(TestCase):
    """Tests for the health check endpoint."""

    def setUp(self):
        self.client = APIClient()

    def test_health_returns_200(self):
        """GET /health/ should return HTTP 200."""
        response = self.client.get(reverse('health-check'))
        self.assertEqual(response.status_code, 200)

    def test_health_returns_ok_status(self):
        """GET /health/ should return {'status': 'ok'}."""
        response = self.client.get(reverse('health-check'))
        self.assertEqual(response.json(), {'status': 'ok'})
