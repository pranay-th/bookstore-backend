from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'user', 'amount', 'status', 'method', 'created_at')
    list_filter  = ('status', 'method')
    search_fields = ('user__email', 'gateway_ref')
