from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'full_name', 'email', 'usn', 'department', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'department', 'is_active', 'is_staff')
    search_fields = ('username', 'full_name', 'email', 'usn')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Student Profile', {
            'fields': ('role', 'full_name', 'usn', 'phone_number', 'department', 'semester')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Student Profile', {
            'fields': ('role', 'full_name', 'usn', 'phone_number', 'department', 'semester')
        }),
    )
