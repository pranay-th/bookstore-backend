"""categories/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Category
from .serializers import CategorySerializer

class CategoryViewSet(viewsets.ModelViewSet):
    # TODO: Add tree-view action for nested categories
    queryset         = Category.objects.all()
    serializer_class = CategorySerializer
