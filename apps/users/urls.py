"""
users/urls.py — Phase 0 placeholder routes.
TODO: Register router in config/urls.py when ready.
"""
from django.urls import path
from .views import SignupView, LoginView

urlpatterns = [
    path(
        "signup/",
        SignupView.as_view(),
        name="signup"
    ),
    path(
        "login/",
        LoginView.as_view(),
        name="login"
    ),
]
