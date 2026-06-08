"""
authors/models.py — Phase 0 placeholder.
TODO: Implement Author model with biography, photo, and book relationships.
"""
import uuid
from django.db import models


class Author(models.Model):
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=150)
    last_name  = models.CharField(max_length=150)
    bio        = models.TextField(blank=True)
    # TODO: Add photo field
    # TODO: Add website / social links

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'authors'

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
