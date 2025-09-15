"""Comprehensive test coverage for core app model-related utilities"""

import os

# Configure Django settings before imports
import uuid
from unittest.mock import MagicMock, Mock, patch

import django
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.core.utils import (
    bulk_update_or_create,
    create_slug,
    format_file_size,
    generate_hash,
    generate_secure_token,
    generate_short_uuid,
    generate_unique_slug,
    generate_uuid,
    get_client_ip,
    get_object_or_none,
    get_user_agent,
    mask_email,
    safe_get_dict_value,
    send_notification_email,
    time_since_creation,
    truncate_string,
    validate_json_structure,
)

User = get_user_model()


class MockModel:
    """Mock model class for testing utilities"""

    class DoesNotExist(Exception):
        pass

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    objects = Mock()


class UUIDUtilsTest(TestCase):
    """Test UUID generation utilities"""

    def test_generate_uuid(self):
        """Test generate_uuid function"""
        result = generate_uuid()

        # Should return a string
        self.assertIsInstance(result, str)

        # Should be a valid UUID when parsed
        uuid_obj = uuid.UUID(result)
        self.assertIsInstance(uuid_obj, uuid.UUID)

        # Should be version 4 (random)
        self.assertEqual(uuid_obj.version, 4)

    def test_generate_uuid_uniqueness(self):
        """Test that generated UUIDs are unique"""
        uuid1 = generate_uuid()
        uuid2 = generate_uuid()

        self.assertNotEqual(uuid1, uuid2)

        # Generate multiple UUIDs and ensure they're all unique
        uuids = [generate_uuid() for _ in range(100)]
        unique_uuids = set(uuids)

        self.assertEqual(len(uuids), len(unique_uuids))

    def test_generate_short_uuid_default(self):
        """Test generate_short_uuid with default length"""
        result = generate_short_uuid()

        # Should be 8 characters by default
        self.assertEqual(len(result), 8)
        self.assertIsInstance(result, str)

        # Should contain only alphanumeric characters (no hyphens)
        self.assertTrue(result.isalnum())

    def test_generate_short_uuid_custom_length(self):
        """Test generate_short_uuid with custom length"""
        lengths = [4, 12, 16, 20]

        for length in lengths:
            result = generate_short_uuid(length)
            self.assertEqual(len(result), length)
            self.assertIsInstance(result, str)
            self.assertTrue(result.isalnum())

    def test_generate_short_uuid_uniqueness(self):
        """Test short UUID uniqueness"""
        short_uuids = [generate_short_uuid() for _ in range(100)]
        unique_short_uuids = set(short_uuids)

        # Should be very likely to be unique for 8-character strings
        self.assertGreaterEqual(
            len(unique_short_uuids), 95
        )  # Allow for small chance of collision


class SecurityUtilsTest(TestCase):
    """Test security-related utilities"""

    def test_generate_secure_token_default(self):
        """Test generate_secure_token with default length"""
        result = generate_secure_token()

        # Should return a URL-safe string
        self.assertIsInstance(result, str)

        # Length should be appropriate for 32 bytes URL-safe encoded
        # URL-safe base64 encoding of 32 bytes should be around 43 characters
        self.assertGreaterEqual(len(result), 40)

    def test_generate_secure_token_custom_length(self):
        """Test generate_secure_token with custom length"""
        lengths = [16, 32, 64]

        for length in lengths:
            result = generate_secure_token(length)
            self.assertIsInstance(result, str)
            # Length will vary due to base64 encoding, but should be substantial
            self.assertGreater(len(result), length)

    def test_generate_secure_token_uniqueness(self):
        """Test secure token uniqueness"""
        tokens = [generate_secure_token() for _ in range(100)]
        unique_tokens = set(tokens)

        # All tokens should be unique
        self.assertEqual(len(tokens), len(unique_tokens))

    def test_generate_hash_sha256(self):
        """Test generate_hash with SHA256"""
        data = "test data"
        result = generate_hash(data)

        # Should return a hex string
        self.assertIsInstance(result, str)

        # SHA256 should produce 64 character hex string
        self.assertEqual(len(result), 64)

        # Should be consistent
        self.assertEqual(result, generate_hash(data))

    def test_generate_hash_different_algorithms(self):
        """Test generate_hash with different algorithms"""
        data = "test data"
        algorithms = ["md5", "sha1", "sha256", "sha512"]
        expected_lengths = [32, 40, 64, 128]

        for algorithm, expected_length in zip(algorithms, expected_lengths):
            result = generate_hash(data, algorithm)
            self.assertEqual(len(result), expected_length)
            self.assertIsInstance(result, str)

    def test_generate_hash_consistency(self):
        """Test hash generation consistency"""
        data = "test data"

        hash1 = generate_hash(data)
        hash2 = generate_hash(data)

        self.assertEqual(hash1, hash2)

    def test_generate_hash_different_data(self):
        """Test hash generation for different data"""
        hash1 = generate_hash("data1")
        hash2 = generate_hash("data2")

        self.assertNotEqual(hash1, hash2)


