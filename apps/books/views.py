"""books/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Book
from .serializers import BookSerializer


class BookViewSet(viewsets.ModelViewSet):
    # TODO: Add filter_backends for category, author, price range, language
    # TODO: Add search on title, isbn, author name
    queryset         = Book.objects.filter(is_active=True).prefetch_related('authors', 'categories')
    serializer_class = BookSerializer
