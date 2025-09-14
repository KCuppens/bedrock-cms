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


class AccountsSerializerTest(TestCase):
    """Test accounts serializers"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="TestPass123!"
        )

    def test_user_serializer(self):
        """Test UserSerializer"""
        from apps.accounts.serializers import UserSerializer

        serializer = UserSerializer(self.user)
        data = serializer.data

        self.assertEqual(data["username"], "testuser")
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
        self.assertIn("user", data)


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