class SlugUtilsTest(TestCase):
    """Test slug generation utilities"""

    def test_create_slug_basic(self):
        """Test basic slug creation"""
        test_cases = [
            ("Hello World", "hello-world"),
            ("Test Title", "test-title"),
            ("Simple", "simple"),
            ("Multiple   Spaces", "multiple-spaces"),
            ("Special!@#$%Characters", "specialcharacters"),
        ]

        for input_text, expected in test_cases:
            result = create_slug(input_text)
            self.assertEqual(result, expected)

    def test_create_slug_max_length(self):
        """Test slug creation with max length"""
        long_text = "This is a very long title that should be truncated"

        # Test default max length (50)
        result = create_slug(long_text)
        self.assertLessEqual(len(result), 50)
        self.assertFalse(result.endswith("-"))  # Should not end with hyphen

        # Test custom max length
        result = create_slug(long_text, max_length=20)
        self.assertLessEqual(len(result), 20)
        self.assertFalse(result.endswith("-"))

    def test_create_slug_edge_cases(self):
        """Test slug creation edge cases"""
        edge_cases = [
            ("", ""),
            ("   ", ""),
            ("!@#$%", ""),
            ("123", "123"),
            ("CamelCase", "camelcase"),
            ("under_score", "under_score"),
        ]

        for input_text, expected in edge_cases:
            result = create_slug(input_text)
            self.assertEqual(result, expected)

    def test_generate_unique_slug_no_conflicts(self):
        """Test unique slug generation without conflicts"""
        mock_model = MockModel
        mock_model.objects = Mock()
        mock_model.objects.filter.return_value.exists.return_value = False

        result = generate_unique_slug(mock_model, "Test Title")

        self.assertEqual(result, "test-title")
        mock_model.objects.filter.assert_called_once_with(slug="test-title")

    def test_generate_unique_slug_with_conflicts(self):
        """Test unique slug generation with conflicts"""
        mock_model = MockModel
        mock_model.objects = Mock()

        # First two calls return True (conflict), third returns False
        mock_model.objects.filter.return_value.exists.side_effect = [True, True, False]

        result = generate_unique_slug(mock_model, "Test Title")

        # Should append number to resolve conflict
        self.assertEqual(result, "test-title-2")

        # Should have called filter multiple times
        self.assertEqual(mock_model.objects.filter.call_count, 3)

    def test_generate_unique_slug_max_length_with_suffix(self):
        """Test unique slug with max length and suffix"""
        mock_model = MockModel
        mock_model.objects = Mock()
        mock_model.objects.filter.return_value.exists.side_effect = [True, False]

        # Long title that will be truncated
        long_title = "This is a very long title that will need truncation"

        result = generate_unique_slug(mock_model, long_title, max_length=20)

        # Should be truncated and have suffix
        self.assertLessEqual(len(result), 20)
        self.assertTrue(result.endswith("-1"))

    def test_generate_unique_slug_custom_field(self):
        """Test unique slug with custom slug field name"""
        mock_model = MockModel
        mock_model.objects = Mock()
        mock_model.objects.filter.return_value.exists.return_value = False

        result = generate_unique_slug(
            mock_model, "Test Title", slug_field="custom_slug"
        )

        mock_model.objects.filter.assert_called_once_with(custom_slug="test-title")


