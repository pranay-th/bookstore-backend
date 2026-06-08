"""
books/models.py — Phase 0 placeholder.
TODO: Add formats (ebook, hardcover, paperback), language, publisher, edition.
"""
import uuid
from django.db import models


class Book(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title       = models.CharField(max_length=500)
    isbn        = models.CharField(max_length=13, unique=True)
    description = models.TextField(blank=True)
    price       = models.DecimalField(max_digits=10, decimal_places=2)
    cover_image = models.ImageField(upload_to='book_covers/', null=True, blank=True)
    published_at = models.DateField(null=True, blank=True)
    page_count  = models.PositiveIntegerField(null=True, blank=True)
    language    = models.CharField(max_length=10, default='en')
    is_active   = models.BooleanField(default=True)

    # Relationships — populated in later phases
    authors    = models.ManyToManyField('authors.Author',     related_name='books', blank=True)
    categories = models.ManyToManyField('categories.Category', related_name='books', blank=True)

    # TODO: Add publisher FK
    # TODO: Add discount / sale price logic
    # TODO: Add rating (computed from reviews)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'books'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
