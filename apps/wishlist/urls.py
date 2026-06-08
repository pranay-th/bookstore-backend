from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WishlistViewSet, WishlistItemViewSet

router = DefaultRouter()
router.register('wishlists',       WishlistViewSet,     basename='wishlist')
router.register('wishlists/items', WishlistItemViewSet, basename='wishlist-item')
urlpatterns = [path('', include(router.urls))]
