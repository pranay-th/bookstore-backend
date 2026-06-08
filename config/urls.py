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
    path('admin/', admin.site.urls),
    path('user/', include('apps.users.urls')),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]

    # App API routes
    # TODO: Uncomment routes as each app is implemented
    # path('api/users/',         include('apps.users.urls')),
    # path('api/authors/',       include('apps.authors.urls')),
    # path('api/categories/',    include('apps.categories.urls')),
    # path('api/books/',         include('apps.books.urls')),
    # path('api/inventory/',     include('apps.inventory.urls')),
    # path('api/cart/',          include('apps.cart.urls')),
    # path('api/wishlist/',      include('apps.wishlist.urls')),
    # path('api/orders/',        include('apps.orders.urls')),
    # path('api/payments/',      include('apps.payments.urls')),
    # path('api/coupons/',       include('apps.coupons.urls')),
    # path('api/reviews/',       include('apps.reviews.urls')),
    # path('api/notifications/', include('apps.notifications.urls')),
    # path('api/analytics/',     include('apps.analytics.urls')),

