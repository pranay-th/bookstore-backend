"""
reviews/models.py — Phase 0 placeholder.
TODO: Enforce one review per user per book; add helpfulness voting.
"""
import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book        = models.ForeignKey('books.Book', on_delete=models.CASCADE, related_name='reviews')
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating      = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title       = models.CharField(max_length=200, blank=True)
    body        = models.TextField()
    is_approved = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table        = 'reviews'
        unique_together = ('book', 'user')
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.rating}★ on {self.book.title} by {self.user.email}'
