from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True)
    helpful_count = serializers.IntegerField(read_only=True)
    is_helpful = serializers.SerializerMethodField()
    
    class Meta:
        model = Review
        fields = ['id', 'book', 'book_title', 'user', 'user_name', 'user_email', 'rating', 'title', 'body', 'is_approved', 'helpful_count', 'is_helpful', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'user_name', 'user_email', 'book_title', 'is_approved', 'helpful_count', 'created_at', 'updated_at']
    
    def get_is_helpful(self, obj):
        """Check if current user marked this review as helpful"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.helpful_users.filter(id=request.user.id).exists()
        return False


class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews"""
    
    class Meta:
        model = Review
        fields = ['book', 'rating', 'title', 'body']
