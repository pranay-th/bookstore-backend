"""discussions/views.py — Forum thread and post management"""
import logging

from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from apps.core.responses import success_response, error_response
from apps.core.throttles import SearchThrottle, AuthenticatedUserThrottle, AnonUserThrottle
from .models import Thread, Post
from .serializers import ThreadSerializer, ThreadListSerializer, PostSerializer

logger = logging.getLogger(__name__)


def _broadcast_post_deleted(thread_id, post_id):
    """Notify everyone viewing the thread (over WS) that a post was removed.

    Mirrors the consumer's own delete broadcast so REST deletes propagate live
    too. Best-effort: never let a channel-layer hiccup break the HTTP response.
    """
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f'discussion_{thread_id}',
            {'type': 'discussion.post_deleted', 'post_id': str(post_id)},
        )
    except Exception as exc:  # pragma: no cover - resilience path
        logger.warning("Failed to broadcast post_deleted: %s", exc)


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


def _notify(user, title, message, notif_type='general', link=''):
    """Create an in-app notification — silently swallows any error."""
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            user=user,
            notif_type=notif_type,
            title=title,
            message=message,
            link=link,
        )
    except Exception:
        pass


class ThreadViewSet(viewsets.ModelViewSet):
    queryset           = Thread.objects.all().select_related('author')
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes   = [AuthenticatedUserThrottle, AnonUserThrottle, SearchThrottle]

    def get_serializer_class(self):
        return ThreadListSerializer if self.action == 'list' else ThreadSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page     = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return success_response(
                data    = self.get_paginated_response(serializer.data).data,
                message = "Threads retrieved successfully.",
            )
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Threads retrieved successfully.")

    def retrieve(self, request, *args, **kwargs):
        instance   = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data, message="Thread retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        thread = serializer.save(author=request.user)
        return success_response(
            data       = ThreadSerializer(thread).data,
            message    = "Thread created successfully.",
            status_code= 201,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user and not request.user.is_staff:
            return error_response(message="You can only edit your own threads.", status_code=403)
        partial    = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Thread updated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user and not request.user.is_staff:
            return error_response(message="You can only delete your own threads.", status_code=403)
        instance.delete()
        return success_response(data={}, message="Thread deleted successfully.", status_code=200)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_post(self, request, pk=None):
        """Reply to a thread and notify the thread author."""
        thread = self.get_object()
        if thread.is_locked and not request.user.is_staff:
            return error_response(message="This thread is locked.", status_code=403)

        serializer = PostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(thread=thread, author=request.user)

        # Notify thread author if someone else replies
        if thread.author != request.user:
            _notify(
                user       = thread.author,
                title      = "New reply on your thread",
                message    = f'{request.user.email} replied to your thread "{thread.title}".',
                notif_type = 'general',
                link       = f'/discussions?thread={thread.id}',
            )

        return success_response(
            data       = PostSerializer(post).data,
            message    = "Post added successfully.",
            status_code= 201,
        )


class PostViewSet(viewsets.ModelViewSet):
    queryset           = Post.objects.all().select_related('author', 'thread')
    serializer_class   = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes   = [AuthenticatedUserThrottle, AnonUserThrottle]

    def list(self, request, *args, **kwargs):
        queryset  = self.filter_queryset(self.get_queryset())
        thread_id = request.query_params.get('thread')
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return success_response(
                data    = self.get_paginated_response(serializer.data).data,
                message = "Posts retrieved successfully.",
            )
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Posts retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            thread = Thread.objects.get(id=request.data.get('thread'))
            if thread.is_locked and not request.user.is_staff:
                return error_response(message="This thread is locked.", status_code=403)
        except Thread.DoesNotExist:
            return error_response(message="Thread not found.", status_code=404)
        post = serializer.save(author=request.user, thread=thread)

        # Notify thread author
        if thread.author != request.user:
            _notify(
                user       = thread.author,
                title      = "New reply on your thread",
                message    = f'{request.user.email} replied to your thread "{thread.title}".',
                notif_type = 'general',
                link       = f'/discussions?thread={thread.id}',
            )

        return success_response(data=PostSerializer(post).data, message="Post created successfully.", status_code=201)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user and not request.user.is_staff:
            return error_response(message="You can only edit your own posts.", status_code=403)
        partial    = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Post updated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # The reply author, the thread author, or staff can delete a reply
        is_reply_author  = instance.author == request.user
        is_thread_author = instance.thread.author == request.user
        if not (is_reply_author or is_thread_author or request.user.is_staff):
            return error_response(
                message="You can only delete your own replies or replies on your thread.",
                status_code=403,
            )
        thread_id = instance.thread_id
        post_id = instance.id
        instance.delete()
        # Propagate the deletion to everyone viewing the thread in real time.
        _broadcast_post_deleted(thread_id, post_id)
        return success_response(data={}, message="Post deleted successfully.", status_code=200)
