"""reviews/views.py — Book reviews with helpful voting"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.responses import success_response, error_response
from apps.core.throttles import AuthenticatedUserThrottle, AnonUserThrottle
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """Allow read access to anyone, write access only to authenticated users"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for book reviews.
    - List, retrieve: anyone (read-only for anonymous)
    - Create, update, delete: authenticated users only
    """
    queryset = Review.objects.filter(is_approved=True).select_related('user', 'book').prefetch_related('helpful_users')
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes = [AuthenticatedUserThrottle, AnonUserThrottle]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer
    
    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def list(self, request, *args, **kwargs):
        """List all approved reviews with pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        book_id = request.query_params.get('book')
        
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated_response = self.get_paginated_response(serializer.data)
            return Response(success_response(
                details="Reviews retrieved successfully.",
                data=paginated_response.data,
                status_code=status.HTTP_200_OK
            ))
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(success_response(
            details="Reviews retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        ))
    
    def retrieve(self, request, *args, **kwargs):
        """Get review details"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(success_response(
            details="Review retrieved successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        ))
    
    def create(self, request, *args, **kwargs):
        """Create a new review (authenticated users only)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if user already reviewed this book
        book_id = request.data.get('book')
        existing_review = Review.objects.filter(user=request.user, book_id=book_id).first()
        
        if existing_review:
            return Response(error_response(
                details="You have already reviewed this book.",
                status_code=status.HTTP_400_BAD_REQUEST
            ), status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save(user=request.user, is_approved=True)
        
        return Response(success_response(
            details="Review submitted successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        ), status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        """Update review (author only)"""
        instance = self.get_object()
        
        # Only author can update their review
        if instance.user != request.user and not request.user.is_staff:
            return Response(error_response(
                details="You can only edit your own reviews.",
                status_code=status.HTTP_403_FORBIDDEN
            ), status=status.HTTP_403_FORBIDDEN)
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(success_response(
            details="Review updated successfully.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        ))
    
    def destroy(self, request, *args, **kwargs):
        """Delete review (author or staff only)"""
        instance = self.get_object()
        
        if instance.user != request.user and not request.user.is_staff:
            return Response(error_response(
                details="You can only delete your own reviews.",
                status_code=status.HTTP_403_FORBIDDEN
            ), status=status.HTTP_403_FORBIDDEN)
        
        instance.delete()
        return Response(success_response(
            details="Review deleted successfully.",
            data={},
            status_code=status.HTTP_204_NO_CONTENT
        ), status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def toggle_helpful(self, request, pk=None):
        """Toggle helpful status for a review"""
        review = self.get_object()
        user = request.user
        
        # Don't allow users to mark their own reviews as helpful
        if review.user == user:
            return Response(error_response(
                details="You cannot mark your own review as helpful.",
                status_code=status.HTTP_400_BAD_REQUEST
            ), status=status.HTTP_400_BAD_REQUEST)
        
        if user in review.helpful_users.all():
            review.helpful_users.remove(user)
            is_helpful = False
            message = "Removed from helpful."
        else:
            review.helpful_users.add(user)
            is_helpful = True
            message = "Marked as helpful."
        
        return Response(success_response(
            details=message,
            data={
                'is_helpful': is_helpful,
                'helpful_count': review.helpful_count
            },
            status_code=status.HTTP_200_OK
        ))
