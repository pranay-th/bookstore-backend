"""reviews/views.py — Book reviews with helpful voting"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from apps.core.responses import success_response, error_response
from apps.core.throttles import AuthenticatedUserThrottle, AnonUserThrottle
from .models import Review
from .serializers import ReviewSerializer, ReviewCreateSerializer


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.filter(is_approved=True).select_related('user', 'book').prefetch_related('helpful_users')
    permission_classes = [IsAuthenticatedOrReadOnly]
    throttle_classes = [AuthenticatedUserThrottle, AnonUserThrottle]

    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        return ReviewSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        book_id = request.query_params.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            paginated = self.get_paginated_response(serializer.data)
            return success_response(data=paginated.data, message="Reviews retrieved successfully.")
        serializer = self.get_serializer(queryset, many=True)
        return success_response(data=serializer.data, message="Reviews retrieved successfully.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data, message="Review retrieved successfully.")

    def create(self, request, *args, **kwargs):
        """Accept book_title (text), look it up, create the review."""
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Duplicate check
        book = getattr(serializer, '_book', None)
        if book and Review.objects.filter(user=request.user, book=book).exists():
            return error_response(message="You have already reviewed this book.", status_code=400)

        review = serializer.create({**serializer.validated_data, 'user': request.user})

        # Notify reviewer (non-fatal)
        try:
            from apps.notifications.models import Notification
            Notification.objects.create(
                user=request.user,
                notif_type='review_approved',
                title='Review Published',
                message=f'Your review of "{review.book.title}" has been published.',
            )
        except Exception:
            pass

        return success_response(
            data=ReviewSerializer(review, context={'request': request}).data,
            message="Review submitted successfully.",
            status_code=201,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user and not request.user.is_staff:
            return error_response(message="You can only edit your own reviews.", status_code=403)
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(data=serializer.data, message="Review updated successfully.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user and not request.user.is_staff:
            return error_response(message="You can only delete your own reviews.", status_code=403)
        instance.delete()
        return success_response(data={}, message="Review deleted successfully.", status_code=204)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def toggle_helpful(self, request, pk=None):
        review = self.get_object()
        user = request.user
        if review.user == user:
            return error_response(message="You cannot mark your own review as helpful.", status_code=400)
        if user in review.helpful_users.all():
            review.helpful_users.remove(user)
            is_helpful = False
            msg = "Removed from helpful."
        else:
            review.helpful_users.add(user)
            is_helpful = True
            msg = "Marked as helpful."
        return success_response(
            data={'is_helpful': is_helpful, 'helpful_count': review.helpful_count},
            message=msg,
        )
