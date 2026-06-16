from django.contrib import admin
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
