from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InventoryItemViewSet

router = DefaultRouter()
router.register('inventory', InventoryItemViewSet, basename='inventory')
urlpatterns = [path('', include(router.urls))]