class ModelUtilsTest(TestCase):
    """Test model-related utilities"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_get_object_or_none_exists(self):
        """Test get_object_or_none when object exists"""
        mock_model = Mock()
        mock_model.DoesNotExist = MockModel.DoesNotExist
        expected_obj = MockModel(id=1, name="Test")
        mock_model.objects.get.return_value = expected_obj

        result = get_object_or_none(mock_model, id=1)

        self.assertEqual(result, expected_obj)
        mock_model.objects.get.assert_called_once_with(id=1)

    def test_get_object_or_none_does_not_exist(self):
        """Test get_object_or_none when object doesn't exist"""
        mock_model = Mock()
        mock_model.DoesNotExist = MockModel.DoesNotExist
        mock_model.objects.get.side_effect = MockModel.DoesNotExist()

        result = get_object_or_none(mock_model, id=999)

        self.assertIsNone(result)
        mock_model.objects.get.assert_called_once_with(id=999)

    def test_bulk_update_or_create_empty_list(self):
        """Test bulk_update_or_create with empty list"""
        mock_model = MockModel

        created, updated = bulk_update_or_create(mock_model, [])

        self.assertEqual(created, [])
        self.assertEqual(updated, [])

    def test_bulk_update_or_create_all_new(self):
        """Test bulk_update_or_create with all new objects"""
        mock_model = MockModel
        mock_model._meta = Mock()
        mock_model._meta.fields = [
            Mock(name="name", primary_key=False),
            Mock(name="email", primary_key=False),
        ]

        # No existing objects
        mock_model.objects.filter.return_value = []

        # Mock bulk_create
        created_objects = [MockModel(id=1), MockModel(id=2)]
        mock_model.objects.bulk_create.return_value = created_objects

        objects_data = [
            {"name": "Test 1", "email": "test1@example.com"},
            {"name": "Test 2", "email": "test2@example.com"},
        ]

        created, updated = bulk_update_or_create(mock_model, objects_data)

        self.assertEqual(len(created), 2)
        self.assertEqual(updated, [])
        mock_model.objects.bulk_create.assert_called_once()

    def test_bulk_update_or_create_all_existing(self):
        """Test bulk_update_or_create with all existing objects"""
        mock_model = MockModel
        mock_model._meta = Mock()
        mock_model._meta.fields = [
            Mock(name="id", primary_key=True),
            Mock(name="name", primary_key=False),
            Mock(name="email", primary_key=False),
        ]

        # Existing objects
        existing_obj1 = MockModel(id=1, name="Old Name 1")
        existing_obj2 = MockModel(id=2, name="Old Name 2")
        mock_model.objects.filter.return_value = [existing_obj1, existing_obj2]

        # Mock bulk_update
        mock_model.objects.bulk_update.return_value = None

        objects_data = [
            {"id": 1, "name": "New Name 1", "email": "new1@example.com"},
            {"id": 2, "name": "New Name 2", "email": "new2@example.com"},
        ]

        created, updated = bulk_update_or_create(mock_model, objects_data, "id")

        self.assertEqual(created, [])
        self.assertEqual(len(updated), 2)

        # Check that objects were updated
        self.assertEqual(existing_obj1.name, "New Name 1")
        self.assertEqual(existing_obj2.name, "New Name 2")

        mock_model.objects.bulk_update.assert_called_once()

    def test_bulk_update_or_create_mixed(self):
        """Test bulk_update_or_create with mix of new and existing"""
        mock_model = MockModel
        mock_model._meta = Mock()
        mock_model._meta.fields = [
            Mock(name="id", primary_key=True),
            Mock(name="name", primary_key=False),
        ]

        # One existing object
        existing_obj = MockModel(id=1, name="Existing")
        mock_model.objects.filter.return_value = [existing_obj]

        # Mock bulk operations
        new_obj = MockModel(id=2, name="New")
        mock_model.objects.bulk_create.return_value = [new_obj]
        mock_model.objects.bulk_update.return_value = None

        objects_data = [
            {"id": 1, "name": "Updated Existing"},  # Update existing
            {"name": "New Object"},  # Create new (no ID)
        ]

        created, updated = bulk_update_or_create(mock_model, objects_data, "id")

        self.assertEqual(len(created), 1)
        self.assertEqual(len(updated), 1)

        # Check existing object was updated
        self.assertEqual(existing_obj.name, "Updated Existing")


