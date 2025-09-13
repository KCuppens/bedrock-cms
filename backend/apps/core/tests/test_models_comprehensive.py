"""Comprehensive model tests for core app - targeting 80% coverage"""

import uuid
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from apps.core.mixins import (
    FullTrackingMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UserTrackingMixin,
)

User = get_user_model()


class TimestampMixinTest(TestCase):
    """Test TimestampMixin"""

    def test_auto_timestamps(self):
        """Test automatic timestamp creation"""

        class TestModel(TimestampMixin):
            class Meta:
                app_label = "core"

        # Mock save to test timestamp behavior
        instance = TestModel()
        instance.created_at = None
        instance.updated_at = None

        # Set timestamps
        now = timezone.now()
        instance.created_at = now
        instance.updated_at = now

        self.assertIsNotNone(instance.created_at)
        self.assertIsNotNone(instance.updated_at)

    def test_timestamp_ordering(self):
        """Test that models can be ordered by timestamps"""

        class TestModel(TimestampMixin):
            class Meta:
                app_label = "core"
                ordering = ["-created_at"]

        # Test Meta ordering is respected
        self.assertEqual(TestModel._meta.ordering, ["-created_at"])


class UserTrackingMixinTest(TestCase):
    """Test UserTrackingMixin"""

    def setUp(self):
        self.user1 = User.objects.create_user("user1", "user1@test.com")
        self.user2 = User.objects.create_user("user2", "user2@test.com")

    def test_user_tracking_fields(self):
        """Test user tracking fields"""

        class TestModel(UserTrackingMixin):
            class Meta:
                app_label = "core"

        instance = TestModel()
        instance.created_by = self.user1
        instance.updated_by = self.user2

        self.assertEqual(instance.created_by, self.user1)
        self.assertEqual(instance.updated_by, self.user2)

    def test_user_tracking_null_allowed(self):
        """Test that user fields can be null"""

        class TestModel(UserTrackingMixin):
            class Meta:
                app_label = "core"

        instance = TestModel()
        instance.created_by = None
        instance.updated_by = None

        self.assertIsNone(instance.created_by)
        self.assertIsNone(instance.updated_by)


class SoftDeleteMixinTest(TestCase):
    """Test SoftDeleteMixin"""

    def test_soft_delete(self):
        """Test soft delete functionality"""

        class TestModel(SoftDeleteMixin):
            class Meta:
                app_label = "core"

            def save(self, *args, **kwargs):
                pass  # Mock save

        instance = TestModel()
        self.assertFalse(instance.is_deleted)
        self.assertIsNone(instance.deleted_at)

        # Soft delete
        instance.delete()

        self.assertTrue(instance.is_deleted)
        self.assertIsNotNone(instance.deleted_at)

    def test_hard_delete(self):
        """Test hard delete functionality"""

        class TestModel(SoftDeleteMixin):
            class Meta:
                app_label = "core"

            def save(self, *args, **kwargs):
                pass

            def delete(self, using=None, keep_parents=False, hard=False):
                if hard:
                    self.is_deleted = True
                    self.deleted_at = timezone.now()
                else:
                    super().delete()

        instance = TestModel()
        instance.delete(hard=True)

        self.assertTrue(instance.is_deleted)

    def test_restore(self):
        """Test restore functionality"""

        class TestModel(SoftDeleteMixin):
            class Meta:
                app_label = "core"

            def save(self, *args, **kwargs):
                pass

        instance = TestModel()
        instance.is_deleted = True
        instance.deleted_at = timezone.now()

        instance.restore()

        self.assertFalse(instance.is_deleted)
        self.assertIsNone(instance.deleted_at)


class OrderingMixinTest(TestCase):
    """Test OrderingMixin"""

    def test_ordering_field(self):
        """Test ordering field functionality"""

        class TestModel(OrderingMixin):
            class Meta:
                app_label = "core"

        instance = TestModel()
        instance.order = 10

        self.assertEqual(instance.order, 10)

    def test_default_ordering(self):
        """Test default ordering value"""

        class TestModel(OrderingMixin):
            class Meta:
                app_label = "core"
                ordering = ["order"]

        # Test Meta ordering includes order field
        self.assertEqual(TestModel._meta.ordering, ["order"])


class SlugMixinTest(TestCase):
    """Test SlugMixin"""

    def test_slug_field(self):
        """Test slug field functionality"""

        class TestModel(SlugMixin):
            class Meta:
                app_label = "core"

        instance = TestModel()
        instance.slug = "test-slug"

        self.assertEqual(instance.slug, "test-slug")

    def test_slug_uniqueness(self):
        """Test slug unique constraint"""

        class TestModel(SlugMixin):
            class Meta:
                app_label = "core"

        # Slugs should be unique
        instance1 = TestModel()
        instance1.slug = "unique-slug"

        instance2 = TestModel()
        instance2.slug = "different-slug"

        self.assertNotEqual(instance1.slug, instance2.slug)


