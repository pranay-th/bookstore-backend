"""discussions/views.py — Forum thread and post management"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from apps.core.responses import success_response, error_response
from apps.core.throttles import SearchThrottle, AuthenticatedUserThrottle, AnonUserThrottle
from .models import Thread, Post
from .serializers import ThreadSerializer, ThreadListSerializer, PostSerializer


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class ThreadViewSet(viewsets.ModelViewSet):
    queryset = Thread.objects.all().select_related('author')
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes = [AuthenticatedUserThrottle, AnonUserThrottle, SearchThrottle]

    def get_serializer_class(self):
        if self.action == 'list':
            return ThreadListSerializer
        return ThreadSerializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            return success_response(data=paginated.data, message="Threads retrieved successfully.")
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Threads retrieved successfully.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data, message="Thread retrieved successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        thread = serializer.save(author=request.user)
        return success_response(
            data=ThreadSerializer(thread).data,
            message="Thread created successfully.",
            status_code=201,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user and not request.user.is_staff:
            return error_response(message="You can only edit your own threads.", status_code=403)
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Thread updated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user and not request.user.is_staff:
            return error_response(message="You can only delete your own threads.", status_code=403)
        instance.delete()
        return success_response(data={}, message="Thread deleted successfully.", status_code=204)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_post(self, request, pk=None):
        thread = self.get_object()
        if thread.is_locked and not request.user.is_staff:
            return error_response(message="This thread is locked.", status_code=403)
        serializer = PostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save(thread=thread, author=request.user)

        # Notify thread author when someone else replies
        try:
            from apps.notifications.models import Notification
            if thread.author != request.user:
                Notification.objects.create(
                    user=thread.author,
                    notif_type='general',
                    title='New reply on your thread',
                    message=f'{request.user.email} replied to your thread "{thread.title}".',
                )
        except Exception:
            pass

        return success_response(
            data=PostSerializer(post).data,
            message="Post added successfully.",
            status_code=201,
        )


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().select_related('author', 'thread')
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes = [AuthenticatedUserThrottle, AnonUserThrottle]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        thread_id = request.query_params.get('thread')
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            return success_response(data=paginated.data, message="Posts retrieved successfully.")
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
        return success_response(data=PostSerializer(post).data, message="Post created successfully.", status_code=201)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user and not request.user.is_staff:
            return error_response(message="You can only edit your own posts.", status_code=403)
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Post updated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.author != request.user and not request.user.is_staff:
            return error_response(message="You can only delete your own posts.", status_code=403)
        instance.delete()
        return success_response(data={}, message="Post deleted successfully.", status_code=204)
