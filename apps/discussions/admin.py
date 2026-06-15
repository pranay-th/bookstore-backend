from django.contrib import admin
from .models import Thread, Post


@admin.register(Thread)
class ThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'is_pinned', 'is_locked', 'created_at')
    list_filter = ('category', 'is_pinned', 'is_locked', 'created_at')
    search_fields = ('title', 'author__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'created_at', 'is_edited')
    list_filter = ('created_at', 'is_edited')
    search_fields = ('thread__title', 'author__email', 'content')
    readonly_fields = ('created_at', 'updated_at')
