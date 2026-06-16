from django.contrib import admin
from .models import Author


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    """Admin for the Author placeholder model.

    NOTE: The frontend Authors page derives authors from the Book.author
    string field (not this table). To add an author that shows on the site,
    create a Book with that author's name in the 'author' field via the
    Books admin. This table can be used for storing extended metadata
    (bio, photo) if the Author model is fully implemented in the future.
    """
    list_display = ('first_name', 'last_name', 'bio', 'created_at')
    search_fields = ('first_name', 'last_name')
    fieldsets = (
        (None, {
            'fields': ('first_name', 'last_name', 'bio'),
            'description': (
                '<strong>Note:</strong> Authors shown on the site are derived '
                'from the Book → author field. To add a new visible author, '
                'go to Books and create/edit a book with the desired author name.'
            ),
        }),
    )
