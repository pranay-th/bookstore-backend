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

    def get_paginated_response_schema(self, schema):
        """
        Override to prevent drf-spectacular from wrapping in
        count/next/previous/results. We handle the envelope ourselves.
        """
        return schema
