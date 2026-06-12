"""
apps/core/pagination.py

Shared pagination classes.
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Page-number pagination that allows the client to override the page size
    via `?page_size=`, capped at a sane maximum.
    """
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
