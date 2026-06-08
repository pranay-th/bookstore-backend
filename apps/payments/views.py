"""payments/views.py — Phase 0 placeholder."""
from rest_framework import viewsets
from .models import Payment
from .serializers import PaymentSerializer

class PaymentViewSet(viewsets.ModelViewSet):
    # TODO: Restrict to admin and the owning user only
    # TODO: Add webhook endpoint for payment gateway callbacks
    # TODO: Add initiate_payment action
    queryset         = Payment.objects.all()
    serializer_class = PaymentSerializer
