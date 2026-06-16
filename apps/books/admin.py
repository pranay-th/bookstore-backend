from django.contrib import admin
from .models import Book


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "isbn", "price", "stock", "is_active", "created_at")
    list_filter = ("is_active", "language", "author")
    search_fields = ("title", "author", "isbn")
    list_editable = ("price", "stock", "is_active")
    list_per_page = 50
