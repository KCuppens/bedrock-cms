from rest_framework import permissions


class HasGroup(permissions.BasePermission):
    """Permission class to check if user belongs to a specific group"""

    def __init__(self, group_name):
        self.group_name = group_name

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.groups.filter(name=self.group_name).exists()


class IsAdminOrReadOnly(permissions.BasePermission):
    """Permission that allows admins to modify, others to read only"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Read permissions for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions only for admins
        return request.user.is_admin()


class IsOwnerOrAdmin(permissions.BasePermission):
    """Permission that allows owners or admins to access"""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Admin users can access everything
        if request.user.is_admin():
            return True

        # Check if object has a user field
        if hasattr(obj, "user"):
            return obj.user == request.user

        # Check if object has a created_by field
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user

        # Default to checking if obj is the user themselves
        return obj == request.user


class IsManagerOrAdmin(permissions.BasePermission):
    """Permission that allows managers or admins to access"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_manager()


class IsMemberOrAbove(permissions.BasePermission):
    """Permission that allows members, managers, or admins to access"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return request.user.is_member()


class RBACPermission(permissions.BasePermission):
    """
    Role-Based Access Control permission that checks both locale and section access.

    This permission integrates with the RBAC system to verify that users have
    the appropriate permissions for the locale and path section of the object
    they're trying to access.
    """

    def has_permission(self, request, view):
        """Check if user is authenticated - object-level checks happen in has_object_permission."""
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user has RBAC access to this specific object."""
        if not request.user or not request.user.is_authenticated:
            return False

        # Superuser has access to everything
        if request.user.is_superuser:
            return True

        # Check if object has RBAC support
        if not hasattr(obj, "user_has_scope_access"):
            # If no RBAC support, fall back to standard permissions
            return True

        # Use the object's RBAC method to check access
        return obj.user_has_scope_access(request.user)
