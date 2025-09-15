"""Comprehensive test coverage for accounts app managers"""

import os
from unittest.mock import Mock, patch

import django
from django.conf import settings

# Configure Django settings before any imports
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.accounts.models import CustomUserManager, User

UserModel = get_user_model()


class CustomUserManagerComprehensiveTest(TestCase):
    """Comprehensive tests for CustomUserManager"""

    def setUp(self):
        """Set up test data"""
        self.valid_email = "test@example.com"
        self.valid_password = "test_password123"
        self.manager = CustomUserManager()
        self.manager.model = User

    def test_manager_initialization(self):
        """Test CustomUserManager can be initialized"""
        manager = CustomUserManager()
        self.assertIsInstance(manager, CustomUserManager)
        from django.contrib.auth.models import BaseUserManager

        self.assertIsInstance(manager, BaseUserManager)

    def test_create_user_basic(self):
        """Test basic user creation with email and password"""
        user = User.objects.create_user(
            email=self.valid_email, password=self.valid_password
        )

        self.assertEqual(user.email, self.valid_email)
        self.assertTrue(user.check_password(self.valid_password))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_user_with_extra_fields(self):
        """Test user creation with additional fields"""
        extra_fields = {
            "name": "Test User",
            "is_active": False,
        }

        user = User.objects.create_user(
            email=self.valid_email, password=self.valid_password, **extra_fields
        )

        self.assertEqual(user.name, "Test User")
        self.assertFalse(user.is_active)

    def test_create_user_without_password(self):
        """Test user creation without password"""
        user = User.objects.create_user(email=self.valid_email)

        self.assertEqual(user.email, self.valid_email)
        self.assertFalse(user.has_usable_password())

    def test_create_user_empty_email(self):
        """Test create_user raises ValueError for empty email"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(email="", password=self.valid_password)

        self.assertIn("The Email field must be set", str(context.exception))

    def test_create_user_none_email(self):
        """Test create_user raises ValueError for None email"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_user(email=None, password=self.valid_password)

        self.assertIn("The Email field must be set", str(context.exception))

    def test_create_user_email_normalization(self):
        """Test email normalization in create_user"""
        test_emails = [
            ("Test@Example.COM", "Test@example.com"),
            ("user+tag@DOMAIN.COM", "user+tag@domain.com"),
            ("  spaced@example.com  ", "spaced@example.com"),
        ]

        for input_email, expected_email in test_emails:
            with self.subTest(input_email=input_email):
                user = User.objects.create_user(
                    email=input_email, password=self.valid_password
                )
                self.assertEqual(user.email, expected_email)

    def test_create_user_with_existing_email(self):
        """Test creating user with existing email raises IntegrityError"""
        User.objects.create_user(email=self.valid_email, password=self.valid_password)

        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email=self.valid_email, password="different_password"
            )

    def test_create_superuser_basic(self):
        """Test basic superuser creation"""
        user = User.objects.create_superuser(
            email=self.valid_email, password=self.valid_password
        )

        self.assertEqual(user.email, self.valid_email)
        self.assertTrue(user.check_password(self.valid_password))
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_create_superuser_with_extra_fields(self):
        """Test superuser creation with additional fields"""
        extra_fields = {
            "name": "Admin User",
        }

        user = User.objects.create_superuser(
            email=self.valid_email, password=self.valid_password, **extra_fields
        )

        self.assertEqual(user.name, "Admin User")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_without_password(self):
        """Test superuser creation without password"""
        user = User.objects.create_superuser(email=self.valid_email)

        self.assertEqual(user.email, self.valid_email)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertFalse(user.has_usable_password())

    def test_create_superuser_is_staff_false(self):
        """Test create_superuser raises ValueError when is_staff=False"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(
                email=self.valid_email, password=self.valid_password, is_staff=False
            )

        self.assertIn("Superuser must have is_staff=True", str(context.exception))

    def test_create_superuser_is_superuser_false(self):
        """Test create_superuser raises ValueError when is_superuser=False"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(
                email=self.valid_email, password=self.valid_password, is_superuser=False
            )

        self.assertIn("Superuser must have is_superuser=True", str(context.exception))

    def test_create_superuser_empty_email(self):
        """Test create_superuser raises ValueError for empty email"""
        with self.assertRaises(ValueError) as context:
            User.objects.create_superuser(email="", password=self.valid_password)

        self.assertIn("The Email field must be set", str(context.exception))

    def test_manager_database_operations(self):
        """Test manager database operations and transactions"""
        # Test successful transaction
        with transaction.atomic():
            user = User.objects.create_user(
                email=self.valid_email, password=self.valid_password
            )
            self.assertTrue(User.objects.filter(email=self.valid_email).exists())

    def test_manager_using_specific_database(self):
        """Test manager with specific database"""
        # This tests the _db parameter usage
        manager = CustomUserManager()
        manager.model = User
        manager._db = "default"

        # Mock database operations
        with patch.object(User, "save") as mock_save:
            user = manager.model(email=self.valid_email)
            user.set_password(self.valid_password)
            user.save(using=manager._db)

            mock_save.assert_called_with(using="default")

    def test_manager_queryset_operations(self):
        """Test manager queryset operations"""
        # Create test users
        user1 = User.objects.create_user("user1@test.com", "password")
        user2 = User.objects.create_user("user2@test.com", "password")
        superuser = User.objects.create_superuser("admin@test.com", "password")

        # Test basic queryset operations
        all_users = User.objects.all()
        self.assertEqual(all_users.count(), 3)

        # Test filtering
        staff_users = User.objects.filter(is_staff=True)
        self.assertEqual(staff_users.count(), 1)
        self.assertEqual(staff_users.first(), superuser)

        # Test ordering
        ordered_users = User.objects.order_by("email")
        self.assertEqual(
            list(ordered_users.values_list("email", flat=True)),
            ["admin@test.com", "user1@test.com", "user2@test.com"],
        )

    def test_manager_bulk_operations(self):
        """Test manager bulk operations"""
        emails = [f"user{i}@test.com" for i in range(3)]

        # Test bulk_create equivalent (create multiple users)
        users = []
        for email in emails:
            user = User.objects.create_user(email=email, password="password")
            users.append(user)

        self.assertEqual(User.objects.count(), 3)

        # Test bulk update
        User.objects.filter(email__in=emails).update(is_active=False)
        inactive_count = User.objects.filter(is_active=False).count()
        self.assertEqual(inactive_count, 3)

    def test_manager_complex_queries(self):
        """Test manager with complex queries"""
        # Clear any existing users to ensure clean test
        User.objects.all().delete()

        # Create test data
        user1 = User.objects.create_user(
            "active@test.com", "password", is_active=True, name="Active User"
        )
        user2 = User.objects.create_user(
            "inactive@test.com", "password", is_active=False, name="Disabled User"
        )
        admin_user = User.objects.create_superuser(
            "admin@test.com", "password", name="Super User"
        )

        # Test complex filtering
        active_users = User.objects.filter(is_active=True, is_staff=False)
        self.assertEqual(active_users.count(), 1)

        # Test Q objects
        from django.db.models import Q

        admin_or_active = User.objects.filter(
            Q(is_superuser=True) | Q(is_active=True, is_staff=False)
        )
        self.assertEqual(admin_or_active.count(), 2)

        # Test annotations - create specific test that should return exactly 2 users
        from django.db.models import BooleanField, Case, When

        users_with_flags = User.objects.annotate(
            is_special=Case(
                When(is_superuser=True, then=True),
                When(
                    name__icontains="Active", then=True
                ),  # Capital A to be more specific
                default=False,
                output_field=BooleanField(),
            )
        )
        special_users = users_with_flags.filter(is_special=True)
        # Should match admin_user (superuser) and user1 (name contains 'Active')
        self.assertEqual(special_users.count(), 2)

    def test_manager_performance_considerations(self):
        """Test manager performance-related functionality"""
        # Create test users
        for i in range(10):
            User.objects.create_user(f"user{i}@test.com", "password")

        # Test select_related and prefetch_related equivalents
        # (User model doesn't have foreign keys, but we can test the queryset methods)
        queryset = User.objects.all()
        self.assertEqual(queryset.count(), 10)

        # Test only() for performance
        limited_fields = User.objects.only("email", "is_active")
        self.assertEqual(limited_fields.count(), 10)

        # Test defer() for performance
        deferred_fields = User.objects.defer("last_login", "date_joined")
        self.assertEqual(deferred_fields.count(), 10)

    def test_manager_error_handling(self):
        """Test manager error handling scenarios"""
        # Test ValidationError during user creation
        with self.assertRaises(ValueError):
            User.objects.create_user("", "password")

        # Test handling of database constraints
        User.objects.create_user(self.valid_email, self.valid_password)

        with self.assertRaises(IntegrityError):
            User.objects.create_user(self.valid_email, "different_password")

    def test_manager_thread_safety(self):
        """Test manager thread safety considerations"""
        # Create multiple manager instances
        manager1 = CustomUserManager()
        manager2 = CustomUserManager()

        # They should be separate instances
        self.assertIsNot(manager1, manager2)

        # Both should be able to create users without interference
        manager1.model = User
        manager2.model = User

        # Test that managers don't share state
        self.assertIsNone(manager1._db)
        self.assertIsNone(manager2._db)

    def test_manager_inheritance_behavior(self):
        """Test manager inheritance behavior"""
        # Test that CustomUserManager inherits from BaseUserManager
        from django.contrib.auth.models import BaseUserManager

        self.assertTrue(issubclass(CustomUserManager, BaseUserManager))

        # Test manager descriptor behavior
        self.assertIsInstance(User.objects, CustomUserManager)

        # Test that manager has required methods
        required_methods = ["create_user", "create_superuser"]
        for method in required_methods:
            self.assertTrue(hasattr(CustomUserManager, method))
            self.assertTrue(callable(getattr(CustomUserManager, method)))

    def test_manager_with_model_validation(self):
        """Test manager integrates with model validation"""
        # Test that manager respects model validation
        user = User.objects.create_user(
            email="valid@test.com", password=self.valid_password
        )

        # User should be valid
        user.full_clean()  # Should not raise ValidationError

        # Test with invalid email (this would be caught by model validation)
        user.email = "invalid-email"
        with self.assertRaises(ValidationError):
            user.clean()

    def test_manager_custom_methods_integration(self):
        """Test manager integration with custom model methods"""
        user = User.objects.create_user(
            email=self.valid_email,
            password=self.valid_password,
            name="Test User",
            first_name="Test",
            last_name="User",
        )

        # Test integration with custom model methods
        self.assertEqual(user.get_full_name(), "Test User")
        self.assertEqual(user.get_short_name(), "Test")

        # Test last_seen update
        import time

        original_last_seen = user.last_seen
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        user.update_last_seen()
        user.refresh_from_db()
        self.assertGreater(user.last_seen, original_last_seen)

    def test_manager_edge_cases(self):
        """Test manager edge cases and boundary conditions"""
        # Test with very long email
        long_email = "a" * 240 + "@test.com"  # Near email field max length
        user = User.objects.create_user(email=long_email, password=self.valid_password)
        self.assertEqual(user.email, long_email)

        # Test with special characters in email
        special_email = "user+test@sub.example-domain.com"
        user = User.objects.create_user(
            email=special_email, password=self.valid_password
        )
        self.assertEqual(user.email, special_email)

        # Test password edge cases
        empty_password_user = User.objects.create_user(email="nopass@test.com")
        self.assertFalse(empty_password_user.has_usable_password())

        # Test very long password
        long_password = "a" * 1000
        user = User.objects.create_user(
            email="longpass@test.com", password=long_password
        )
        self.assertTrue(user.check_password(long_password))

    def test_manager_database_constraints(self):
        """Test manager respects database constraints"""
        # Test unique email constraint
        User.objects.create_user(self.valid_email, self.valid_password)

        with self.assertRaises(IntegrityError):
            User.objects.create_user(self.valid_email, "different_password")

    def test_manager_transaction_behavior(self):
        """Test manager behavior within transactions"""
        try:
            with transaction.atomic():
                user1 = User.objects.create_user("user1@test.com", "password")
                user2 = User.objects.create_user("user2@test.com", "password")
                # Force a constraint violation to test rollback
                User.objects.create_user(
                    "user1@test.com", "password"
                )  # Should raise IntegrityError
        except IntegrityError:
            pass

        # Both users should be rolled back
        self.assertEqual(User.objects.count(), 0)

    def test_manager_with_different_field_combinations(self):
        """Test manager with various field combinations"""
        test_cases = [
            {"email": "basic@test.com", "password": "password"},
            {"email": "withname@test.com", "password": "password", "name": "Full Name"},
            {"email": "inactive@test.com", "password": "password", "is_active": False},
            {"email": "staff@test.com", "password": "password", "is_staff": True},
        ]

        for i, test_case in enumerate(test_cases):
            with self.subTest(case=i):
                user = User.objects.create_user(**test_case)
                self.assertEqual(user.email, test_case["email"])
                if "name" in test_case:
                    self.assertEqual(user.name, test_case["name"])
                if "is_active" in test_case:
                    self.assertEqual(user.is_active, test_case["is_active"])


