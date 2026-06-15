"""
cart/urls.py

Routes (mounted under /api/ in config/urls.py):

  GET    /api/cart/                       Retrieve the current user's cart
  POST   /api/cart/add/                   Add a book (or increment if present)
  DELETE /api/cart/clear/                 Empty the cart
  POST   /api/cart/<id>/increment/        Increment a line item by 1
  POST   /api/cart/<id>/decrement/        Decrement a line item by 1 (removes at 0)
  PATCH  /api/cart/<id>/quantity/         Set a line item's absolute quantity
  DELETE /api/cart/<id>/remove/           Remove a line item entirely
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import CartViewSet

router = DefaultRouter()
router.register('cart', CartViewSet, basename='cart')

urlpatterns = [path('', include(router.urls))]
