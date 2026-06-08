"""analytics/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import PageView
from .serializers import PageViewSerializer

class PageViewViewSet(viewsets.ModelViewSet):
    # TODO: Restrict to admin only
    # TODO: Delegate report generation to FastAPI microservice
    queryset         = PageView.objects.all()
    serializer_class = PageViewSerializer
