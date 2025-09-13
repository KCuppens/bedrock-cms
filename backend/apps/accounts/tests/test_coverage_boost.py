"""Comprehensive tests for accounts app - targeting 80% coverage"""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import (
    APIKey,
    LoginAttempt,
    PasswordResetToken,
    Role,
    Team,
    TeamMembership,
    UserProfile,
)
from apps.accounts.permissions import IsOwnerOrReadOnly, IsTeamMember
from apps.accounts.serializers import (
    TeamSerializer,
    UserProfileSerializer,
    UserSerializer,
)
from apps.accounts.utils import (
    check_rate_limit,
    generate_api_key,
    send_verification_email,
    validate_password_strength,
)

User = get_user_model()


class AccountsModelTest(TestCase):
    """Test all accounts models"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="TestPass123!"
        )

    def test_user_profile_creation(self):
        """Test UserProfile auto-creation"""
        self.assertTrue(hasattr(self.user, "profile"))
        self.assertIsInstance(self.user.profile, UserProfile)

    def test_user_profile_str(self):
        """Test UserProfile string representation"""
        profile = self.user.profile
        self.assertEqual(str(profile), f"Profile for {self.user.username}")

    def test_user_profile_fields(self):
        """Test UserProfile fields"""
        profile = self.user.profile
        profile.bio = "Test bio"
        profile.avatar = "avatar.jpg"
        profile.phone = "+1234567890"
        profile.timezone = "UTC"
        profile.language = "en"
        profile.save()

        self.assertEqual(profile.bio, "Test bio")
        self.assertEqual(profile.phone, "+1234567890")

    def test_team_model(self):
        """Test Team model"""
        team = Team.objects.create(name="Test Team", slug="test-team", owner=self.user)

        self.assertEqual(str(team), "Test Team")
        self.assertEqual(team.owner, self.user)

    def test_team_membership(self):
        """Test TeamMembership model"""
        team = Team.objects.create(name="Test Team", slug="test-team", owner=self.user)
        user2 = User.objects.create_user("user2", "user2@test.com", "pass")

        membership = TeamMembership.objects.create(team=team, user=user2, role="member")

        self.assertEqual(str(membership), f"{user2.username} - {team.name}")
        self.assertEqual(membership.role, "member")

    def test_team_add_member(self):
        """Test adding members to team"""
        team = Team.objects.create(name="Test Team", slug="test-team", owner=self.user)
        user2 = User.objects.create_user("user2", "user2@test.com", "pass")

        team.add_member(user2, role="admin")

        self.assertTrue(team.members.filter(id=user2.id).exists())

    def test_team_remove_member(self):
        """Test removing members from team"""
        team = Team.objects.create(name="Test Team", slug="test-team", owner=self.user)
        user2 = User.objects.create_user("user2", "user2@test.com", "pass")

        team.add_member(user2)
        team.remove_member(user2)

        self.assertFalse(team.members.filter(id=user2.id).exists())

    def test_role_model(self):
        """Test Role model"""
        role = Role.objects.create(
            name="Editor", slug="editor", description="Can edit content"
        )

        self.assertEqual(str(role), "Editor")

    def test_role_permissions(self):
        """Test Role permissions"""
        role = Role.objects.create(name="Editor", slug="editor")
        perm = Permission.objects.first()
        role.permissions.add(perm)

        self.assertIn(perm, role.permissions.all())

    def test_api_key_model(self):
        """Test APIKey model"""
        api_key = APIKey.objects.create(
            user=self.user, name="Test Key", key="test-key-123"
        )

        self.assertEqual(str(api_key), f"API Key for {self.user.username}: Test Key")
        self.assertTrue(api_key.is_active)

    def test_api_key_revoke(self):
        """Test revoking API key"""
        api_key = APIKey.objects.create(
            user=self.user, name="Test Key", key="test-key-123"
        )

        api_key.revoke()

        self.assertFalse(api_key.is_active)
        self.assertIsNotNone(api_key.revoked_at)

    def test_login_attempt_model(self):
        """Test LoginAttempt model"""
        attempt = LoginAttempt.objects.create(
            username="testuser", ip_address="192.168.1.1", success=False
        )

        self.assertEqual(str(attempt), "Login attempt for testuser from 192.168.1.1")
        self.assertFalse(attempt.success)

    def test_password_reset_token(self):
        """Test PasswordResetToken model"""
        token = PasswordResetToken.objects.create(
            user=self.user, token="reset-token-123"
        )

        self.assertEqual(str(token), f"Reset token for {self.user.email}")
        self.assertFalse(token.is_used)

    def test_password_reset_token_use(self):
        """Test using password reset token"""
        token = PasswordResetToken.objects.create(
            user=self.user, token="reset-token-123"
        )

        token.use()

        self.assertTrue(token.is_used)
        self.assertIsNotNone(token.used_at)


class AccountsSerializerTest(TestCase):
    """Test accounts serializers"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="TestPass123!"
        )

    def test_user_serializer(self):
        """Test UserSerializer"""
        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["email"], "test@test.com")
        self.assertNotIn("password", data)

    def test_user_profile_serializer(self):
        """Test UserProfileSerializer"""
        profile = self.user.profile
        profile.bio = "Test bio"
        profile.save()

        serializer = UserProfileSerializer(profile)
        data = serializer.data

        self.assertEqual(data["bio"], "Test bio")
        self.assertIn("user", data)

    def test_team_serializer(self):
        """Test TeamSerializer"""
        team = Team.objects.create(name="Test Team", slug="test-team", owner=self.user)

        serializer = TeamSerializer(team)
        data = serializer.data

        self.assertEqual(data["name"], "Test Team")
        self.assertEqual(data["slug"], "test-team")


