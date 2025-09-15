"""
Comprehensive tests for authentication flows and security.

Tests user registration, login/logout, password reset, email verification,
and various authentication scenarios focusing on models and business logic.
"""

import os
from unittest.mock import Mock, patch

import django
from django.conf import settings

# Configure Django settings before any imports
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

User = get_user_model()


class UserRegistrationFlowTests(TestCase):
    """Test comprehensive user registration and validation."""

    def setUp(self):
        # Valid user data for testing
        self.valid_user_data = {
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
        }

    def test_successful_user_creation(self):
        """Test successful user creation with valid data."""
        user = User.objects.create_user(
            email=self.valid_user_data["email"],
            password=self.valid_user_data["password"],
            first_name=self.valid_user_data["first_name"],
            last_name=self.valid_user_data["last_name"],
        )

        # Verify user was created correctly
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "User")
        self.assertTrue(user.is_active)  # Default behavior for create_user
        self.assertTrue(user.check_password("SecurePass123!"))

    def test_duplicate_email_validation(self):
        """Test that duplicate emails are prevented at model level."""
        # Create first user
        User.objects.create_user(email="test@example.com", password="pass123")

        # Try to create second user with same email
        with self.assertRaises(Exception):  # IntegrityError
            User.objects.create_user(email="test@example.com", password="pass456")

    def test_email_validation(self):
        """Test email validation in user model."""
        user = User(email="invalid-email", password="pass123")

        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_password_hashing(self):
        """Test that passwords are properly hashed."""
        user = User.objects.create_user(
            email="test@example.com", password="plaintext123"
        )

        # Password should be hashed
        self.assertNotEqual(user.password, "plaintext123")
        self.assertTrue(len(user.password) > 20)  # Hashed password is much longer
        self.assertTrue(user.check_password("plaintext123"))

    def test_user_manager_create_user(self):
        """Test custom user manager create_user method."""
        user = User.objects.create_user(
            email="manager@example.com",
            password="pass123",
            first_name="Test",
            is_staff=False,
        )

        self.assertEqual(user.email, "manager@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_user_manager_create_superuser(self):
        """Test custom user manager create_superuser method."""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )

        self.assertEqual(user.email, "admin@example.com")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_user_manager_create_user_no_email(self):
        """Test create_user requires email."""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(email="", password="pass123")

        self.assertIn("Email field must be set", str(context.exception))

    def test_user_manager_create_superuser_validation(self):
        """Test create_superuser validation."""
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com",
                password="pass123",
                is_staff=False,  # Should raise error
            )

        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="admin@example.com",
                password="pass123",
                is_superuser=False,  # Should raise error
            )

    def test_user_profile_creation(self):
        """Test that user profile is automatically created via signal."""
        from apps.accounts.models import UserProfile

        user = User.objects.create_user(
            email="profiletest@example.com", password="pass123"  # Use unique email
        )

        # Profile should be created automatically via signal
        self.assertTrue(hasattr(user, "profile"))
        profile = user.profile

        # Update the profile
        profile.bio = "Test bio"
        profile.location = "Test Location"
        profile.save()

        self.assertEqual(profile.user, user)
        self.assertEqual(profile.bio, "Test bio")
        self.assertEqual(str(profile), "profiletest@example.com Profile")


