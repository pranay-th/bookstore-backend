from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ('book', 'user', 'rating', 'is_approved', 'created_at')
    list_filter   = ('is_approved', 'rating', 'created_at')
    search_fields = ('book__title', 'user__email', 'title')
    ordering      = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    autocomplete_fields = ('book', 'user')
    actions       = ['approve_reviews', 'unapprove_reviews']

    @admin.action(description='Approve selected reviews')
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} review(s) approved.')

    @admin.action(description='Unapprove selected reviews')
    def unapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} review(s) unapproved.')