class AccountsPermissionTest(TestCase):
    """Test custom permissions"""

    def setUp(self):
        self.user1 = User.objects.create_user("user1", "user1@test.com", "pass")
        self.user2 = User.objects.create_user("user2", "user2@test.com", "pass")
        self.team = Team.objects.create(
            name="Test Team", slug="test-team", owner=self.user1
        )

    def test_is_owner_permission(self):
        """Test IsOwnerOrReadOnly permission"""
        permission = IsOwnerOrReadOnly()

        # Mock request and view
        request = MagicMock()
        request.user = self.user1
        request.method = "GET"

        # Read permission should be granted
        self.assertTrue(permission.has_permission(request, None))

        # Write permission for owner
        request.method = "PUT"
        obj = MagicMock()
        obj.owner = self.user1

        self.assertTrue(permission.has_object_permission(request, None, obj))

        # Write permission denied for non-owner
        obj.owner = self.user2
        self.assertFalse(permission.has_object_permission(request, None, obj))

    def test_is_team_member_permission(self):
        """Test IsTeamMember permission"""
        permission = IsTeamMember()

        # Add user to team
        self.team.add_member(self.user2)

        # Mock request
        request = MagicMock()
        request.user = self.user2

        self.assertTrue(permission.has_object_permission(request, None, self.team))

        # Non-member
        user3 = User.objects.create_user("user3", "user3@test.com", "pass")
        request.user = user3

        self.assertFalse(permission.has_object_permission(request, None, self.team))


class AccountsUtilsTest(TestCase):
    """Test utility functions"""

    def test_generate_api_key(self):
        """Test API key generation"""
        key = generate_api_key()

        self.assertIsNotNone(key)
        self.assertTrue(len(key) > 20)

    def test_validate_password_strength(self):
        """Test password strength validation"""
        # Weak password
        self.assertFalse(validate_password_strength("weak"))

        # Strong password
        self.assertTrue(validate_password_strength("Strong!Pass123"))

    @patch("apps.accounts.utils.send_mail")
    def test_send_verification_email(self, mock_send_mail):
        """Test sending verification email"""
        user = User.objects.create_user("test", "test@test.com", "pass")

        send_verification_email(user)

        mock_send_mail.assert_called_once()

    def test_check_rate_limit(self):
        """Test rate limiting check"""
        # First attempt should pass
        self.assertTrue(check_rate_limit("test_key", limit=5, window=60))

        # Multiple attempts
        for _ in range(4):
            check_rate_limit("test_key", limit=5, window=60)

        # Should fail after limit
        self.assertFalse(check_rate_limit("test_key", limit=5, window=60))


class AccountsViewTest(TestCase):
    """Test accounts views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="TestPass123!"
        )

    def test_login_view(self):
        """Test login endpoint"""
        response = self.client.post(
            "/api/auth/login/", {"username": "testuser", "password": "TestPass123!"}
        )

        self.assertEqual(response.status_code, 200)

    def test_logout_view(self):
        """Test logout endpoint"""
        self.client.login(username="testuser", password="TestPass123!")

        response = self.client.post("/api/auth/logout/")

        self.assertEqual(response.status_code, 200)

    def test_register_view(self):
        """Test registration endpoint"""
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "newuser",
                "email": "new@test.com",
                "password": "NewPass123!",
                "password2": "NewPass123!",
            },
        )

        self.assertIn(response.status_code, [200, 201])

    def test_profile_view_requires_auth(self):
        """Test profile view requires authentication"""
        response = self.client.get("/api/auth/profile/")

        self.assertIn(response.status_code, [401, 403])

    def test_profile_update(self):
        """Test profile update"""
        self.client.login(username="testuser", password="TestPass123!")

        response = self.client.patch("/api/auth/profile/", {"bio": "Updated bio"})

        self.assertEqual(response.status_code, 200)

    def test_password_reset_request(self):
        """Test password reset request"""
        response = self.client.post(
            "/api/auth/password-reset/", {"email": "test@test.com"}
        )

        self.assertEqual(response.status_code, 200)

    def test_team_create(self):
        """Test team creation"""
        self.client.login(username="testuser", password="TestPass123!")

        response = self.client.post(
            "/api/teams/", {"name": "New Team", "slug": "new-team"}
        )

        self.assertIn(response.status_code, [200, 201])

    def test_team_list(self):
        """Test team listing"""
        self.client.login(username="testuser", password="TestPass123!")

        Team.objects.create(name="Team 1", slug="team-1", owner=self.user)

        response = self.client.get("/api/teams/")

        self.assertEqual(response.status_code, 200)
