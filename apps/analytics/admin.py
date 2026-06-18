from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import PageView


@admin.register(PageView)
class PageViewAdmin(admin.ModelAdmin):
    list_display = ('path', 'user', 'created_at')
    search_fields = ('path',)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = format_html(
            'Page Views &nbsp;|&nbsp; <a href="{}" style="color: #417690;">'
            '📊 Open Analytics Dashboard</a>',
            reverse('analytics-dashboard'),
        )
        return super().changelist_view(request, extra_context=extra_context)
