from django.contrib import admin
from .models import Order, OrderItem, OrderDelivery


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('subtotal',)


class OrderDeliveryInline(admin.StackedInline):
    model = OrderDelivery
    extra = 0
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('id', 'user', 'status', 'total_amount', 'created_at')
    list_filter   = ('status',)
    search_fields = ('user__email',)
    inlines       = [OrderDeliveryInline, OrderItemInline]


@admin.register(OrderDelivery)
class OrderDeliveryAdmin(admin.ModelAdmin):
    list_display  = ('order', 'full_name', 'email', 'city', 'postal_code', 'created_at')
    search_fields = ('full_name', 'email', 'order__id')
