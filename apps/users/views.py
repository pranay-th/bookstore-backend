"""
apps/users/views.py

Authentication endpoints:

  POST /user/signup/            Register a new user (sends verification email)
  POST /user/verify-email/      Verify email from link (uid + token)
  POST /user/login/             Credentials → OTP sent to email
  POST /user/verify-otp/        OTP → JWT access + refresh tokens
  POST /user/token/refresh/     Refresh JWT access token
  POST /user/resend-verification/ Resend verification email

  POST /user/cron/send-reminders/  Cron-triggered reminder emails (protected by secret)
"""

import logging

from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from drf_spectacular.utils import (
    extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
)

from apps.core.responses import success_response, error_response
from apps.core.serializers import SuccessResponseSerializer, ErrorResponseSerializer

from .serializers import (
    SignupSerializer,
    SignupResponseSerializer,
    VerifyEmailSerializer,
    LoginSerializer,
    LoginResponseSerializer,
    VerifyOTPSerializer,
    RefreshTokenSerializer,
)
from .emails import send_verification_email, send_reminder_email
from .tokens import make_verification_link
from .models import User

logger = logging.getLogger(__name__)


# ============================================================================
# Signup
# ============================================================================

class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new user",
        description=(
            "Create a new account. A verification email is sent automatically.\n\n"
            "Allowed roles: `CUSTOMER`, `AUTHOR`. ADMIN registration is not allowed."
        ),
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(response=SuccessResponseSerializer, description="Registration successful"),
            400: OpenApiResponse(response=ErrorResponseSerializer,   description="Validation error"),
        },
        examples=[
            OpenApiExample(
                "Customer Signup",
                value={"email": "customer@example.com", "password": "Secret@123",
                       "first_name": "John", "last_name": "Doe",
                       "phone": "+919876543210", "role": "CUSTOMER"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return success_response(
            data={"id": str(user.id), "email": user.email,
                  "role": user.role, "full_name": user.full_name},
            message="Registration successful. Please check your email to verify your account.",
            status_code=201,
        )


# ============================================================================
# Resend verification email
# ============================================================================

class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Resend email verification link",
        request=None,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Email sent"),
            400: OpenApiResponse(response=ErrorResponseSerializer,   description="Already verified or not found"),
        },
        examples=[
            OpenApiExample(
                "Request body",
                value={"email": "customer@example.com"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        email = request.data.get("email", "").strip()
        if not email:
            return error_response("Email is required.", status_code=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Return success anyway to avoid email enumeration
            return success_response(
                message="If that email exists, a verification link has been sent."
            )

        if user.is_email_verified:
            return error_response("Email is already verified.", status_code=400)

        try:
            send_verification_email(user)
        except Exception:
            return error_response("Could not send email. Please try again.", status_code=500)

        return success_response(
            message="Verification email sent. Please check your inbox."
        )


# ============================================================================
# Verify email
# ============================================================================

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify email address",
        description="Validate the uid + token from the verification link.",
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Email verified"),
            400: OpenApiResponse(response=ErrorResponseSerializer,   description="Invalid or expired link"),
        },
        examples=[
            OpenApiExample(
                "Request body",
                value={"uid": "<base64-uid>", "token": "<token>"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])

        return success_response(
            data={"email": user.email},
            message="Email verified successfully. You can now log in.",
        )


# ============================================================================
# Login — step 1
# ============================================================================

class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Login — step 1 (credentials)",
        description=(
            "Validate email + password. If correct and email is verified, "
            "a one-time OTP is sent to the user's email.\n\n"
            "Then call `POST /user/verify-otp/` with the OTP to receive JWT tokens."
        ),
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="OTP sent"),
            400: OpenApiResponse(response=ErrorResponseSerializer,   description="Invalid credentials or unverified email"),
        },
        examples=[
            OpenApiExample(
                "Login request",
                value={"email": "customer@example.com", "password": "Secret@123"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        return success_response(
            data={"email": user.email},
            message=f"OTP sent to {user.email}. Enter it to complete login.",
        )


# ============================================================================
# Verify OTP — step 2
# ============================================================================

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Login — step 2 (OTP → JWT tokens)",
        description="Submit the OTP received by email. Returns JWT access and refresh tokens.",
        request=VerifyOTPSerializer,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Login successful — tokens returned"),
            400: OpenApiResponse(response=ErrorResponseSerializer,   description="Invalid or expired OTP"),
        },
        examples=[
            OpenApiExample(
                "OTP verification",
                value={"email": "customer@example.com", "otp": "847291"},
                request_only=True,
            ),
            OpenApiExample(
                "Success response",
                value={
                    "status": {"success": True, "code": 200, "message": "Login successful."},
                    "data": {
                        "access":  "<jwt-access-token>",
                        "refresh": "<jwt-refresh-token>",
                        "user": {"id": "uuid", "email": "customer@example.com",
                                 "role": "CUSTOMER", "full_name": "John Doe"},
                    },
                },
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user    = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return success_response(
            data={
                "access":  str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id":        str(user.id),
                    "email":     user.email,
                    "role":      user.role,
                    "full_name": user.full_name,
                },
            },
            message="Login successful.",
        )


# ============================================================================
# Refresh token
# ============================================================================

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Refresh JWT access token",
        request=RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="New access token"),
            401: OpenApiResponse(response=ErrorResponseSerializer,   description="Invalid or expired refresh token"),
        },
        examples=[
            OpenApiExample(
                "Refresh request",
                value={"refresh": "<jwt-refresh-token>"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        refresh_token = request.data.get("refresh", "")
        if not refresh_token:
            return error_response("Refresh token is required.", status_code=400)

        try:
            token  = RefreshToken(refresh_token)
            access = str(token.access_token)
        except TokenError as exc:
            return error_response(str(exc), status_code=401)

        return success_response(
            data={"access": access},
            message="Access token refreshed.",
        )


# ============================================================================
# Cron endpoint — triggered by crojob.org
# ============================================================================

class CronSendRemindersView(APIView):
    """
    POST /user/cron/send-reminders/

    Called by crojob.org on a schedule.
    Protected by X-Cron-Secret header matching CRON_SECRET_KEY in settings.

    Request body:
        {
            "recipients": [
                {"email": "user@example.com", "subject": "...", "body": "..."},
                ...
            ]
        }
    """
    permission_classes = [AllowAny]  # Auth is via the secret header, not JWT

    @extend_schema(
        summary="Cron — send scheduled reminder emails",
        description=(
            "Protected endpoint called by crojob.org.\n\n"
            "Requires `X-Cron-Secret` header matching `CRON_SECRET_KEY` env var.\n\n"
            "Sends reminder emails to the provided list of recipients."
        ),
        responses={
            200: OpenApiResponse(response=SuccessResponseSerializer, description="Emails dispatched"),
            401: OpenApiResponse(response=ErrorResponseSerializer,   description="Invalid secret"),
            400: OpenApiResponse(response=ErrorResponseSerializer,   description="Bad request body"),
        },
        parameters=[
            OpenApiParameter(
                name="X-Cron-Secret",
                location=OpenApiParameter.HEADER,
                description="Must match CRON_SECRET_KEY env var.",
                required=True,
                type=str,
            ),
        ],
    )
    def post(self, request):
        # Validate secret
        secret = request.headers.get("X-Cron-Secret", "")
        if not settings.CRON_SECRET_KEY or secret != settings.CRON_SECRET_KEY:
            return error_response("Unauthorized.", status_code=401)

        recipients = request.data.get("recipients", [])
        if not isinstance(recipients, list) or not recipients:
            return error_response(
                "Provide a non-empty 'recipients' list.", status_code=400
            )

        sent    = []
        failed  = []

        for item in recipients:
            email   = item.get("email", "").strip()
            subject = item.get("subject", "Reminder from Enterprise Book Store")
            body    = item.get("body", "")

            if not email:
                failed.append({"email": email, "reason": "Missing email."})
                continue

            try:
                send_reminder_email(to_email=email, subject=subject, body=body)
                sent.append(email)
            except Exception as exc:
                logger.error("Cron reminder failed for %s: %s", email, exc)
                failed.append({"email": email, "reason": str(exc)})

        return success_response(
            data={"sent": len(sent), "failed": len(failed)},
            message=f"{len(sent)} reminder(s) sent, {len(failed)} failed.",
        )
