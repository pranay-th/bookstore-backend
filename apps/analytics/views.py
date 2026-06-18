"""
analytics/views.py

Custom Django admin view that displays live data from the FastAPI Analytics
Microservice. Renders a dashboard inside the admin panel with sales, inventory
and customer summaries fetched from the microservice's API.
"""
import logging
from functools import lru_cache

import httpx
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render

logger = logging.getLogger(__name__)


def _service_url():
    return getattr(settings, 'ANALYTICS_SERVICE_URL', 'http://localhost:8001')


def _fetch(path: str, timeout: float = 10.0) -> dict | list | None:
    """Fetch JSON from the analytics microservice. Returns None on failure."""
    url = f"{_service_url()}{path}"
    try:
        resp = httpx.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Analytics fetch failed (%s): %s", url, exc)
        return None


@staff_member_required
def analytics_dashboard(request):
    """Render the analytics dashboard inside the admin."""
    sales = _fetch('/analytics/sales/summary')
    inventory = _fetch('/analytics/inventory/health')
    customers = _fetch('/analytics/customers/ltv')

    context = {
        'title': 'Analytics Dashboard',
        'sales': sales,
        'inventory': inventory,
        'customers': customers,
        'service_url': _service_url(),
        'has_data': any([sales, inventory, customers]),
    }
    return render(request, 'admin/analytics_dashboard.html', context)


@staff_member_required
def analytics_api_proxy(request):
    """
    Proxy endpoint: GET /admin/analytics/api/<path>/
    Forwards requests to the microservice so admin JS widgets can fetch data
    without CORS issues.
    """
    path = request.GET.get('path', '/analytics/sales/summary')
    data = _fetch(path)
    if data is None:
        return JsonResponse({'error': 'Analytics service unreachable'}, status=503)
    return JsonResponse(data, safe=False)
