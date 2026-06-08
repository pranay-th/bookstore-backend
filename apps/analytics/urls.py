from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PageViewViewSet

router = DefaultRouter()
router.register('analytics/pageviews', PageViewViewSet, basename='pageview')
urlpatterns = [path('', include(router.urls))]
