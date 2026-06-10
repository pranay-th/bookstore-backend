"""
apps/users/views.py

Authentication endpoints:

  POST /user/signup/                Register + send verification email
  POST /user/verify-email/          Verify email (uid + token from link)
  POST /user/resend-verification/   Resend verification email
  POST /user/login/                 Credentials → OTP sent
  POST /user/verify-otp/            OTP → JWT tokens
  POST /user/token/refresh/         Refresh JWT access token
  POST /user/cron/send-reminders/   Cron-triggered reminder emails

Error handling:
  All exceptions bubble to apps.core.exceptions.custom_exception_handler.
  Views never catch generic Exception — only specific typed exceptions
  that require view-level handling (e.g. TokenError from simplejwt).
"""
import logging

from django.conf import settings
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError as SimpleJWTTokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.exceptions import ServiceUnavailableError
from apps.core.responses import error_response, success_response
from apps.core.serializers import ErrorResponseSerializer, SuccessResponseSerializer

from .emails import send_verification_email
from .models import User
from .serializers import (
    LoginSerializer,
    RefreshTokenSerializer,
    SignupSerializer,
    VerifyEmailSerializer,
    VerifyOTPSerializer,
)
from .emails import send_reminder_email

logger = logging.getLogger(__name__)


# ============================================================================
# Signup
# ============================================================================

