"""
users/models.py

Phase 0 — User, UserProfile, UserAddress models.
UUID primary keys. NO authentication logic.
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


# ---------------------------------------------------------------------------
# Custom Manager
# ---------------------------------------------------------------------------

class UserManager(BaseUserManager):
    """
    Custom manager — creates standard and superusers.
    TODO: No login/register endpoints; manager used only for migrations & shell.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required.')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model — replaces Django's default.
    AUTH_USER_MODEL = 'users.User'

    TODO: No login/register/JWT endpoints in Phase 0.
    """

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name  = models.CharField(max_length=150, blank=True)
    phone      = models.CharField(max_length=20, blank=True)
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    # TODO: Add avatar / profile_picture field
    # TODO: Add role field (customer, admin, staff) in a later phase

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table  = 'users'
        ordering  = ['-date_joined']
        verbose_name        = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


# ---------------------------------------------------------------------------
# UserProfile
# ---------------------------------------------------------------------------

class UserProfile(models.Model):
    """
    Extended profile information for a User.
    One-to-one relationship.
    """

    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    date_of_birth = models.DateField(null=True, blank=True)
    bio           = models.TextField(blank=True)
    avatar        = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # Preferences
    preferred_language = models.CharField(max_length=10, default='en')
    preferred_currency = models.CharField(max_length=3, default='USD')
    newsletter_opt_in  = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # TODO: Add social media links
    # TODO: Add notification preferences

    class Meta:
        db_table = 'user_profiles'
        verbose_name        = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'Profile of {self.user.email}'


# ---------------------------------------------------------------------------
# UserAddress
# ---------------------------------------------------------------------------

class UserAddress(models.Model):
    """
    Shipping / billing addresses for a User.
    A user may have multiple addresses.
    """

    ADDRESS_TYPE_CHOICES = [
        ('shipping', 'Shipping'),
        ('billing',  'Billing'),
    ]

    id   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')

    address_type  = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='shipping')
    label         = models.CharField(max_length=50, blank=True, help_text='e.g. Home, Office')
    full_name     = models.CharField(max_length=200)
    line1         = models.CharField(max_length=255)
    line2         = models.CharField(max_length=255, blank=True)
    city          = models.CharField(max_length=100)
    state         = models.CharField(max_length=100)
    postal_code   = models.CharField(max_length=20)
    country       = models.CharField(max_length=2, help_text='ISO 3166-1 alpha-2')
    phone         = models.CharField(max_length=20, blank=True)
    is_default    = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table  = 'user_addresses'
        ordering  = ['-is_default', '-created_at']
        verbose_name        = 'User Address'
        verbose_name_plural = 'User Addresses'

    def __str__(self):
        return f'{self.label or self.address_type} — {self.user.email}'
