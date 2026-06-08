"""
users/views.py — Phase 0 placeholders.
NO authentication / login / register endpoints.
TODO: Implement UserViewSet, UserProfileViewSet, UserAddressViewSet.
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import User, UserProfile, UserAddress
from .serializers import UserSerializer, UserProfileSerializer, UserAddressSerializer


class UserViewSet(viewsets.ModelViewSet):
    """
    CRUD for Users.
    TODO: Add permission classes once auth is implemented.
    TODO: Filter queryset to request.user for non-admin requests.
    """
    queryset         = User.objects.all()
    serializer_class = UserSerializer

    # TODO: def get_queryset(self): restrict to authenticated user or admin


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    CRUD for UserProfiles.
    TODO: Enforce one-to-one constraint in create.
    """
    queryset         = UserProfile.objects.select_related('user')
    serializer_class = UserProfileSerializer


class UserAddressViewSet(viewsets.ModelViewSet):
    """
    CRUD for UserAddresses.
    TODO: Restrict to addresses belonging to the authenticated user.
    TODO: Enforce only one default address per type per user.
    """
    queryset         = UserAddress.objects.select_related('user')
    serializer_class = UserAddressSerializer
