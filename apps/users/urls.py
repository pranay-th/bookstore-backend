"""
users/urls.py — Phase 0 placeholder routes.
TODO: Register router in config/urls.py when ready.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, UserProfileViewSet, UserAddressViewSet

router = DefaultRouter()
router.register('users',           UserViewSet,        basename='user')
router.register('users/profiles',  UserProfileViewSet, basename='user-profile')
router.register('users/addresses', UserAddressViewSet, basename='user-address')

urlpatterns = [
    path('', include(router.urls)),
]
