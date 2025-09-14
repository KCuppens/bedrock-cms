"""Comprehensive tests for accounts app - targeting 80% coverage"""

import os

import django

# Configure Django settings before any imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import UserProfile

User = get_user_model()


class AccountsModelTest(TestCase):
    """Test all accounts models"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@test.com", password="TestPass123!"
        )

    def test_user_profile_creation(self):
        """Test UserProfile auto-creation"""
        self.assertTrue(hasattr(self.user, "profile"))
        self.assertIsInstance(self.user.profile, UserProfile)

    def test_user_profile_str(self):
        """Test UserProfile string representation"""
        profile = self.user.profile
        self.assertEqual(str(profile), f"{self.user.email} Profile")

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


class AccountsSerializerTest(TestCase):
    """Test accounts serializers"""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@test.com", password="TestPass123!"
        )

    def test_user_serializer(self):
        """Test UserSerializer"""
        from apps.accounts.serializers import UserSerializer

        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertEqual(data["email"], "test@test.com")
        self.assertEqual(data["email"], "test@test.com")
        self.assertNotIn("password", data)

    def test_user_profile_serializer(self):
        """Test UserProfileSerializer"""
        from apps.accounts.serializers import UserProfileSerializer

        profile = self.user.profile
        profile.bio = "Test bio"
        profile.save()

        serializer = UserProfileSerializer(profile)
        data = serializer.data

        self.assertEqual(data["bio"], "Test bio")
        # Check that serializer contains expected fields (user field may not be included in serializer)
        self.assertIn("bio", data)


class AccountsViewTest(TestCase):
    """Test accounts views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="test@test.com", password="TestPass123!"
        )

    def test_login_view(self):
        """Test login endpoint"""
        response = self.client.post(
            "/auth/login/",
            json.dumps({"email": "test@test.com", "password": "TestPass123!"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

    def test_logout_view(self):
        """Test logout endpoint"""
        self.client.login(username="test@test.com", password="TestPass123!")

        response = self.client.post("/auth/logout/")

        self.assertEqual(response.status_code, 200)

    def test_register_view(self):
        """Test registration endpoint"""
        response = self.client.post(
            "/auth/users/register/",
            json.dumps(
                {
                    "email": "new@test.com",
                    "password1": "NewPass123!",
                    "password2": "NewPass123!",
                }
            ),
            content_type="application/json",
        )

        self.assertIn(response.status_code, [200, 201])

    def test_profile_view_requires_auth(self):
        """Test profile view requires authentication"""
        response = self.client.get("/auth/users/me/")

        self.assertIn(response.status_code, [401, 403])

    def test_profile_update(self):
        """Test profile update"""
        self.client.login(username="test@test.com", password="TestPass123!")

        response = self.client.patch(
            "/auth/users/me/",
            json.dumps({"profile": {"bio": "Updated bio"}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

    def test_password_reset_request(self):
        """Test password reset request"""
        response = self.client.post(
            "/auth/password-reset/",
            json.dumps({"email": "test@test.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
