from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    # TODO: Never expose full card details — only gateway_ref
    class Meta:
        model  = Payment
        fields = '__all__'
