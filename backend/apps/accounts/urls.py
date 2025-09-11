from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import UserViewSet
from .auth_views import (
    login_view,
    logout_view,
    current_user_view,
    password_reset_view,
    password_reset_confirm_view,
    password_reset_verify_token,
    SessionCheckView,
)
from .role_views import (
    UserManagementViewSet,
    RoleViewSet,
    PermissionViewSet,
    get_scopes,
)
from apps.core.csrf_views import get_csrf_token
from .password_reset_redirect import password_reset_redirect, email_verification_redirect

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")
router.register(r"users-management", UserManagementViewSet, basename="user-management")
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"permissions", PermissionViewSet, basename="permissions")

urlpatterns = [
    path("", include(router.urls)),
    # Authentication endpoints
    path("csrf/", get_csrf_token, name="api-csrf-token"),
    path("login/", login_view, name="api-login"),
    path("logout/", logout_view, name="api-logout"),
    path("users/me/", current_user_view, name="api-current-user"),
    path("password-reset/", password_reset_view, name="api-password-reset"),
    path("password-reset/verify/", password_reset_verify_token, name="api-password-reset-verify"),
    path("password-reset/confirm/", password_reset_confirm_view, name="api-password-reset-confirm"),
    path("session/", SessionCheckView.as_view(), name="api-session-check"),
    # Permission endpoints
    path("scopes/", get_scopes, name="api-scopes"),
]