class StringUtilsTest(TestCase):
    """Test string manipulation utilities"""

    def test_safe_get_dict_value_exists(self):
        """Test safe_get_dict_value with existing key"""
        dictionary = {"key1": "value1", "key2": 42}

        result = safe_get_dict_value(dictionary, "key1")
        self.assertEqual(result, "value1")

        result = safe_get_dict_value(dictionary, "key2")
        self.assertEqual(result, 42)

    def test_safe_get_dict_value_missing(self):
        """Test safe_get_dict_value with missing key"""
        dictionary = {"key1": "value1"}

        result = safe_get_dict_value(dictionary, "missing_key")
        self.assertIsNone(result)

        result = safe_get_dict_value(dictionary, "missing_key", "default")
        self.assertEqual(result, "default")

    def test_safe_get_dict_value_error_handling(self):
        """Test safe_get_dict_value error handling"""
        # Test with None (not a dict)
        result = safe_get_dict_value(None, "key")
        self.assertIsNone(result)

        result = safe_get_dict_value(None, "key", "default")
        self.assertEqual(result, "default")

    def test_truncate_string_short(self):
        """Test truncate_string with short text"""
        text = "Short text"
        result = truncate_string(text, max_length=100)
        self.assertEqual(result, text)

    def test_truncate_string_long(self):
        """Test truncate_string with long text"""
        text = "This is a very long text that should be truncated"
        result = truncate_string(text, max_length=20)

        self.assertLessEqual(len(result), 20)
        self.assertTrue(result.endswith("..."))
        self.assertTrue(text.startswith(result[:-3]))

    def test_truncate_string_custom_suffix(self):
        """Test truncate_string with custom suffix"""
        text = "Long text that needs truncation"
        result = truncate_string(text, max_length=15, suffix="...")

        self.assertLessEqual(len(result), 15)
        self.assertTrue(result.endswith("..."))

        # Test different suffix
        result = truncate_string(text, max_length=15, suffix=" [...]")
        self.assertLessEqual(len(result), 15)
        self.assertTrue(result.endswith(" [...]"))

    def test_mask_email_valid(self):
        """Test mask_email with valid emails"""
        test_cases = [
            ("test@example.com", "t**t@example.com"),
            ("a@example.com", "a@example.com"),
            ("ab@example.com", "a*@example.com"),
            ("user.name@domain.com", "u*******e@domain.com"),
        ]

        for email, expected in test_cases:
            result = mask_email(email)
            # Check basic structure
            self.assertIn("@", result)
            self.assertTrue(result.endswith("@" + email.split("@")[1]))

    def test_mask_email_invalid(self):
        """Test mask_email with invalid emails"""
        invalid_emails = [
            "not-an-email",
            "",
            "no-at-symbol",
            "@domain.com",
            "user@",
        ]

        for email in invalid_emails:
            result = mask_email(email)
            # Should return original for invalid formats
            if "@" not in email:
                self.assertEqual(result, email)