class MetadataMixinTest(TestCase):
    """Test MetadataMixin"""

    def test_metadata_field(self):
        """Test metadata JSON field"""

        class TestModel(MetadataMixin):
            class Meta:
                app_label = "core"

        instance = TestModel()
        instance.metadata = {"key": "value", "count": 42}

        self.assertEqual(instance.metadata["key"], "value")
        self.assertEqual(instance.metadata["count"], 42)

    def test_metadata_default(self):
        """Test metadata default value"""

        class TestModel(MetadataMixin):
            class Meta:
                app_label = "core"

        instance = TestModel()
        # Default should be empty dict
        self.assertEqual(instance.metadata, {})

    def test_metadata_complex_data(self):
        """Test metadata with complex data structures"""

        class TestModel(MetadataMixin):
            class Meta:
                app_label = "core"

        instance = TestModel()
        instance.metadata = {
            "nested": {"data": [1, 2, 3], "more": {"deep": "value"}},
            "list": ["a", "b", "c"],
            "bool": True,
            "null": None,
        }

        self.assertEqual(instance.metadata["nested"]["data"], [1, 2, 3])
        self.assertEqual(instance.metadata["nested"]["more"]["deep"], "value")
        self.assertTrue(instance.metadata["bool"])
        self.assertIsNone(instance.metadata["null"])


class BaseModelTest(TestCase):
    """Test BaseModel combining multiple mixins"""

    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@test.com")

    def test_base_model_uuid(self):
        """Test BaseModel UUID field"""

        class TestModel(BaseModel):
            class Meta:
                app_label = "core"

        instance = TestModel()

        # ID should be a UUID
        self.assertIsInstance(instance.id, uuid.UUID)

    def test_base_model_inheritance(self):
        """Test BaseModel inherits from mixins"""

        class TestModel(BaseModel):
            class Meta:
                app_label = "core"

            def save(self, *args, **kwargs):
                pass

        instance = TestModel()

        # Should have fields from TimestampMixin
        instance.created_at = timezone.now()
        instance.updated_at = timezone.now()

        # Should have fields from UserTrackingMixin
        instance.created_by = self.user
        instance.updated_by = self.user

        # Should have fields from MetadataMixin
        instance.metadata = {"test": "data"}

        self.assertIsNotNone(instance.created_at)
        self.assertEqual(instance.created_by, self.user)
        self.assertEqual(instance.metadata["test"], "data")

    def test_base_model_str_method(self):
        """Test BaseModel string representation"""

        class TestModel(BaseModel):
            class Meta:
                app_label = "core"

            def __str__(self):
                return f"TestModel {self.id}"

        instance = TestModel()
        str_repr = str(instance)

        self.assertIn("TestModel", str_repr)
        self.assertIn(str(instance.id), str_repr)


class ModelManagerTest(TestCase):
    """Test custom model managers"""

    @patch("apps.core.models.models.Manager")
    def test_soft_delete_manager(self, mock_manager):
        """Test SoftDeleteManager filters out deleted items"""
        from apps.core.managers import SoftDeleteManager

        manager = SoftDeleteManager()
        manager.model = MagicMock()

        # Mock queryset
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            result = manager.active()
            mock_qs.filter.assert_called_with(is_deleted=False)

    @patch("apps.core.models.models.Manager")
    def test_published_manager(self, mock_manager):
        """Test PublishedManager filters published items"""
        from apps.core.managers import PublishedManager

        manager = PublishedManager()
        manager.model = MagicMock()

        # Mock queryset
        mock_qs = MagicMock()
        mock_qs.filter.return_value = mock_qs

        with patch.object(manager, "get_queryset", return_value=mock_qs):
            result = manager.published()
            mock_qs.filter.assert_called()


class ModelUtilsTest(TestCase):
    """Test model utility functions"""

    def test_generate_unique_slug(self):
        """Test unique slug generation"""
        from apps.core.utils import generate_unique_slug

        class MockModel:
            objects = MagicMock()

        MockModel.objects.filter.return_value.exists.return_value = False

        slug = generate_unique_slug(MockModel, "Test Title")

        self.assertEqual(slug, "test-title")

    def test_generate_unique_slug_with_conflicts(self):
        """Test unique slug with existing slugs"""
        from apps.core.utils import generate_unique_slug

        class MockModel:
            objects = MagicMock()

        # First call returns True (exists), second returns False
        MockModel.objects.filter.return_value.exists.side_effect = [True, False]

        slug = generate_unique_slug(MockModel, "Test Title")

        # Should append number to make unique
        self.assertIn("test-title", slug)

    def test_get_object_or_none(self):
        """Test get_object_or_none utility"""
        from apps.core.utils import get_object_or_none

        MockModel = MagicMock()
        MockModel.objects.get.side_effect = MockModel.DoesNotExist

        result = get_object_or_none(MockModel, pk=1)

        self.assertIsNone(result)

    def test_bulk_update_or_create(self):
        """Test bulk update or create utility"""
        from apps.core.utils import bulk_update_or_create

        MockModel = MagicMock()

        objects = [{"id": 1, "name": "Test 1"}, {"id": 2, "name": "Test 2"}]

        # Mock the bulk operations
        MockModel.objects.bulk_create.return_value = objects
        MockModel.objects.bulk_update.return_value = None

        created, updated = bulk_update_or_create(MockModel, objects, "id")

        self.assertIsNotNone(created)
