from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, UserAddress


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    fieldsets     = (
        (None,           {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Permissions',  {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates',        {'fields': ('date_joined',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    # Override username-based fields from BaseUserAdmin
    filter_horizontal = ('groups', 'user_permissions',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'preferred_language', 'preferred_currency', 'newsletter_opt_in')
    search_fields = ('user__email',)


@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    list_display  = ('user', 'address_type', 'label', 'city', 'country', 'is_default')
    search_fields = ('user__email', 'city', 'country')
    list_filter   = ('address_type', 'country', 'is_default')
