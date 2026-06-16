"""
discussions/models.py — Book discussion forum threads and posts
"""
import uuid
from django.db import models
from django.conf import settings


class Thread(models.Model):
    """A discussion thread in the forum"""
    
    CATEGORY_CHOICES = [
        ('general', 'General Discussion'),
        ('recommendations', 'Book Recommendations'),
        ('authors', 'Author Discussions'),
        ('events', 'Events & Book Clubs'),
        ('help', 'Help & Support'),
    ]
    
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title       = models.CharField(max_length=200)
    author      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='threads')
    category    = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    is_pinned   = models.BooleanField(default=False)
    is_locked   = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discussion_threads'
        ordering = ['-is_pinned', '-updated_at']

    def __str__(self):
        return self.title

    @property
    def post_count(self):
        return self.posts.count()

    @property
    def last_post_at(self):
        last_post = self.posts.order_by('-created_at').first()
        return last_post.created_at if last_post else self.created_at


class Post(models.Model):
    """A post/reply in a discussion thread"""
    
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread     = models.ForeignKey(Thread, on_delete=models.CASCADE, related_name='posts')
    author     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    content    = models.TextField()
    is_edited  = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discussion_posts'
        ordering = ['created_at']

    def __str__(self):
        return f'Post by {self.author.email} in {self.thread.title}'

    def save(self, *args, **kwargs):
        # Mark as edited if content changes after creation.
        # Note: id is a UUID with a default, so self.pk is set even before the
        # first insert — use _state.adding to detect a genuine update instead.
        if not self._state.adding:
            original = Post.objects.filter(pk=self.pk).first()
            if original and original.content != self.content:
                self.is_edited = True
        super().save(*args, **kwargs)
        # Update thread's updated_at timestamp
        self.thread.save()
