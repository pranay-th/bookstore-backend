"""
discussions/test_posts.py

Regression tests for commenting on threads.

Bug: PostSerializer required `thread` as a writable field, but the add_post
action (and the nested PostViewSet.create) supply the thread from the URL /
view rather than the request body. Validation failed with
"thread: This field is required" before the view could inject it.
"""
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.discussions.models import Thread, Post

User = get_user_model()


class AddPostTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="poster@example.com",
            password="Passw0rd!",
            first_name="Pat",
            last_name="Poster",
            is_email_verified=True,
        )
        self.thread = Thread.objects.create(
            title="A thread to comment on",
            author=self.user,
            category="general",
        )

    def test_add_post_without_thread_in_body_succeeds(self):
        """The thread comes from the URL — the body only needs content."""
        self.client.force_authenticate(self.user)
        res = self.client.post(
            f"/api/threads/{self.thread.id}/add_post/",
            {"content": "First reply!"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(Post.objects.filter(thread=self.thread).count(), 1)
        post = Post.objects.get(thread=self.thread)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.content, "First reply!")

    def test_locked_thread_rejects_post(self):
        self.thread.is_locked = True
        self.thread.save(update_fields=["is_locked"])
        self.client.force_authenticate(self.user)
        res = self.client.post(
            f"/api/threads/{self.thread.id}/add_post/",
            {"content": "Should be blocked"},
            format="json",
        )
        self.assertEqual(res.status_code, 403)

    def test_postviewset_create_associates_thread_from_body(self):
        """The flat /api/posts/ create path still links the post to its thread."""
        self.client.force_authenticate(self.user)
        res = self.client.post(
            "/api/posts/",
            {"thread": str(self.thread.id), "content": "Reply via posts endpoint"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.data)
        post = Post.objects.get(content="Reply via posts endpoint")
        self.assertEqual(post.thread, self.thread)
        self.assertEqual(post.author, self.user)
