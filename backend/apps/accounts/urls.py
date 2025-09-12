from django.urls import include, path

from rest_framework.routers import DefaultRouter

from apps.core.csrf_views import get_csrf_token

from .auth_views import (
    SessionCheckView,
    current_user_view,
    login_view,
    logout_view,
    password_reset_confirm_view,
    password_reset_verify_token,
    password_reset_view,
)
from .role_views import (
    PermissionViewSet,
    RoleViewSet,
    UserManagementViewSet,
    get_scopes,
)
from .views import UserViewSet

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
    path(
        "password-reset/verify/",
        password_reset_verify_token,
        name="api-password-reset-verify",
    ),
    path(
        "password-reset/confirm/",
        password_reset_confirm_view,
        name="api-password-reset-confirm",
    ),
    path("session/", SessionCheckView.as_view(), name="api-session-check"),
    # Permission endpoints
    path("scopes/", get_scopes, name="api-scopes"),
]
