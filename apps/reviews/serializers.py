from rest_framework import serializers
from .models import Review
from apps.books.models import Book


class ReviewSerializer(serializers.ModelSerializer):
    user_name     = serializers.SerializerMethodField()
    user_email    = serializers.EmailField(source='user.email', read_only=True)
    book_title    = serializers.CharField(source='book.title', read_only=True)
    helpful_count = serializers.SerializerMethodField()
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

    def get_helpful_count(self, obj):
        return obj.helpful_users.count()

    def get_is_helpful(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.helpful_users.filter(id=request.user.id).exists()
        return False


class ReviewCreateSerializer(serializers.Serializer):
    """Accept a free-text book title, look it up, create the review."""
    book_title = serializers.CharField(max_length=255)
    rating     = serializers.IntegerField(min_value=1, max_value=5)
    title      = serializers.CharField(max_length=200, required=False, allow_blank=True, default='')
    body       = serializers.CharField()

    def validate(self, attrs):
        """Resolve book during validation so it's available in create()."""
        title = attrs['book_title'].strip()
        book  = Book.objects.filter(title__iexact=title).first()
        if not book:
            book = Book.objects.filter(title__icontains=title).first()
        if not book:
            raise serializers.ValidationError({
                'book_title': f'No book found matching "{title}". Please check the title and try again.'
            })
        attrs['_book'] = book
        return attrs

    def create(self, validated_data):
        book = validated_data.pop('_book')
        validated_data.pop('book_title')
        user = validated_data.pop('user')
        return Review.objects.create(
            book=book,
            user=user,
            rating=validated_data['rating'],
            title=validated_data.get('title', ''),
            body=validated_data['body'],
            is_approved=True,
        )