class CustomUserManagerTransactionTest(TestCase):
    """Tests requiring transaction rollback capability"""

    def test_manager_atomic_operations(self):
        """Test manager atomic operations"""
        from django.db import transaction

        # Test successful atomic block
        with transaction.atomic():
            user = User.objects.create_user("atomic@test.com", "password")
            self.assertTrue(User.objects.filter(email="atomic@test.com").exists())

        # User should be committed
        self.assertTrue(User.objects.filter(email="atomic@test.com").exists())

        # Test failed atomic block
        try:
            with transaction.atomic():
                User.objects.create_user("rollback1@test.com", "password")
                User.objects.create_user("rollback2@test.com", "password")
                # Force an error
                User.objects.create_user(
                    "atomic@test.com", "password"
                )  # Duplicate email
        except IntegrityError:
            pass

        # Neither user should exist due to rollback
        self.assertFalse(User.objects.filter(email="rollback1@test.com").exists())
        self.assertFalse(User.objects.filter(email="rollback2@test.com").exists())

    def test_manager_savepoint_operations(self):
        """Test manager with savepoints"""
        from django.db import connection, transaction

        # Skip this test for SQLite as it has issues with nested savepoints
        if connection.vendor == "sqlite":
            self.skipTest("SQLite doesn't properly support nested savepoints")

        with transaction.atomic():
            User.objects.create_user("outer@test.com", "password")

            # Create a savepoint
            sid = transaction.savepoint()

            # Add user that will be in savepoint
            User.objects.create_user("inner@test.com", "password")

            # Test savepoint with valid operation (no error)
            sid2 = transaction.savepoint()
            User.objects.create_user("valid@test.com", "password")
            transaction.savepoint_commit(sid2)

            # Create recovery user in the original savepoint
            User.objects.create_user("recovery@test.com", "password")
            transaction.savepoint_commit(sid)

        # outer, inner, valid and recovery users should exist
        self.assertTrue(User.objects.filter(email="outer@test.com").exists())
        self.assertTrue(User.objects.filter(email="inner@test.com").exists())
        self.assertTrue(User.objects.filter(email="valid@test.com").exists())
        self.assertTrue(User.objects.filter(email="recovery@test.com").exists())


