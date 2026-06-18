from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'amount', 'currency', 'status',
                    'razorpay_order_id', 'razorpay_payment_id', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id', 'user__email')
    readonly_fields = ('id', 'razorpay_order_id', 'razorpay_payment_id',
                       'razorpay_signature', 'created_at', 'updated_at')
    ordering = ('-created_at',)
