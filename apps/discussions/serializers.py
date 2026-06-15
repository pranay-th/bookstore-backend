from rest_framework import serializers
from .models import Thread, Post


class PostSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    author_email = serializers.EmailField(source='author.email', read_only=True)
    
    class Meta:
        model = Post
        fields = ['id', 'thread', 'author', 'author_name', 'author_email', 'content', 'is_edited', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'author_name', 'author_email', 'is_edited', 'created_at', 'updated_at']


class ThreadSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    author_email = serializers.EmailField(source='author.email', read_only=True)
    post_count = serializers.IntegerField(read_only=True)
    last_post_at = serializers.DateTimeField(read_only=True)
    posts = PostSerializer(many=True, read_only=True)
    
    class Meta:
        model = Thread
        fields = ['id', 'title', 'author', 'author_name', 'author_email', 'category', 'is_pinned', 'is_locked', 'post_count', 'last_post_at', 'posts', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'author_name', 'author_email', 'post_count', 'last_post_at', 'is_pinned', 'is_locked', 'created_at', 'updated_at']


class ThreadListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for thread list view (without all posts)"""
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    post_count = serializers.IntegerField(read_only=True)
    last_post_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Thread
        fields = ['id', 'title', 'author_name', 'category', 'is_pinned', 'is_locked', 'post_count', 'last_post_at', 'created_at', 'updated_at']
