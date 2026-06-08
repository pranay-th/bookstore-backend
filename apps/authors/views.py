"""authors/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Author
from .serializers import AuthorSerializer

class AuthorViewSet(viewsets.ModelViewSet):
    # TODO: Add filtering, search, pagination
    queryset         = Author.objects.all()
    serializer_class = AuthorSerializer
