from rest_framework import serializers
from .models import Thread, Post


class PostSerializer(serializers.ModelSerializer):
    author_name  = serializers.SerializerMethodField()
    author_email = serializers.EmailField(source='author.email', read_only=True)

    class Meta:
        model  = Post
        fields = [
            'id', 'thread', 'author', 'author_name', 'author_email',
            'content', 'is_edited', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'thread', 'author', 'author_name', 'author_email',
            'is_edited', 'created_at', 'updated_at',
        ]

    def get_author_name(self, obj):
        return getattr(obj.author, 'full_name', None) or obj.author.email


class ThreadListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for thread list (no posts)."""
    author_name  = serializers.SerializerMethodField()
    post_count   = serializers.SerializerMethodField()
    last_post_at = serializers.SerializerMethodField()

    class Meta:
        model  = Thread
        fields = [
            'id', 'title', 'author_name', 'category',
            'is_pinned', 'is_locked',
            'post_count', 'last_post_at',
            'created_at', 'updated_at',
        ]

    def get_author_name(self, obj):
        return getattr(obj.author, 'full_name', None) or obj.author.email

    def get_post_count(self, obj):
        return obj.posts.count()

    def get_last_post_at(self, obj):
        last = obj.posts.order_by('-created_at').first()
        val  = last.created_at if last else obj.created_at
        return val.isoformat() if val else None


class ThreadSerializer(serializers.ModelSerializer):
    author_name  = serializers.SerializerMethodField()
    author_email = serializers.EmailField(source='author.email', read_only=True)
    post_count   = serializers.SerializerMethodField()
    last_post_at = serializers.SerializerMethodField()
    posts        = PostSerializer(many=True, read_only=True)

    class Meta:
        model  = Thread
        fields = [
            'id', 'title', 'author', 'author_name', 'author_email',
            'category', 'is_pinned', 'is_locked',
            'post_count', 'last_post_at',
            'posts', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'author', 'author_name', 'author_email',
            'post_count', 'last_post_at',
            'is_pinned', 'is_locked',
            'created_at', 'updated_at',
        ]

    def get_author_name(self, obj):
        return getattr(obj.author, 'full_name', None) or obj.author.email

    def get_post_count(self, obj):
        return obj.posts.count()

    def get_last_post_at(self, obj):
        last = obj.posts.order_by('-created_at').first()
        val  = last.created_at if last else obj.created_at
        return val.isoformat() if val else None
