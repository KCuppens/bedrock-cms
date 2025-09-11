from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile
from .rbac import ScopedLocale, ScopedSection


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model"""

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name", "avatar", "last_seen")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {"fields": ("last_login", "date_joined", "created_at", "updated_at")},
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )
    list_display = ("email", "name", "is_staff", "is_active", "last_seen", "created_at")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "date_joined")
    search_fields = ("email", "name")
    ordering = ("-created_at",)
    filter_horizontal = ("groups", "user_permissions")
    readonly_fields = (
        "last_login",
        "date_joined",
        "created_at",
        "updated_at",
        "last_seen",
    )


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile"""

    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model"""

    list_display = (
        "user",
        "location",
        "timezone",
        "receive_notifications",
        "created_at",
    )
    list_filter = (
        "timezone",
        "language",
        "receive_notifications",
        "receive_marketing_emails",
    )
    search_fields = ("user__email", "user__name", "location")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("user",)}),
        (_("Profile Information"), {"fields": ("bio", "location", "website", "phone")}),
        (
            _("Preferences"),
            {
                "fields": (
                    "timezone",
                    "language",
                    "receive_notifications",
                    "receive_marketing_emails",
                )
            },
        ),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


# Add UserProfile inline to UserAdmin
UserAdmin.inlines = [UserProfileInline]


# RBAC Admin Classes


class ScopedLocaleInline(admin.TabularInline):
    """Inline admin for ScopedLocale."""

    model = ScopedLocale
    extra = 1
    autocomplete_fields = ["locale"]


class ScopedSectionInline(admin.TabularInline):
    """Inline admin for ScopedSection."""

    model = ScopedSection
    extra = 1
    fields = ["path_prefix", "name", "description"]


@admin.register(ScopedLocale)
class ScopedLocaleAdmin(admin.ModelAdmin):
    """Admin for ScopedLocale model."""

    list_display = ["group", "locale", "created_at"]
    list_filter = ["locale", "created_at"]
    search_fields = ["group__name", "locale__name", "locale__code"]
    autocomplete_fields = ["group", "locale"]
    readonly_fields = ["created_at"]


@admin.register(ScopedSection)
class ScopedSectionAdmin(admin.ModelAdmin):
    """Admin for ScopedSection model."""

    list_display = ["group", "name", "path_prefix", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["group__name", "name", "path_prefix", "description"]
    autocomplete_fields = ["group"]
    readonly_fields = ["created_at"]

    fieldsets = [
        ("Group Assignment", {"fields": ["group"]}),
        ("Section Details", {"fields": ["path_prefix", "name", "description"]}),
        ("Metadata", {"fields": ["created_at"], "classes": ["collapse"]}),
    ]


# Unregister default GroupAdmin and register enhanced version
admin.site.unregister(Group)


@admin.register(Group)
class EnhancedGroupAdmin(BaseGroupAdmin):
    """Enhanced Group admin with RBAC scope inlines."""

    inlines = [ScopedLocaleInline, ScopedSectionInline]

    fieldsets = (
        (None, {"fields": ("name", "permissions")}),
        (
            "Scope Configuration",
            {
                "description": "Configure which locales and sections this group can access. If no scopes are defined, the group has no content access restrictions.",
                "classes": ("collapse",),
                "fields": (),  # Scopes are handled via inlines
            },
        ),
    )

    def save_related(self, request, form, formsets, change):
        """Save related objects including inlines."""
        super().save_related(request, form, formsets, change)

        # Add helpful message about scope configuration
        if not change:  # New group
            self.message_user(
                request,
                "Group created successfully. Configure locale and section scopes below to restrict access.",
                level="info",
            )
