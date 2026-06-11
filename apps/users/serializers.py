"""
apps/users/serializers.py

Serializers for the users authentication flow.

Error handling strategy:
  - Field validation errors  → serializers.ValidationError (400)
  - Auth/business failures   → custom BookstoreAPIError subclasses
  - Infrastructure failures  → ServiceUnavailableError (503)

All exceptions bubble up to custom_exception_handler which wraps them
in the standard envelope and logs them at the appropriate level.
"""
import logging

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.core.exceptions import (
    AccountDisabledError,
    EmailDeliveryError,
    EmailNotVerifiedError,
    ServiceUnavailableError,
)
from .emails import send_otp_email, send_verification_email
from .models import User
from .tokens import generate_otp, verify_email_token, verify_otp

logger = logging.getLogger(__name__)


# ============================================================================
# Signup
# ============================================================================

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        help_text="Minimum 8 characters.",
    )
    role = serializers.ChoiceField(
        choices=[("CUSTOMER", "Customer"), ("AUTHOR", "Author")],
        default="CUSTOMER",
    )
    # Override model-level UniqueValidator message so it uses our wording
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="An account with this email already exists.",
            )
        ]
    )

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "phone", "role"]

    def validate_email(self, value):
        normalized = value.lower().strip()
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return normalized

    def validate_password(self, value):
        # At least one uppercase, one lowercase, one digit
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter."
            )
        if not any(c.islower() for c in value):
            raise serializers.ValidationError(
                "Password must contain at least one lowercase letter."
            )
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError(
                "Password must contain at least one digit."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        logger.info(
            "New user registered | email='%s' role=%s user_id=%s",
            user.email, user.role, user.id,
        )

        # Send verification email — failure raises EmailDeliveryError (503)
        # but we catch it here so signup still succeeds.
        # The user can use resend-verification to get a new link.
        try:
            send_verification_email(user)
        except EmailDeliveryError as exc:
            logger.warning(
                "Verification email failed after signup for user_id=%s: %s",
                user.id, exc,
            )
            # Don't block signup — user can resend verification
        except Exception as exc:
            logger.error(
                "Unexpected error sending verification email for user_id=%s: %s",
                user.id, exc, exc_info=True,
            )

        return user


class SignupResponseSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "full_name"]


# ============================================================================
# Email verification
# ============================================================================

class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        from apps.core.exceptions import TokenError as BookstoreTokenError

        try:
            user = verify_email_token(attrs["uid"], attrs["token"])
        except BookstoreTokenError as exc:
            # Convert to ValidationError so DRF returns 400
            raise serializers.ValidationError(str(exc))

        if user.is_email_verified:
            raise serializers.ValidationError(
                "This email address has already been verified."
            )

        attrs["user"] = user
        return attrs


# ============================================================================
# Login — step 1 (credentials → OTP)
# ============================================================================

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        password = attrs["password"]

        logger.debug("Login attempt for email='%s'", email)

        # Authenticate — returns None on wrong credentials
        user = authenticate(username=email, password=password)

        if user is None:
            # Check if user exists to give a slightly more helpful log
            # (but never reveal to the client whether the email exists)
            exists = User.objects.filter(email__iexact=email).exists()
            if exists:
                logger.warning(
                    "Failed login — wrong password for email='%s'", email
                )
            else:
                logger.warning(
                    "Failed login — email not found: '%s'", email
                )
            raise serializers.ValidationError(
                "Invalid email or password."
            )

        # Account status checks — raise typed exceptions (not ValidationError)
        # so the exception handler maps them to the correct HTTP codes
        if not user.is_active:
            logger.warning(
                "Login blocked — account disabled for user_id=%s", user.id
            )
            raise AccountDisabledError()

        if not user.is_email_verified:
            logger.info(
                "Login blocked — email not verified for user_id=%s", user.id
            )
            raise EmailNotVerifiedError()

        # Generate OTP and send — raises ServiceUnavailableError if Redis/email down
        try:
            otp = generate_otp(user)
        except ServiceUnavailableError:
            raise  # propagate 503 as-is

        try:
            send_otp_email(user, otp)
        except EmailDeliveryError:
            logger.error(
                "OTP email delivery failed for user_id=%s", user.id
            )
            raise ServiceUnavailableError(
                "Could not send OTP email. Please try again in a moment."
            )

        logger.info("OTP sent to user_id=%s email='%s'", user.id, user.email)
        attrs["user"] = user
        return attrs


# ============================================================================
# OTP verification — step 2 (OTP → JWT tokens)
# ============================================================================

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=4, max_length=8)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Don't reveal whether the email exists
            logger.warning(
                "OTP verify attempt for unknown email='%s'", email
            )
            raise serializers.ValidationError("Invalid or expired OTP.")

        # verify_otp raises ServiceUnavailableError if Redis is down
        try:
            valid = verify_otp(user, attrs["otp"])
        except ServiceUnavailableError:
            raise  # propagate 503

        if not valid:
            logger.warning(
                "OTP mismatch or expired for user_id=%s", user.id
            )
            raise serializers.ValidationError("Invalid or expired OTP.")

        attrs["user"] = user
        return attrs


# ============================================================================
# Refresh token
# ============================================================================

class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# ============================================================================
# Response shape (drf-spectacular only)
# ============================================================================

class LoginResponseSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ["id", "email", "role", "full_name"]
