from django.urls import path
from .views import list_authors, author_books, author_image

urlpatterns = [
    path("authors/", list_authors, name="author-list"),
    path("authors/image/", author_image, name="author-image"),
    path("authors/<path:author_name>/books/", author_books, name="author-books"),
]
