"""Custom authentication backends for RBAC scope enforcement."""

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import Permission

from apps.i18n.models import Locale

from .rbac import ScopedLocale, ScopedSection


class ScopedPermissionBackend(BaseBackend):
    """Custom authentication backend that enforces locale and section scopes.



    This backend checks if a user has the required permission AND

    if they have scope access (locale + section) to the object.

    """

    def has_perm(self, user_obj, perm, obj=None):
        """Check if user has permission, considering scopes.

        Args:
            user_obj: User instance
            perm: Permission string (e.g., 'cms.change_page')
            obj: Model instance being accessed (optional)

        Returns:
            bool: True if user has permission and scope access
        """

        if not user_obj.is_active:

            return False

        # Superuser bypasses all scope checks

        if user_obj.is_superuser:

            return True

        # Check if user has the base permission via Django's default system

        if not self._has_base_permission(user_obj, perm):

            return False

        # If no object is provided, we can't check scopes

        if obj is None:

            return True

        # Check scope access for the object

        if hasattr(obj, "user_has_scope_access"):

            return obj.user_has_scope_access(user_obj)

        # If object doesn't have scope methods, check manually

        return self._check_object_scopes(user_obj, obj)

    def _has_base_permission(self, user_obj, perm):
        """Check if user has the base permission via groups."""

        if not user_obj.is_active or user_obj.is_anonymous:

            return False

        # Get permission object

        try:

            app_label, codename = perm.split(".", 1)

            permission = Permission.objects.get(
                content_type__app_label=app_label, codename=codename
            )

        except (ValueError, Permission.DoesNotExist):

            return False

        # Check if user's groups have this permission

        return user_obj.groups.filter(permissions=permission).exists()

    def _check_object_scopes(self, user_obj, obj):
        """Manually check locale and section scopes for an object.

        Args:
            user_obj: User instance
            obj: Model instance

        Returns:
            bool: True if user has scope access
        """

        # Check locale scope if object has a locale

        if hasattr(obj, "locale"):

            locale_access = ScopedLocale.objects.filter(
                group__in=user_obj.groups.all(), locale=obj.locale
            ).exists()

            if not locale_access:

                return False

        # Check section scope if object has a path

        if hasattr(obj, "path"):

            scoped_sections = ScopedSection.objects.filter(
                group__in=user_obj.groups.all()
            ).select_related("group")

            section_access = any(
                section.matches_path(obj.path) for section in scoped_sections
            )

            if not section_access:

                return False

        return True

    def get_user_scoped_locales(self, user_obj):
        """Get all locales this user has access to."""

        if user_obj.is_superuser:

            return Locale.objects.filter(is_active=True)

        user_groups = user_obj.groups.all()

        locale_ids = ScopedLocale.objects.filter(group__in=user_groups).values_list(
            "locale_id", flat=True
        )

        return Locale.objects.filter(id__in=locale_ids, is_active=True)

    def get_user_scoped_sections(self, user_obj):
        """Get all section scopes this user has access to."""

        if user_obj.is_superuser:

            return ["/"]  # Root access for superusers

        user_groups = user_obj.groups.all()

        return list(
            ScopedSection.objects.filter(group__in=user_groups).values_list(
                "path_prefix", flat=True
            )
        )

    def user_can_access_locale(self, user_obj, locale):
        """Check if user can access a specific locale."""

        if user_obj.is_superuser:

            return True

        user_groups = user_obj.groups.all()

        return ScopedLocale.objects.filter(
            group__in=user_groups, locale=locale
        ).exists()

    def user_can_access_path(self, user_obj, path):
        """Check if user can access a specific path."""

        if user_obj.is_superuser:

            return True

        user_groups = user_obj.groups.all()

        scoped_sections = ScopedSection.objects.filter(group__in=user_groups)

        return any(section.matches_path(path) for section in scoped_sections)
