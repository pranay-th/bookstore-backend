"""
analytics/urls.py

Store-wide (admin) analytics REST API, proxied to the FastAPI analytics
microservice. Mounted under /api/ in config/urls.py, so paths below resolve as
/api/analytics/...

The Django-admin HTML dashboard lives in admin_urls.py (mounted at
/admin/analytics/).
"""
from django.urls import path

from . import views

urlpatterns = [
    path("analytics/sales/", views.sales_summary, name="analytics-sales-summary"),
    path("analytics/sales/daily/", views.sales_daily, name="analytics-sales-daily"),
    path(
        "analytics/sales/monthly/",
        views.sales_monthly,
        name="analytics-sales-monthly",
    ),
    path(
        "analytics/sales/top-books/",
        views.sales_top_books,
        name="analytics-sales-top-books",
    ),
    path(
        "analytics/sales/by-author/",
        views.sales_by_author,
        name="analytics-sales-by-author",
    ),
    path(
        "analytics/sales/by-category/",
        views.sales_by_category,
        name="analytics-sales-by-category",
    ),
    path(
        "analytics/inventory/",
        views.inventory_health,
        name="analytics-inventory-health",
    ),
    path(
        "analytics/customers/",
        views.customers_overview,
        name="analytics-customers-overview",
    ),
    path("analytics/reports/", views.generate_report, name="analytics-generate-report"),
]
