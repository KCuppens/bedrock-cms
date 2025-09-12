"""Custom permissions for analytics functionality."""

from rest_framework.permissions import BasePermission


class AnalyticsViewPermission(BasePermission):
    """Permission to view analytics data.



    Requires user to be authenticated and have manager or admin role."""

    def has_permission(self, request, view):

        if not request.user.is_authenticated:

            return False

        # Allow managers and admins to view analytics

        return request.user.is_manager() or request.user.is_admin()


class AnalyticsEditPermission(BasePermission):
    """Permission to edit analytics data (create/update/delete).

    Requires user to be authenticated and have admin role."""

    def has_permission(self, request, view):

        if not request.user.is_authenticated:

            return False

        # Only admins can edit analytics data

        return request.user.is_admin()


class SecurityAnalyticsPermission(BasePermission):
    """Permission to view security analytics (threats, risks, assessments).

    Requires user to be authenticated and have appropriate security clearance.
    """

    def has_permission(self, request, view):

        if not request.user.is_authenticated:

            return False

        # For now, same as admin permission

        # Could be extended with security-specific roles

        return request.user.is_admin()

    def has_object_permission(self, request, view, obj):
        """Check object-level permissions for security items"""

        if not self.has_permission(request, view):

            return False

        # Additional object-level checks could go here

        # For example, check if user is assigned to the security item

        return True


class DashboardPermission(BasePermission):
    """Permission to access analytics dashboard.



    Allows different levels of access based on user role."""

    def has_permission(self, request, view):

        if not request.user.is_authenticated:

            return False

        # Members can view basic dashboard

        # Managers can view detailed analytics

        # Admins can view everything

        return (
            request.user.is_member()
            or request.user.is_manager()
            or request.user.is_admin()
        )

    def get_dashboard_scope(self, user):
        """Get dashboard data scope based on user role.

        Returns:
            str: Dashboard scope level ('basic', 'detailed', 'full')
        """

        if user.is_admin():

            return "full"

        elif user.is_manager():

            return "detailed"

        elif user.is_member():

            return "basic"

        else:

            return None


class ContentMetricsPermission(BasePermission):
    """Permission to view content performance metrics."""

    def has_permission(self, request, view):

        if not request.user.is_authenticated:

            return False

        # Content creators can view metrics for their content

        # Managers and admins can view all metrics

        return (
            request.user.is_member()
            or request.user.is_manager()
            or request.user.is_admin()
        )

    def has_object_permission(self, request, view, obj):
        """Check if user can view specific content metrics"""

        if not self.has_permission(request, view):

            return False

        # Admins and managers can view any metrics

        if request.user.is_admin() or request.user.is_manager():

            return True

        # Content creators can view metrics for content they created

        # This would require checking the related content object

        # For now, allow access to all authenticated users

        return True


class ExportPermission(BasePermission):
    """Permission to export analytics data."""

    def has_permission(self, request, view):

        if not request.user.is_authenticated:

            return False

        # Only managers and admins can export data

        return request.user.is_manager() or request.user.is_admin()
