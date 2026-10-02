from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "account_status", "is_active", "is_staff", "email_verified")
    list_filter = ("account_status", "is_staff", "email_verified")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("id", "last_login", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("first_name", "last_name", "phone")}),
        (
            "Estado",
            {"fields": ("account_status", "is_active", "email_verified")},
        ),
        (
            "Permisos",
            {"fields": ("is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Técnico", {"fields": ("id", "last_login", "created_at", "updated_at")}),
    )
