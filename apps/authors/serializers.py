from rest_framework import serializers
from .models import Author

class AuthorSerializer(serializers.ModelSerializer):
    # TODO: Add book count annotation
    class Meta:
        model  = Author
        fields = '__all__'
