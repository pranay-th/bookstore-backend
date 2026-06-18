from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.analytics_dashboard, name='analytics-dashboard'),
    path('api/', views.analytics_api_proxy, name='analytics-api-proxy'),
]