class SignupView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new user",
        description=(
            "Create a new account. A verification email is sent automatically "
            "after successful registration.\n\n"
            "**Allowed roles:** `CUSTOMER`, `AUTHOR`\n\n"
            "**Password rules:** min 8 chars, at least one uppercase, "
            "one lowercase, one digit."
        ),
        request=SignupSerializer,
        responses={
            201: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Registration successful — verification email sent",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "status": {
                                "success": True,
                                "code": 201,
                                "message": "Registration successful. Please check your email to verify your account.",
                            },
                            "data": {
                                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                "email": "customer@example.com",
                                "role": "CUSTOMER",
                                "full_name": "John Doe",
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Validation error",
                examples=[
                    OpenApiExample(
                        "Duplicate email",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "email: An account with this email already exists.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Weak password",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "password: Password must contain at least one uppercase letter.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Missing fields",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "email: This field is required. | password: This field is required.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Customer signup",
                value={
                    "email": "customer@example.com",
                    "password": "Secret@123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "phone": "+919876543210",
                    "role": "CUSTOMER",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Author signup",
                value={
                    "email": "author@example.com",
                    "password": "Author@456",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "phone": "+919876543210",
                    "role": "AUTHOR",
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return success_response(
            data={
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "full_name": user.full_name,
            },
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
        description=(
            "Resend the verification link to the given email address.\n\n"
            "Always returns 200 even if the email does not exist "
            "(to prevent email enumeration)."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Email sent (or silently skipped if not found)",
                examples=[
                    OpenApiExample(
                        "Sent",
                        value={
                            "status": {
                                "success": True,
                                "code": 200,
                                "message": "Verification email sent. Please check your inbox.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Email missing in request or already verified",
                examples=[
                    OpenApiExample(
                        "Already verified",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "This email address has already been verified.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
            503: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Email service unavailable",
                examples=[
                    OpenApiExample(
                        "Email service down",
                        value={
                            "status": {
                                "success": False,
                                "code": 503,
                                "message": "Email could not be sent. Please try again later.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
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
        email = request.data.get("email", "").strip().lower()

        if not email:
            return error_response("email: This field is required.", status_code=400)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Silently succeed — don't reveal whether the email exists
            logger.info(
                "Resend verification requested for unknown email='%s'", email
            )
            return success_response(
                message="If that email is registered, a verification link has been sent."
            )

        if user.is_email_verified:
            return error_response(
                "This email address has already been verified.",
                status_code=400,
            )

        # Raises ServiceUnavailableError (503) if email backend is down
        send_verification_email(user)

        logger.info(
            "Verification email resent to user_id=%s email='%s'", user.id, user.email
        )
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
        description=(
            "Validate the `uid` + `token` from the verification link.\n\n"
            "On success, `is_email_verified` is set to `true` and the user "
            "can proceed to log in."
        ),
        request=VerifyEmailSerializer,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Email verified successfully",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "status": {
                                "success": True,
                                "code": 200,
                                "message": "Email verified successfully. You can now log in.",
                            },
                            "data": {"email": "customer@example.com"},
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Invalid / expired token or already verified",
                examples=[
                    OpenApiExample(
                        "Expired link",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "Verification link has expired or is invalid.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Already verified",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "This email address has already been verified.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Request body",
                value={"uid": "<base64-encoded-uid>", "token": "<verification-token>"},
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

        logger.info(
            "Email verified for user_id=%s email='%s'", user.id, user.email
        )

        return success_response(
            data={"email": user.email},
            message="Email verified successfully. You can now log in.",
        )


# ============================================================================
# Login — step 1 (credentials → OTP)
# ============================================================================

class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Login — step 1 (credentials)",
        description=(
            "Validate email + password.\n\n"
            "On success a one-time OTP is sent to the user's email.\n\n"
            "Proceed to `POST /user/verify-otp/` with the OTP to receive JWT tokens.\n\n"
            "**Possible errors:**\n"
            "- `400` — wrong email/password\n"
            "- `403` — account disabled or email not verified\n"
            "- `503` — OTP/email service temporarily unavailable"
        ),
        request=LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="OTP sent to email",
                examples=[
                    OpenApiExample(
                        "OTP sent",
                        value={
                            "status": {
                                "success": True,
                                "code": 200,
                                "message": "OTP sent to customer@example.com. Enter it to complete login.",
                            },
                            "data": {"email": "customer@example.com"},
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Invalid credentials",
                examples=[
                    OpenApiExample(
                        "Wrong password",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "Invalid email or password.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
            403: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Account disabled or email not verified",
                examples=[
                    OpenApiExample(
                        "Email not verified",
                        value={
                            "status": {
                                "success": False,
                                "code": 403,
                                "message": "Email not verified. Please check your inbox for the verification link.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                    OpenApiExample(
                        "Account disabled",
                        value={
                            "status": {
                                "success": False,
                                "code": 403,
                                "message": "This account has been disabled. Please contact support.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
            503: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="OTP or email service unavailable",
                examples=[
                    OpenApiExample(
                        "Service unavailable",
                        value={
                            "status": {
                                "success": False,
                                "code": 503,
                                "message": "Could not send OTP email. Please try again in a moment.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "Customer login",
                value={"email": "customer@example.com", "password": "Secret@123"},
                request_only=True,
            ),
            OpenApiExample(
                "Admin login",
                value={"email": "admin@example.com", "password": "Admin@123"},
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
        description=(
            "Submit the OTP received by email.\n\n"
            "Returns a JWT access token and refresh token on success.\n\n"
            "**Possible errors:**\n"
            "- `400` — OTP invalid or expired\n"
            "- `503` — Redis temporarily unavailable"
        ),
        request=VerifyOTPSerializer,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Login successful — JWT tokens issued",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "status": {
                                "success": True,
                                "code": 200,
                                "message": "Login successful.",
                            },
                            "data": {
                                "access": "<jwt-access-token>",
                                "refresh": "<jwt-refresh-token>",
                                "user": {
                                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                                    "email": "customer@example.com",
                                    "role": "CUSTOMER",
                                    "full_name": "John Doe",
                                },
                            },
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="OTP invalid or expired",
                examples=[
                    OpenApiExample(
                        "Invalid OTP",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "Invalid or expired OTP.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
            503: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Redis unavailable",
                examples=[
                    OpenApiExample(
                        "Redis down",
                        value={
                            "status": {
                                "success": False,
                                "code": 503,
                                "message": "OTP service is temporarily unavailable. Please try again.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
        examples=[
            OpenApiExample(
                "OTP verification",
                value={"email": "customer@example.com", "otp": "847291"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        logger.info(
            "Login successful — JWT issued for user_id=%s role=%s",
            user.id, user.role,
        )

        return success_response(
            data={
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "role": user.role,
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
        description=(
            "Exchange a valid refresh token for a new access token.\n\n"
            "**Possible errors:**\n"
            "- `400` — refresh token missing\n"
            "- `401` — refresh token invalid or expired"
        ),
        request=RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="New access token issued",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "status": {
                                "success": True,
                                "code": 200,
                                "message": "Access token refreshed.",
                            },
                            "data": {"access": "<new-jwt-access-token>"},
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Missing refresh token",
                examples=[
                    OpenApiExample(
                        "Missing token",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "refresh: This field is required.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Invalid or expired refresh token",
                examples=[
                    OpenApiExample(
                        "Expired token",
                        value={
                            "status": {
                                "success": False,
                                "code": 401,
                                "message": "Token is invalid or expired.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
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
        refresh_token = request.data.get("refresh", "").strip()

        if not refresh_token:
            return error_response("refresh: This field is required.", status_code=400)

        try:
            token = RefreshToken(refresh_token)
            access = str(token.access_token)
        except SimpleJWTTokenError as exc:
            logger.warning("Refresh token rejected: %s", exc)
            return error_response("Token is invalid or expired.", status_code=401)

        logger.debug("Access token refreshed successfully")
        return success_response(
            data={"access": access},
            message="Access token refreshed.",
        )


# ============================================================================
# Cron — send reminder emails (called by crojob.org)
# ============================================================================

class CronSendRemindersView(APIView):
    permission_classes = [AllowAny]  # Auth via X-Cron-Secret header

    @extend_schema(
        summary="Cron — send scheduled reminder emails",
        description=(
            "Called by crojob.org on a schedule.\n\n"
            "**Authentication:** `X-Cron-Secret` header must match `CRON_SECRET_KEY` env var.\n\n"
            "**Request body:** a list of recipients with email, subject, and body.\n\n"
            "**Possible errors:**\n"
            "- `400` — missing or empty recipients list\n"
            "- `401` — wrong or missing X-Cron-Secret\n"
            "- `503` — email service unavailable"
        ),
        responses={
            200: OpenApiResponse(
                response=SuccessResponseSerializer,
                description="Reminder run complete",
                examples=[
                    OpenApiExample(
                        "Success",
                        value={
                            "status": {
                                "success": True,
                                "code": 200,
                                "message": "3 reminder(s) sent, 0 failed.",
                            },
                            "data": {"sent": 3, "failed": 0},
                        },
                        response_only=True,
                    ),
                ],
            ),
            401: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Invalid or missing cron secret",
                examples=[
                    OpenApiExample(
                        "Unauthorized",
                        value={
                            "status": {
                                "success": False,
                                "code": 401,
                                "message": "Unauthorized.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(
                response=ErrorResponseSerializer,
                description="Bad request body",
                examples=[
                    OpenApiExample(
                        "Empty recipients",
                        value={
                            "status": {
                                "success": False,
                                "code": 400,
                                "message": "Provide a non-empty 'recipients' list.",
                            },
                            "data": None,
                        },
                        response_only=True,
                    ),
                ],
            ),
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
        examples=[
            OpenApiExample(
                "Reminder payload",
                value={
                    "recipients": [
                        {
                            "email": "user@example.com",
                            "subject": "Don't forget your wishlist",
                            "body": "You have items waiting in your wishlist.",
                        }
                    ]
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        # Validate secret
        secret = request.headers.get("X-Cron-Secret", "")
        if not settings.CRON_SECRET_KEY or secret != settings.CRON_SECRET_KEY:
            logger.warning(
                "Cron endpoint called with invalid secret from IP=%s",
                request.META.get("REMOTE_ADDR"),
            )
            return error_response("Unauthorized.", status_code=401)

        recipients = request.data.get("recipients", [])
        if not isinstance(recipients, list) or not recipients:
            return error_response(
                "Provide a non-empty 'recipients' list.", status_code=400
            )

        sent = 0
        failed = 0

        for item in recipients:
            email = item.get("email", "").strip()
            subject = item.get("subject", "Reminder — Enterprise Book Store")
            body = item.get("body", "")

            if not email:
                logger.warning("Cron: skipping item with missing email: %s", item)
                failed += 1
                continue

            try:
                send_reminder_email(to_email=email, subject=subject, body=body)
                sent += 1
            except ServiceUnavailableError as exc:
                logger.error(
                    "Cron reminder failed (service unavailable) for '%s': %s",
                    email, exc,
                )
                failed += 1
            except Exception as exc:
                logger.error(
                    "Cron reminder unexpected failure for '%s': %s",
                    email, exc, exc_info=True,
                )
                failed += 1

        logger.info("Cron reminder run complete: sent=%d failed=%d", sent, failed)

        return success_response(
            data={"sent": sent, "failed": failed},
            message=f"{sent} reminder(s) sent, {failed} failed.",
        )
