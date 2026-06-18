"""
analytics/admin_urls.py

Django-admin analytics dashboard (staff-only HTML view + JSON proxy).
Mounted at /admin/analytics/ in config/urls.py.

The REST API for the frontend lives in urls.py (mounted at /api/analytics/).
"""
from django.urls import path

from . import views

urlpatterns = [
    path('dashboard/', views.analytics_dashboard, name='analytics-dashboard'),
    path('api/', views.analytics_api_proxy, name='analytics-api-proxy'),
]
