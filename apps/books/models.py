"""
books/models.py

All book data is stored locally in PostgreSQL.
Imported once from Open Library, served directly from the database.
"""
import uuid
from django.db import models


class Book(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    isbn = models.CharField(max_length=20, blank=True, null=True, unique=True)
    description = models.TextField(blank=True)
    cover_url = models.URLField(blank=True)
    published_year = models.IntegerField(blank=True, null=True)
    language = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "books"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
