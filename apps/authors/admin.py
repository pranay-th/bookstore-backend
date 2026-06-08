from django.contrib import admin
from .models import Author

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display  = ('first_name', 'last_name', 'created_at')
    search_fields = ('first_name', 'last_name')
