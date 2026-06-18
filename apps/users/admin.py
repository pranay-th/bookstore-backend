from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, UserAddress


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    extra = 0
    fields = ('date_of_birth', 'bio', 'avatar', 'preferred_language', 'newsletter_opt_in')


class UserAddressInline(admin.TabularInline):
    model = UserAddress
    extra = 0
    fields = ('address_type', 'label', 'city', 'country', 'is_default')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ('email', 'full_name', 'role', 'is_email_verified', 'is_staff', 'is_active', 'date_joined')
    list_filter   = ('role', 'is_staff', 'is_active', 'is_email_verified')
    search_fields = ('email', 'first_name', 'last_name')
    ordering      = ('-date_joined',)
    readonly_fields = ('date_joined', 'created_at', 'updated_at')
    inlines = (UserProfileInline, UserAddressInline)
    fieldsets = (
        (None,            {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'phone', 'role')}),
        ('Status',        {'fields': ('is_email_verified', 'is_active')}),
        ('Permissions',   {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('date_joined', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )
    filter_horizontal = ('groups', 'user_permissions',)

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.full_name