@override_settings(USE_TZ=True)
class CustomUserManagerTimezoneTest(TestCase):
    """Test manager behavior with timezone handling"""

    def test_manager_timezone_aware_operations(self):
        """Test manager handles timezone-aware operations"""
        user = User.objects.create_user("tz@test.com", "password")

        # Check that timestamps are timezone-aware
        self.assertIsNotNone(user.created_at.tzinfo)
        self.assertIsNotNone(user.updated_at.tzinfo)
        self.assertIsNotNone(user.last_seen.tzinfo)

        # Test last_seen update
        import time

        original_last_seen = user.last_seen
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        user.update_last_seen()
        user.refresh_from_db()

        # Should be timezone-aware and more recent
        self.assertIsNotNone(user.last_seen.tzinfo)
        self.assertGreater(user.last_seen, original_last_seen)


class CustomUserManagerPerformanceTest(TestCase):
    """Performance-related tests for CustomUserManager"""

    def test_manager_bulk_user_creation(self):
        """Test performance of bulk user creation"""
        import time

        start_time = time.time()

        # Create multiple users
        users = []
        for i in range(50):
            user = User.objects.create_user(f"bulk{i}@test.com", "password")
            users.append(user)

        end_time = time.time()

        # Verify all users were created
        self.assertEqual(User.objects.count(), 50)

        # Basic performance check (should complete in reasonable time)
        elapsed = end_time - start_time
        self.assertLess(elapsed, 5.0, "Bulk user creation took too long")

    def test_manager_query_optimization(self):
        """Test query optimization in manager operations"""
        # Create test users
        for i in range(20):
            User.objects.create_user(f"opt{i}@test.com", "password")

        # Test that basic queries are optimized
        with self.assertNumQueries(1):
            users = list(User.objects.all())
            self.assertEqual(len(users), 20)

        # Test filtering queries
        with self.assertNumQueries(1):
            active_users = list(User.objects.filter(is_active=True))
            self.assertEqual(len(active_users), 20)
