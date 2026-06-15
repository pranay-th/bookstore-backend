from rest_framework import serializers
from .models import Review
from apps.books.models import Book


class ReviewSerializer(serializers.ModelSerializer):
    user_name     = serializers.SerializerMethodField()
    user_email    = serializers.EmailField(source='user.email', read_only=True)
    book_title    = serializers.CharField(source='book.title', read_only=True)
    helpful_count = serializers.IntegerField(read_only=True)
    is_helpful    = serializers.SerializerMethodField()

    class Meta:
        model  = Review
        fields = [
            'id', 'book', 'book_title', 'user', 'user_name', 'user_email',
            'rating', 'title', 'body', 'is_approved',
            'helpful_count', 'is_helpful', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'user_email', 'book_title',
            'is_approved', 'helpful_count', 'created_at', 'updated_at',
        ]

    def get_user_name(self, obj):
        return getattr(obj.user, 'full_name', None) or obj.user.email

    def get_is_helpful(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.helpful_users.filter(id=request.user.id).exists()
        return False


class ReviewCreateSerializer(serializers.Serializer):
    """Accept a free-text book title, look it up, and create the review."""
    book_title = serializers.CharField(max_length=255)
    rating     = serializers.IntegerField(min_value=1, max_value=5)
    title      = serializers.CharField(max_length=200, required=False, allow_blank=True)
    body       = serializers.CharField()

    def validate_book_title(self, value):
        book = Book.objects.filter(title__iexact=value.strip()).first()
        if not book:
            # Try partial match
            book = Book.objects.filter(title__icontains=value.strip()).first()
        if not book:
            raise serializers.ValidationError(
                f'No book found matching "{value}". Please check the title and try again.'
            )
        # Cache for create()
        self._book = book
        return value

    def create(self, validated_data):
        book = getattr(self, '_book', None)
        if not book:
            book = Book.objects.filter(
                title__icontains=validated_data['book_title'].strip()
            ).first()
        return Review.objects.create(
            book=book,
            user=validated_data['user'],
            rating=validated_data['rating'],
            title=validated_data.get('title', ''),
            body=validated_data['body'],
            is_approved=True,
        )
