from django.urls import path
from .views import list_authors, author_books

urlpatterns = [
    path("authors/", list_authors, name="author-list"),
    path("authors/<str:author_name>/books/", author_books, name="author-books"),
]
