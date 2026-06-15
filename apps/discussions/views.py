"""discussions/views.py — Forum thread and post management"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.responses import success_response, error_response
from apps.core.throttles import SearchThrottle, AuthenticatedUserThrottle, AnonUserThrottle
from .models import Thread, Post
from .serializers import ThreadSerializer, ThreadListSerializer, PostSerializer


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """Allow read access to anyone, write access only to authenticated users"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class ThreadViewSet(viewsets.ModelViewSet):
    """
    ViewSet for discussion threads.
    - List, retrieve: anyone (read-only for anonymous)
    - Create, update, delete: authenticated users only
    """
    queryset = Thread.objects.all().select_related('author')
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes = [AuthenticatedUserThrottle, AnonUserThrottle, SearchThrottle]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ThreadListSerializer
        return ThreadSerializer
    
    def list(self, request, *args, **kwargs):
        """List all threads with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response(success_response(
                details="Threads retrieved successfully.",
                data=paginated_response.data,
                status_code=status.HTTP_200_OK
            ))
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(success_response(
            details="Threads retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        ))
    
    def retrieve(self, request, *args, **kwargs):
        """Get thread details with all posts"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(success_response(
            details="Thread retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        ))
    
    def create(self, request, *args, **kwargs):
        """Create a new thread (authenticated users only)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        
        return Response(success_response(
            details="Thread created successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        ), status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update thread (author only)"""
        instance = self.get_object()
        
        # Only author can update their thread
        if instance.author != request.user and not request.user.is_staff:
            return Response(error_response(
                details="You can only edit your own threads.",
                status_code=status.HTTP_403_FORBIDDEN
            ), status=status.HTTP_403_FORBIDDEN)
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(success_response(
            details="Thread updated successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        ))
    
    def destroy(self, request, *args, **kwargs):
        """Delete thread (author or staff only)"""
        instance = self.get_object()
        
        if instance.author != request.user and not request.user.is_staff:
            return Response(error_response(
                details="You can only delete your own threads.",
                status_code=status.HTTP_403_FORBIDDEN
            ), status=status.HTTP_403_FORBIDDEN)
        
        instance.delete()
        return Response(success_response(
            details="Thread deleted successfully.",
            data={},
            status_code=status.HTTP_204_NO_CONTENT
        ), status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_post(self, request, pk=None):
        """Add a post/reply to a thread"""
        thread = self.get_object()
        
        if thread.is_locked and not request.user.is_staff:
            return Response(error_response(
                details="This thread is locked.",
                status_code=status.HTTP_403_FORBIDDEN
            ), status=status.HTTP_403_FORBIDDEN)
        
        serializer = PostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(thread=thread, author=request.user)
        
        return Response(success_response(
            details="Post added successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        ), status=status.HTTP_201_CREATED)


class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for discussion posts.
    - List, retrieve: anyone
    - Create, update, delete: authenticated users only
    """
    queryset = Post.objects.all().select_related('author', 'thread')
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes = [AuthenticatedUserThrottle, AnonUserThrottle]
    
    def list(self, request, *args, **kwargs):
        """List posts (optionally filtered by thread)"""
        queryset = self.filter_queryset(self.get_queryset())
        thread_id = request.query_params.get('thread')
        
        if thread_id:
            queryset = queryset.filter(thread_id=thread_id)
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response(success_response(
                details="Posts retrieved successfully.",
                data=paginated_response.data,
                status_code=status.HTTP_200_OK
            ))
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(success_response(
            details="Posts retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        ))
    
    def create(self, request, *args, **kwargs):
        """Create a new post"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        thread = Thread.objects.get(id=request.data.get('thread'))
        if thread.is_locked and not request.user.is_staff:
            return Response(error_response(
                details="This thread is locked.",
                status_code=status.HTTP_403_FORBIDDEN
            ), status=status.HTTP_403_FORBIDDEN)
        
        serializer.save(author=request.user)
        
        return Response(success_response(
            details="Post created successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        ), status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update post (author only)"""
        instance = self.get_object()
        
        if instance.author != request.user and not request.user.is_staff:
            return Response(error_response(
                details="You can only edit your own posts.",
                status_code=status.HTTP_403_FORBIDDEN
            ), status=status.HTTP_403_FORBIDDEN)
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(success_response(
            details="Post updated successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        ))
    
    def destroy(self, request, *args, **kwargs):
        """Delete post (author or staff only)"""
        instance = self.get_object()
        
        if instance.author != request.user and not request.user.is_staff:
            return Response(error_response(
                details="You can only delete your own posts.",
                status_code=status.HTTP_403_FORBIDDEN
            ), status=status.HTTP_403_FORBIDDEN)
        
        instance.delete()
        return Response(success_response(
            details="Post deleted successfully.",
            data={},
            status_code=status.HTTP_204_NO_CONTENT
        ), status=status.HTTP_204_NO_CONTENT)