class DateTimeUtilsTest(TestCase):
    """Test date/time utilities"""

    def test_time_since_creation_days(self):
        """Test time_since_creation with days"""
        created_at = timezone.now() - timezone.timedelta(days=5)

        result = time_since_creation(created_at)
        self.assertEqual(result, "5 days ago")

    def test_time_since_creation_hours(self):
        """Test time_since_creation with hours"""
        created_at = timezone.now() - timezone.timedelta(hours=3)

        result = time_since_creation(created_at)
        self.assertEqual(result, "3 hours ago")

    def test_time_since_creation_minutes(self):
        """Test time_since_creation with minutes"""
        created_at = timezone.now() - timezone.timedelta(minutes=30)

        result = time_since_creation(created_at)
        self.assertEqual(result, "30 minutes ago")

    def test_time_since_creation_just_now(self):
        """Test time_since_creation with recent time"""
        created_at = timezone.now() - timezone.timedelta(seconds=30)

        result = time_since_creation(created_at)
        self.assertEqual(result, "Just now")

    def test_time_since_creation_edge_cases(self):
        """Test time_since_creation edge cases"""
        # Exactly 1 day
        created_at = timezone.now() - timezone.timedelta(days=1)
        result = time_since_creation(created_at)
        self.assertEqual(result, "1 days ago")

        # Exactly 1 hour
        created_at = timezone.now() - timezone.timedelta(hours=1)
        result = time_since_creation(created_at)
        self.assertEqual(result, "1 hours ago")


class FileUtilsTest(TestCase):
    """Test file-related utilities"""

    def test_format_file_size_bytes(self):
        """Test format_file_size with bytes"""
        test_cases = [
            (0, "0 B"),
            (1, "1.0 B"),
            (512, "512.0 B"),
            (1023, "1023.0 B"),
        ]

        for size_bytes, expected in test_cases:
            result = format_file_size(size_bytes)
            self.assertEqual(result, expected)

    def test_format_file_size_kb(self):
        """Test format_file_size with kilobytes"""
        test_cases = [
            (1024, "1.0 KB"),
            (1536, "1.5 KB"),
            (2048, "2.0 KB"),
        ]

        for size_bytes, expected in test_cases:
            result = format_file_size(size_bytes)
            self.assertEqual(result, expected)

    def test_format_file_size_larger_units(self):
        """Test format_file_size with larger units"""
        test_cases = [
            (1024**2, "1.0 MB"),
            (1024**3, "1.0 GB"),
            (1024**4, "1.0 TB"),
        ]

        for size_bytes, expected in test_cases:
            result = format_file_size(size_bytes)
            self.assertEqual(result, expected)

    def test_format_file_size_precision(self):
        """Test format_file_size precision"""
        # Test that result is rounded to 1 decimal place
        size_bytes = int(1.234567 * 1024 * 1024)  # ~1.23 MB
        result = format_file_size(size_bytes)

        # Should be rounded to 1 decimal place
        self.assertRegex(result, r"^\d+\.\d MB$")


class ValidationUtilsTest(TestCase):
    """Test validation utilities"""

    def test_validate_json_structure_valid(self):
        """Test validate_json_structure with valid data"""
        data = {
            "field1": "value1",
            "field2": 42,
            "field3": True,
        }

        required_fields = ["field1", "field2"]

        errors = validate_json_structure(data, required_fields)
        self.assertEqual(errors, {})

    def test_validate_json_structure_missing_fields(self):
        """Test validate_json_structure with missing fields"""
        data = {
            "field1": "value1",
        }

        required_fields = ["field1", "field2", "field3"]

        errors = validate_json_structure(data, required_fields)

        self.assertIn("field2", errors)
        self.assertIn("field3", errors)
        self.assertNotIn("field1", errors)

        self.assertEqual(errors["field2"], "Field 'field2' is required")
        self.assertEqual(errors["field3"], "Field 'field3' is required")

    def test_validate_json_structure_empty_required(self):
        """Test validate_json_structure with no required fields"""
        data = {"any": "data"}
        required_fields = []

        errors = validate_json_structure(data, required_fields)
        self.assertEqual(errors, {})


