"""
apps/users/serializers.py

Serializers for the users authentication flow:
  - SignupSerializer          : validate + create user, send verification email
  - LoginSerializer           : validate credentials + email verified, send OTP
  - VerifyEmailSerializer     : validate uid + token, mark email verified
  - VerifyOTPSerializer       : validate OTP, return JWT tokens
  - RefreshTokenSerializer    : wraps simplejwt RefreshToken
"""

import logging

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .emails import send_verification_email, send_otp_email
from .tokens import verify_email_token, generate_otp, verify_otp

logger = logging.getLogger(__name__)


# ============================================================================
# Signup
# ============================================================================

class SignupSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True, min_length=8)
    role     = serializers.ChoiceField(
        choices=[("CUSTOMER", "Customer"), ("AUTHOR", "Author")],
        default="CUSTOMER",
    )

    class Meta:
        model  = User
        fields = ["email", "password", "first_name", "last_name", "phone", "role"]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user     = User.objects.create_user(password=password, **validated_data)

        # Send verification email — failure is logged but doesn't block signup
        try:
            send_verification_email(user)
        except Exception:
            logger.error("Failed to send verification email to %s", user.email)

        return user


class SignupResponseSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model  = User
        fields = ["id", "email", "role", "full_name"]


# ============================================================================
# Email verification
# ============================================================================

class VerifyEmailSerializer(serializers.Serializer):
    uid   = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        user = verify_email_token(attrs["uid"], attrs["token"])
        if user is None:
            raise serializers.ValidationError("Invalid or expired verification link.")
        if user.is_email_verified:
            raise serializers.ValidationError("Email is already verified.")
        attrs["user"] = user
        return attrs


# ============================================================================
# Login — step 1 (credentials → OTP sent)
# ============================================================================

class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["email"], password=attrs["password"])

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("Account is disabled.")

        if not user.is_email_verified:
            raise serializers.ValidationError(
                "Email not verified. Please check your inbox for the verification link."
            )

        # Generate OTP and send via email
        otp = generate_otp(user)
        try:
            send_otp_email(user, otp)
        except Exception:
            logger.error("Failed to send OTP email to %s", user.email)
            raise serializers.ValidationError(
                "Could not send OTP. Please try again."
            )

        attrs["user"] = user
        return attrs


# ============================================================================
# OTP verification — step 2 (OTP → JWT tokens issued)
# ============================================================================

class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp   = serializers.CharField(min_length=4, max_length=8)

    def validate(self, attrs):
        try:
            user = User.objects.get(email=attrs["email"])
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid request.")

        if not verify_otp(user, attrs["otp"]):
            raise serializers.ValidationError("Invalid or expired OTP.")

        attrs["user"] = user
        return attrs


# ============================================================================
# Refresh token
# ============================================================================

class RefreshTokenSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# ============================================================================
# Response shapes (used by drf-spectacular only)
# ============================================================================

class LoginResponseSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model  = User
        fields = ["id", "email", "role", "full_name"]