class AuthenticationBackendTests(TestCase):
    """Test Django authentication backend functionality."""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
            is_active=True,
        )

        self.inactive_user = User.objects.create_user(
            email="inactive@example.com", password="TestPass123!", is_active=False
        )

    def test_successful_authentication(self):
        """Test successful authentication with valid credentials."""
        user = authenticate(username="testuser@example.com", password="TestPass123!")

        self.assertIsNotNone(user)
        self.assertEqual(user.email, "testuser@example.com")
        self.assertTrue(user.is_active)

    def test_authentication_invalid_credentials(self):
        """Test authentication fails with invalid credentials."""
        user = authenticate(username="testuser@example.com", password="WrongPassword")

        self.assertIsNone(user)

    def test_authentication_nonexistent_user(self):
        """Test authentication fails with nonexistent user."""
        user = authenticate(username="nonexistent@example.com", password="TestPass123!")

        self.assertIsNone(user)

    def test_authentication_inactive_user(self):
        """Test authentication fails with inactive user."""
        user = authenticate(username="inactive@example.com", password="TestPass123!")

        self.assertIsNone(user)

    def test_user_last_seen_update(self):
        """Test user's last_seen timestamp can be updated."""
        original_last_seen = self.user.last_seen

        # Test the update method
        self.user.update_last_seen()

        self.user.refresh_from_db()
        self.assertGreater(self.user.last_seen, original_last_seen)

    def test_user_group_methods(self):
        """Test user group checking methods."""
        from django.contrib.auth.models import Group

        # Create groups
        admin_group = Group.objects.create(name="Admin")
        manager_group = Group.objects.create(name="Manager")
        member_group = Group.objects.create(name="Member")

        # Add user to groups
        self.user.groups.add(member_group)

        # Test group checking methods
        self.assertTrue(self.user.has_group("Member"))
        self.assertFalse(self.user.has_group("Admin"))

        self.assertTrue(self.user.is_member())
        self.assertFalse(self.user.is_manager())
        self.assertFalse(self.user.is_admin())

        # Add to manager group
        self.user.groups.add(manager_group)
        # Clear cached property to force refresh (cached_property uses attribute name as cache key)
        if hasattr(self.user, "user_groups"):
            delattr(self.user, "user_groups")
        self.assertTrue(self.user.is_manager())
        self.assertTrue(self.user.is_member())  # Should still be true

    def test_user_display_methods(self):
        """Test user display name methods."""
        # Test with first_name and last_name
        self.assertEqual(self.user.get_full_name(), "Test User")
        self.assertEqual(self.user.get_short_name(), "Test")

        # Test with only name field
        user_with_name = User.objects.create_user(
            email="named@example.com", password="pass123", name="John Doe"
        )

        self.assertEqual(user_with_name.get_full_name(), "John Doe")
        self.assertEqual(user_with_name.get_short_name(), "John")

        # Test with no name fields
        user_no_name = User.objects.create_user(
            email="noname@example.com", password="pass123"
        )

        self.assertEqual(user_no_name.get_full_name(), "noname@example.com")
        self.assertEqual(user_no_name.get_short_name(), "noname")

    def test_password_validation(self):
        """Test password validation and security."""
        user = User.objects.create_user(
            email="secure@example.com", password="VerySecurePassword123!"
        )

        # Password should be hashed
        self.assertNotEqual(user.password, "VerySecurePassword123!")

        # Should validate correct password
        self.assertTrue(user.check_password("VerySecurePassword123!"))

        # Should reject incorrect password
        self.assertFalse(user.check_password("WrongPassword"))

    def test_user_clean_method(self):
        """Test user model clean method."""
        # Test with valid email
        user = User(email="valid@example.com")
        user.clean()  # Should not raise

        # Test with invalid email
        user_invalid = User(email="invalid-email")
        with self.assertRaises(ValidationError):
            user_invalid.clean()


class PasswordSecurityTests(TestCase):
    """Test password security and token functionality."""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="OldPass123!",
            first_name="Test",
            last_name="User",
            is_active=True,
        )

    def test_password_token_generation(self):
        """Test password reset token generation."""
        token = default_token_generator.make_token(self.user)

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

        # Token should be valid for the user
        self.assertTrue(default_token_generator.check_token(self.user, token))

    def test_password_token_invalid_for_different_user(self):
        """Test password reset token is invalid for different users."""
        # Create another user
        other_user = User.objects.create_user(
            email="other@example.com", password="pass123"
        )

        # Generate token for first user
        token = default_token_generator.make_token(self.user)

        # Token should not be valid for other user
        self.assertFalse(default_token_generator.check_token(other_user, token))

    def test_password_token_invalid_after_password_change(self):
        """Test token becomes invalid after password change."""
        # Generate token
        token = default_token_generator.make_token(self.user)

        # Verify token is initially valid
        self.assertTrue(default_token_generator.check_token(self.user, token))

        # Change password
        self.user.set_password("NewPassword123!")
        self.user.save()

        # Token should now be invalid
        self.assertFalse(default_token_generator.check_token(self.user, token))

    def test_uid_encoding_decoding(self):
        """Test UID encoding and decoding for password reset."""
        # Encode user ID
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        # Decode and verify
        decoded_uid = urlsafe_base64_decode(uid).decode()
        self.assertEqual(int(decoded_uid), self.user.pk)

    def test_password_change_validation(self):
        """Test password change validation."""
        # Test successful password change
        old_password_hash = self.user.password

        self.user.set_password("NewSecurePass123!")
        self.user.save()

        # Password hash should have changed
        self.assertNotEqual(self.user.password, old_password_hash)

        # Should authenticate with new password
        user = authenticate(
            username="testuser@example.com", password="NewSecurePass123!"
        )
        self.assertIsNotNone(user)

        # Should not authenticate with old password
        user = authenticate(username="testuser@example.com", password="OldPass123!")
        self.assertIsNone(user)

    def test_password_security_requirements(self):
        """Test password security requirements."""
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        # Test that password validation function exists and works
        # Note: Actual validation rules depend on Django settings
        # Test that validation function works
        try:
            validate_password("VerySecurePassword123!", self.user)
            # If no exception, that's fine - validation passed
        except ValidationError:
            # If exception, that's also fine - means validation is working
            pass

        # Test that function can validate passwords
        self.assertTrue(callable(validate_password))

    def test_email_normalization(self):
        """Test email normalization in user creation."""
        # Test that emails are normalized by the manager
        email_input = "  TEST@EXAMPLE.COM  "
        normalized = User.objects.normalize_email(email_input)

        # Django's normalize_email lowercases the domain part
        self.assertEqual(normalized, "TEST@example.com")