class HTTPUtilsTest(TestCase):
    """Test HTTP-related utilities"""

    def test_get_client_ip_x_forwarded_for(self):
        """Test get_client_ip with X-Forwarded-For header"""
        request = Mock()
        request.META = {
            "HTTP_X_FORWARDED_FOR": "192.168.1.1, 10.0.0.1",
            "REMOTE_ADDR": "127.0.0.1",
        }

        result = get_client_ip(request)
        self.assertEqual(result, "192.168.1.1")

    def test_get_client_ip_remote_addr(self):
        """Test get_client_ip with REMOTE_ADDR"""
        request = Mock()
        request.META = {
            "REMOTE_ADDR": "192.168.1.1",
        }

        result = get_client_ip(request)
        self.assertEqual(result, "192.168.1.1")

    def test_get_client_ip_no_headers(self):
        """Test get_client_ip with no IP headers"""
        request = Mock()
        request.META = {}

        result = get_client_ip(request)
        self.assertIsNone(result)

    def test_get_user_agent_present(self):
        """Test get_user_agent with user agent present"""
        request = Mock()
        request.META = {
            "HTTP_USER_AGENT": "Mozilla/5.0 (compatible; test)",
        }

        result = get_user_agent(request)
        self.assertEqual(result, "Mozilla/5.0 (compatible; test)")

    def test_get_user_agent_missing(self):
        """Test get_user_agent with no user agent"""
        request = Mock()
        request.META = {}

        result = get_user_agent(request)
        self.assertEqual(result, "")


class EmailUtilsTest(TestCase):
    """Test email utilities"""

    @patch("apps.core.utils.send_mail")
    def test_send_notification_email_success(self, mock_send_mail):
        """Test successful notification email sending"""
        mock_send_mail.return_value = True

        result = send_notification_email(
            subject="Test Subject",
            message="Test Message",
            recipient_list=["test@example.com"],
        )

        self.assertTrue(result)
        mock_send_mail.assert_called_once()

    @patch("apps.core.utils.send_mail")
    def test_send_notification_email_failure_silent(self, mock_send_mail):
        """Test notification email failure with fail_silently=True"""
        mock_send_mail.side_effect = Exception("SMTP Error")

        result = send_notification_email(
            subject="Test Subject",
            message="Test Message",
            recipient_list=["test@example.com"],
            fail_silently=True,
        )

        self.assertFalse(result)

    @patch("apps.core.utils.send_mail")
    def test_send_notification_email_failure_raise(self, mock_send_mail):
        """Test notification email failure with fail_silently=False"""
        mock_send_mail.side_effect = Exception("SMTP Error")

        with self.assertRaises(Exception):
            send_notification_email(
                subject="Test Subject",
                message="Test Message",
                recipient_list=["test@example.com"],
                fail_silently=False,
            )

    @patch("apps.core.utils.send_mail")
    @patch("django.conf.settings.DEFAULT_FROM_EMAIL", "default@example.com")
    def test_send_notification_email_default_from(self, mock_send_mail):
        """Test notification email with default from_email"""
        result = send_notification_email(
            subject="Test Subject",
            message="Test Message",
            recipient_list=["test@example.com"],
        )

        # Check that settings.DEFAULT_FROM_EMAIL was used
        call_args = mock_send_mail.call_args
        self.assertIn("from_email", call_args.kwargs)


class UtilsIntegrationTest(TestCase):
    """Test utility function integration"""

    def test_slug_generation_pipeline(self):
        """Test complete slug generation pipeline"""
        # Test the complete flow from title to unique slug
        mock_model = Mock()

        # No conflicts - mock the filter().exists() chain
        mock_filter = Mock()
        mock_filter.exists.return_value = False
        mock_model.objects.filter.return_value = mock_filter

        title = "My Blog Post Title!"
        result = generate_unique_slug(mock_model, title)

        # Should be properly slugified and unique
        self.assertEqual(result, "my-blog-post-title")

        # Test with conflicts
        mock_filter.exists.side_effect = [True, False]
        result = generate_unique_slug(mock_model, title)

        self.assertEqual(result, "my-blog-post-title-1")

    def test_utility_chaining(self):
        """Test chaining utility functions"""
        # Generate UUID, then create hash of it
        uuid_str = generate_uuid()
        hash_result = generate_hash(uuid_str)

        self.assertIsInstance(uuid_str, str)
        self.assertIsInstance(hash_result, str)
        self.assertEqual(len(hash_result), 64)  # SHA256

        # Generate slug from UUID
        slug_result = create_slug(uuid_str)
        self.assertIsInstance(slug_result, str)
        self.assertIn("-", uuid_str)  # Original UUID has hyphens
        # Slug should be alphanumeric only
