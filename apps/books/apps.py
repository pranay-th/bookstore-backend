from django.apps import AppConfig


class BooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.books'

    def ready(self):
        import apps.books.signals  # noqa: F401 — register post_save/post_delete handlers
