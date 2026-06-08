"""
Initial migration — User, UserProfile, UserAddress.
Generated for Phase 0 foundation.
"""
import uuid
import django.db.models.deletion
import django.core.validators
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        # ---------------------------------------------------------
        # User
        # ---------------------------------------------------------
        migrations.CreateModel(
            name='User',
            fields=[
                ('password',     models.CharField(max_length=128, verbose_name='password')),
                ('last_login',   models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(
                    default=False,
                    help_text='Designates that this user has all permissions without explicitly assigning them.',
                    verbose_name='superuser status',
                )),
                ('id',          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email',       models.EmailField(max_length=254, unique=True)),
                ('first_name',  models.CharField(blank=True, max_length=150)),
                ('last_name',   models.CharField(blank=True, max_length=150)),
                ('phone',       models.CharField(blank=True, max_length=20)),
                ('is_active',   models.BooleanField(default=True)),
                ('is_staff',    models.BooleanField(default=False)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('groups',      models.ManyToManyField(
                    blank=True,
                    help_text='The groups this user belongs to.',
                    related_name='user_set',
                    related_query_name='user',
                    to='auth.group',
                    verbose_name='groups',
                )),
                ('user_permissions', models.ManyToManyField(
                    blank=True,
                    help_text='Specific permissions for this user.',
                    related_name='user_set',
                    related_query_name='user',
                    to='auth.permission',
                    verbose_name='user permissions',
                )),
            ],
            options={
                'db_table': 'users',
                'ordering': ['-date_joined'],
                'verbose_name': 'User',
                'verbose_name_plural': 'Users',
            },
        ),
        # ---------------------------------------------------------
        # UserProfile
        # ---------------------------------------------------------
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id',                  models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date_of_birth',       models.DateField(blank=True, null=True)),
                ('bio',                 models.TextField(blank=True)),
                ('avatar',              models.ImageField(blank=True, null=True, upload_to='avatars/')),
                ('preferred_language',  models.CharField(default='en', max_length=10)),
                ('preferred_currency',  models.CharField(default='USD', max_length=3)),
                ('newsletter_opt_in',   models.BooleanField(default=False)),
                ('created_at',          models.DateTimeField(auto_now_add=True)),
                ('updated_at',          models.DateTimeField(auto_now=True)),
                ('user',                models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'user_profiles',
                'verbose_name': 'User Profile',
                'verbose_name_plural': 'User Profiles',
            },
        ),
        # ---------------------------------------------------------
        # UserAddress
        # ---------------------------------------------------------
        migrations.CreateModel(
            name='UserAddress',
            fields=[
                ('id',           models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('address_type', models.CharField(
                    choices=[('shipping', 'Shipping'), ('billing', 'Billing')],
                    default='shipping', max_length=10,
                )),
                ('label',       models.CharField(blank=True, max_length=50)),
                ('full_name',   models.CharField(max_length=200)),
                ('line1',       models.CharField(max_length=255)),
                ('line2',       models.CharField(blank=True, max_length=255)),
                ('city',        models.CharField(max_length=100)),
                ('state',       models.CharField(max_length=100)),
                ('postal_code', models.CharField(max_length=20)),
                ('country',     models.CharField(help_text='ISO 3166-1 alpha-2', max_length=2)),
                ('phone',       models.CharField(blank=True, max_length=20)),
                ('is_default',  models.BooleanField(default=False)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('user',        models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='addresses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'user_addresses',
                'ordering': ['-is_default', '-created_at'],
                'verbose_name': 'User Address',
                'verbose_name_plural': 'User Addresses',
            },
        ),
    ]
