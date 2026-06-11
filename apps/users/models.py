"""
users/models.py

Enterprise Book Store
Users Module

Models:
- User
- UserProfile
- UserAddress

AUTH_USER_MODEL = "users.User"
"""

import uuid

from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)


# ============================================================================
# Validators
# ============================================================================

phone_validator = RegexValidator(
    regex=r'^\+?[1-9]\d{7,14}$',
    message='Enter a valid phone number.'
)


# ============================================================================
# User Manager
# ============================================================================

class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):

        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):

        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            email,
            password,
            **extra_fields
        )


# ============================================================================
# User
# ============================================================================

class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = (
        ("CUSTOMER", "Customer"),
        ("AUTHOR", "Author"),
        ("ADMIN", "Admin"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    email = models.EmailField(
        unique=True
    )

    first_name = models.CharField(
        max_length=150
    )

    last_name = models.CharField(
        max_length=150
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator]
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="CUSTOMER"
    )

    is_active = models.BooleanField(
        default=True
    )

    is_staff = models.BooleanField(
        default=False
    )

    is_email_verified = models.BooleanField(
        default=False,
        help_text="Set to True after the user clicks the verification link."
    )

    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    date_joined = models.DateTimeField(
        auto_now_add=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "first_name",
        "last_name",
    ]

    class Meta:

        db_table = "users"

        ordering = [
            "-date_joined"
        ]

        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


# ============================================================================
# User Profile
# ============================================================================

class UserProfile(models.Model):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True
    )

    bio = models.TextField(
        blank=True
    )

    avatar = models.ImageField(
        upload_to="avatars/",
        null=True,
        blank=True
    )

    preferred_language = models.CharField(
        max_length=10,
        default="en"
    )

    newsletter_opt_in = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "user_profiles"

    def __str__(self):
        return f"Profile: {self.user.email}"


# ============================================================================
# User Address
# ============================================================================

class UserAddress(models.Model):

    ADDRESS_TYPE_CHOICES = (
        ("shipping", "Shipping"),
        ("billing", "Billing"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses"
    )

    address_type = models.CharField(
        max_length=20,
        choices=ADDRESS_TYPE_CHOICES,
        default="shipping"
    )

    label = models.CharField(
        max_length=50,
        blank=True
    )

    full_name = models.CharField(
        max_length=255
    )

    line1 = models.CharField(
        max_length=255
    )

    line2 = models.CharField(
        max_length=255,
        blank=True
    )

    city = models.CharField(
        max_length=100
    )

    state = models.CharField(
        max_length=100
    )

    postal_code = models.CharField(
        max_length=20
    )

    country = models.CharField(
        max_length=2,
        help_text="ISO 3166-1 alpha-2"
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator]
    )

    is_default = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "user_addresses"

        ordering = [
            "-is_default",
            "-created_at"
        ]

        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["is_default"]),
        ]

    def save(self, *args, **kwargs):

        if self.is_default:
            UserAddress.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(
                pk=self.pk
            ).update(
                is_default=False
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.label or self.address_type} "
            f"- {self.user.email}"
        )