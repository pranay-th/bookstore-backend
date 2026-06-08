"""reviews/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Review
from .serializers import ReviewSerializer

class ReviewViewSet(viewsets.ModelViewSet):
    # TODO: Allow read by anyone, write only by purchasers of the book
    # TODO: Add moderation flag action for admin
    queryset         = Review.objects.filter(is_approved=True).select_related('user', 'book')
    serializer_class = ReviewSerializer
