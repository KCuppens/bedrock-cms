"""
Role-Based Access Control (RBAC) models and utilities.

This module provides scoped permissions that allow users to be granted
permissions only for specific locales and/or path sections.
"""

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    CharField,
    DateTimeField,
    ForeignKey,
    TextField,
)

from apps.i18n.models import Locale


class ScopedLocale(models.Model):
    """
    Scopes a Django Group to specific locales.

    Users in the group will only have permissions for content
    in the specified locales.
    """

    group: ForeignKey = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="locale_scopes",
        help_text="Django group to scope",
    )
    locale: ForeignKey = models.ForeignKey(
        Locale,
        on_delete=models.CASCADE,
        related_name="group_scopes",
        help_text="Locale this group has access to",
    )
    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("group", "locale")]
        indexes = [
            models.Index(fields=["group", "locale"]),
        ]
        verbose_name = "Scoped Locale"
        verbose_name_plural = "Scoped Locales"

    def __str__(self):
        return f"{self.group.name} → {self.locale.name}"


class ScopedSection(models.Model):
    """
    Scopes a Django Group to specific path sections.

    Users in the group will only have permissions for content
    under the specified path prefixes.
    """

    group: ForeignKey = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name="section_scopes",
        help_text="Django group to scope",
    )
    path_prefix: CharField = models.CharField(
        max_length=255,
        help_text="Path prefix (e.g., '/blog', '/products'). Use '/' for root access.",
    )
    name: CharField = models.CharField(
        max_length=100,
        help_text="Human-readable name for this section (e.g., 'Blog', 'Products')",
    )
    description: TextField = models.TextField(
        blank=True, help_text="Optional description of what this section includes"
    )
    created_at: DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("group", "path_prefix")]
        indexes = [
            models.Index(fields=["group", "path_prefix"]),
        ]
        ordering = ["-path_prefix"]  # Longer paths first for proper matching
        verbose_name = "Scoped Section"
        verbose_name_plural = "Scoped Sections"

    def clean(self):
        """Validate path prefix format."""
        if not self.path_prefix.startswith("/"):
            raise ValidationError({"path_prefix": 'Path prefix must start with "/"'})

        # Normalize trailing slash (except for root)
        if len(self.path_prefix) > 1 and self.path_prefix.endswith("/"):
            self.path_prefix = self.path_prefix.rstrip("/")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def matches_path(self, path):
        """Check if this section scope matches a given path."""
        if self.path_prefix == "/":
            return True  # Root access matches everything
        return path.startswith(self.path_prefix + "/") or path == self.path_prefix

    def __str__(self):
        return f"{self.group.name} → {self.name} ({self.path_prefix})"


class RBACMixin:
    """
    Mixin to add RBAC scope checking methods to models.

    Usage:
        class Page(models.Model, RBACMixin):
            locale: ForeignKey = models.ForeignKey(Locale, ...)
            path: CharField = models.CharField(...)
    """

    def user_has_locale_access(self, user):
        """Check if user has access to this object's locale."""
        if not hasattr(self, "locale") or not user.is_authenticated:
            return False

        # Superuser has access to everything
        if user.is_superuser:
            return True

        # Check if any of the user's groups have access to this locale
        # Use exists() with direct join to avoid N+1
        return ScopedLocale.objects.filter(
            group__in=user.groups.all(), locale=self.locale
        ).exists()

    def user_has_section_access(self, user):
        """Check if user has access to this object's path section."""
        if not hasattr(self, "path") or not user.is_authenticated:
            return False

        # Superuser has access to everything
        if user.is_superuser:
            return True

        # Check if any of the user's groups have access to this path
        # Prefetch groups to avoid N+1 queries
        scoped_sections = ScopedSection.objects.filter(
            group__in=user.groups.all()
        ).select_related("group")

        # Use database filtering where possible
        for section in scoped_sections:
            if section.matches_path(self.path):
                return True
        return False

    def user_has_scope_access(self, user):
        """Check if user has both locale and section access."""
        return self.user_has_locale_access(user) and self.user_has_section_access(user)