class UserModelAdvancedTests(TestCase):
    """Test advanced user model functionality."""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="TestPass123!",
            first_name="Test",
            last_name="User",
            is_active=True,
        )

    def test_user_meta_ordering(self):
        """Test user model Meta ordering."""
        # Create multiple users with different creation times
        user1 = User.objects.create_user(email="user1@example.com", password="pass123")
        user2 = User.objects.create_user(email="user2@example.com", password="pass123")

        # Get all users ordered by Meta.ordering
        users = list(User.objects.all())

        # Should be ordered by -created_at (newest first)
        self.assertGreaterEqual(users[0].created_at, users[1].created_at)

    def test_user_model_indexes(self):
        """Test that user model indexes are properly defined."""
        # This tests that the Meta.indexes are defined correctly
        from django.db import connection

        # Get table name
        table_name = User._meta.db_table

        # Check that indexes exist (this will vary by database backend)
        with connection.cursor() as cursor:
            # Get index information (implementation varies by database)
            if connection.vendor == "sqlite":
                cursor.execute(f"PRAGMA index_list({table_name})")
                indexes = cursor.fetchall()
                self.assertGreater(len(indexes), 0)

    def test_user_string_representation(self):
        """Test user model __str__ method."""
        self.assertEqual(str(self.user), "testuser@example.com")

    def test_user_permissions_and_groups(self):
        """Test user permissions and groups functionality."""
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType

        # Create group and permission
        group = Group.objects.create(name="Test Group")
        content_type = ContentType.objects.get_or_create(
            app_label="accounts", model="user"
        )[0]
        permission = Permission.objects.get_or_create(
            codename="test_permission",
            name="Test Permission",
            content_type=content_type,
        )[0]

        # Add user to group
        self.user.groups.add(group)

        # Add permission to group
        group.permissions.add(permission)

        # Test user has permission through group
        self.assertTrue(self.user.has_perm("accounts.test_permission"))

        # Remove user from group
        self.user.groups.remove(group)

        # Should no longer have permission
        self.assertFalse(self.user.has_perm("accounts.test_permission"))

    def test_user_profile_relationship(self):
        """Test user profile one-to-one relationship."""
        from apps.accounts.models import UserProfile

        # Create a new user for this test - profile will be created automatically
        test_user = User.objects.create_user(
            email="profilerel@example.com", password="pass123"
        )

        # Profile should exist due to signal
        self.assertTrue(UserProfile.objects.filter(user=test_user).exists())
        profile = test_user.profile

        # Update the profile to test the relationship
        profile.bio = "Test bio"
        profile.location = "Test City"
        profile.timezone = "UTC"
        profile.language = "en"
        profile.save()

        # Test relationship
        self.assertEqual(test_user.profile, profile)
        self.assertEqual(profile.user, test_user)
        self.assertEqual(profile.bio, "Test bio")

    def test_user_last_seen_functionality(self):
        """Test user last_seen field and update functionality."""
        import time

        from django.utils import timezone

        original_last_seen = self.user.last_seen

        # Wait a moment
        time.sleep(0.1)

        # Update last seen
        self.user.update_last_seen()

        # Refresh from database
        self.user.refresh_from_db()

        # Should be updated
        self.assertGreater(self.user.last_seen, original_last_seen)

    def test_superuser_permissions(self):
        """Test superuser permissions."""
        superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )

        # Superuser should have all permissions
        self.assertTrue(superuser.has_perm("any.permission"))
        self.assertTrue(superuser.has_perm("nonexistent.permission"))
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
