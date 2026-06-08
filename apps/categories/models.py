"""
categories/models.py — Phase 0 placeholder.
TODO: Add slug, parent (self-referential), icon, and display_order fields.
"""
import uuid
from django.db import models


class Category(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=200, unique=True)
    slug        = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    parent      = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='children'
    )
    # TODO: Add icon / image field
    # TODO: Add is_active flag
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = 'categories'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name
