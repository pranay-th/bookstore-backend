from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import reverse

from .models import PageView


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    """Page-view tracking is disabled, so instead of an empty changelist the
    "Page Views" admin entry shows a live analytics summary pulled from the
    FastAPI analytics service, plus a link to the full dashboard."""

    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        # Imported lazily to avoid import side effects at app-load time.
        from .views import _fetch

        sales = _fetch('/analytics/sales/summary') or {}
        inventory = _fetch('/analytics/inventory/health') or {}
        customers = _fetch('/analytics/customers/ltv') or {}

        context = {
            **self.admin_site.each_context(request),
            'title': 'Analytics Overview',
            'sales': sales,
            'inventory': inventory,
            'customers': customers,
            'dashboard_url': reverse('analytics-dashboard'),
            'has_data': bool(sales or inventory or customers),
            'opts': self.model._meta,
        }
        return TemplateResponse(request, 'admin/analytics_pageview.html', context)
