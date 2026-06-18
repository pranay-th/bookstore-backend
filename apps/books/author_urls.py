"""
books/author_urls.py

Author studio routes, mounted under /api/author/.

  /api/author/books/          AuthorBookViewSet (list/create/retrieve/update/destroy
                              + publish/unpublish)
  /api/author/stats/          AuthorStudioViewSet.list — aggregate stats
  /api/author/reviews/        AuthorStudioViewSet.reviews — recent reviews
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .author_views import AuthorBookViewSet, AuthorStudioViewSet

router = DefaultRouter()
router.register("author/books", AuthorBookViewSet, basename="author-book")

urlpatterns = [
    path(
        "author/stats/",
        AuthorStudioViewSet.as_view({"get": "list"}),
        name="author-stats",
    ),
    path(
        "author/reviews/",
        AuthorStudioViewSet.as_view({"get": "reviews"}),
        name="author-reviews",
    ),
    path(
        "author/analytics/",
        AuthorStudioViewSet.as_view({"get": "analytics"}),
        name="author-analytics",
    ),
    path(
        "author/analytics/book/<str:book_id>/",
        AuthorStudioViewSet.as_view({"get": "book_analytics"}),
        name="author-book-analytics",
    ),
    path("", include(router.urls)),
]
