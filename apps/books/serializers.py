from rest_framework import serializers
from .models import Book


class BookSerializer(serializers.ModelSerializer):
    # TODO: Add nested author / category serializers
    # TODO: Add avg_rating annotation field
    class Meta:
        model  = Book
        fields = '__all__'
