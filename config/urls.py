"""
Root URL configuration.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Admin + analytics dashboard inside admin
    path('admin/analytics/', include('apps.analytics.admin_urls')),
    path('admin/', admin.site.urls),

    # Health probe
    path('health/', include('apps.core.urls')),

    # Auth
    path('user/', include('apps.users.urls')),

    # Swagger / OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API routes
    path('api/', include('apps.authors.urls')),
    path('api/', include('apps.categories.urls')),
    path('api/', include('apps.books.urls')),
    path('api/', include('apps.books.author_urls')),
    path('api/', include('apps.notifications.urls')),
    path('api/', include('apps.cart.urls')),
    path('api/', include('apps.reviews.urls')),
    path('api/', include('apps.discussions.urls')),
    path('api/', include('apps.analytics.urls')),
    path('api/', include('apps.orders.urls')),
    path('api/', include('apps.coupons.urls')),
    # path('api/inventory/',  include('apps.inventory.urls')),
    # path('api/wishlist/',   include('apps.wishlist.urls')),
    # path('api/payments/',   include('apps.payments.urls')),
]
