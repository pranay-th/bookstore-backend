from django.contrib import admin
from .models import Book

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display  = ('title', 'isbn', 'price', 'is_active', 'created_at')
    list_filter   = ('is_active', 'language', 'categories')
    search_fields = ('title', 'isbn')
    filter_horizontal = ('authors', 'categories')
