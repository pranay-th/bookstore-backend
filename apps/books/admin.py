from django.contrib import admin
from django.db.models import F
from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "isbn", "price", "stock", "is_active", "created_at")
    list_filter = ("is_active", "language")
    search_fields = ("title", "author", "isbn")
    list_editable = ("price", "stock", "is_active")
    list_per_page = 50
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        ("Book", {"fields": ("title", "author", "isbn", "description", "cover_url")}),
        ("Catalogue", {"fields": ("published_year", "language", "price", "stock", "is_active")}),
        ("Ownership & dates", {"fields": ("owner", "id", "created_at", "updated_at")}),
    )
    autocomplete_fields = ("owner",)
    actions = ["restock_10", "restock_50", "restock_100", "set_out_of_stock"]

    # ── Admin Actions for restocking ───────────────────────────
    @admin.action(description="Restock: +10 units to selected books")
    def restock_10(self, request, queryset):
        count = queryset.update(stock=F('stock') + 10)
        self.message_user(request, f"Added 10 units to {count} book(s).")

    @admin.action(description="Restock: +50 units to selected books")
    def restock_50(self, request, queryset):
        count = queryset.update(stock=F('stock') + 50)
        self.message_user(request, f"Added 50 units to {count} book(s).")

    @admin.action(description="Restock: +100 units to selected books")
    def restock_100(self, request, queryset):
        count = queryset.update(stock=F('stock') + 100)
        self.message_user(request, f"Added 100 units to {count} book(s).")

    @admin.action(description="Set stock to 0 (mark out of stock)")
    def set_out_of_stock(self, request, queryset):
        count = queryset.update(stock=0)
        self.message_user(request, f"Set {count} book(s) to out of stock.")
