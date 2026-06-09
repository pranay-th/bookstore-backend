"""
apps/users/urls.py

Auth endpoints mounted at /user/ in config/urls.py

  POST /user/signup/                  Register + send verification email
  POST /user/verify-email/            Verify email (uid + token from link)
  POST /user/resend-verification/     Resend verification email
  POST /user/login/                   Credentials → OTP sent
  POST /user/verify-otp/              OTP → JWT tokens
  POST /user/token/refresh/           Refresh JWT access token
  POST /user/cron/send-reminders/     Cron-triggered reminder emails
"""

from django.urls import path
from .views import (
    SignupView,
    VerifyEmailView,
    ResendVerificationView,
    LoginView,
    VerifyOTPView,
    RefreshTokenView,
    CronSendRemindersView,
)

urlpatterns = [
    path("signup/",               SignupView.as_view(),              name="signup"),
    path("verify-email/",         VerifyEmailView.as_view(),         name="verify-email"),
    path("resend-verification/",  ResendVerificationView.as_view(),  name="resend-verification"),
    path("login/",                LoginView.as_view(),               name="login"),
    path("verify-otp/",           VerifyOTPView.as_view(),           name="verify-otp"),
    path("token/refresh/",        RefreshTokenView.as_view(),        name="token-refresh"),
    path("cron/send-reminders/",  CronSendRemindersView.as_view(),   name="cron-send-reminders"),
]
