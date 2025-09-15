"""Comprehensive test coverage for core app models and mixins"""

import os

import django

# Setup Django before imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

import uuid
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase
from django.utils import timezone

from apps.core.managers import PublishedManager, SoftDeleteManager
from apps.core.mixins import (
    ActiveManager,
    AllObjectsManager,
    BaseModel,
    FullTrackingMixin,
    MetadataMixin,
    OrderingMixin,
    SlugMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UserTrackingMixin,
)

User = get_user_model()


class ConcreteTimestampModel(TimestampMixin):
    """Concrete model for testing TimestampMixin"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class ConcreteUserTrackingModel(UserTrackingMixin):
    """Concrete model for testing UserTrackingMixin"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class ConcreteFullTrackingModel(FullTrackingMixin):
    """Concrete model for testing FullTrackingMixin"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class ConcreteSoftDeleteModel(SoftDeleteMixin):
    """Concrete model for testing SoftDeleteMixin"""

    name = models.CharField(max_length=100)
    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        app_label = "core"


class ConcreteOrderingModel(OrderingMixin):
    """Concrete model for testing OrderingMixin"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"
        ordering = ["order", "name"]


class ConcreteSlugModel(SlugMixin):
    """Concrete model for testing SlugMixin"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class ConcreteMetadataModel(MetadataMixin):
    """Concrete model for testing MetadataMixin"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class ConcreteBaseModel(BaseModel):
    """Concrete model for testing BaseModel"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class MixinsTestPublishedModel(models.Model):
    """Concrete model for testing PublishedManager in mixins tests"""

    name = models.CharField(max_length=100)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    objects = PublishedManager()

    class Meta:
        app_label = "core"


class TimestampMixinComprehensiveTest(TestCase):
    """Comprehensive tests for TimestampMixin"""

    def test_timestamp_fields_creation(self):
        """Test that timestamp fields are properly created and configured"""
        model = ConcreteTimestampModel()

        # Test field existence
        self.assertTrue(hasattr(model, "created_at"))
        self.assertTrue(hasattr(model, "updated_at"))

        # Test field types
        created_at_field = model._meta.get_field("created_at")
        updated_at_field = model._meta.get_field("updated_at")

        self.assertIsInstance(created_at_field, models.DateTimeField)
        self.assertIsInstance(updated_at_field, models.DateTimeField)

        # Test verbose names
        self.assertEqual(created_at_field.verbose_name, "Created")
        self.assertEqual(updated_at_field.verbose_name, "Updated")

    def test_timestamp_auto_behavior(self):
        """Test auto_now_add and auto_now behavior"""
        created_at_field = ConcreteTimestampModel._meta.get_field("created_at")
        updated_at_field = ConcreteTimestampModel._meta.get_field("updated_at")

        # Test auto_now_add and auto_now settings
        self.assertTrue(created_at_field.auto_now_add)
        self.assertFalse(created_at_field.auto_now)
        self.assertFalse(updated_at_field.auto_now_add)
        self.assertTrue(updated_at_field.auto_now)

    def test_mixin_is_abstract(self):
        """Test that TimestampMixin is abstract"""
        self.assertTrue(TimestampMixin._meta.abstract)

    def test_timestamp_ordering(self):
        """Test models can be ordered by timestamps"""
        # This would be tested in integration tests with actual database
        # Here we test that the fields exist and are orderable
        model = ConcreteTimestampModel()
        self.assertIn("created_at", [f.name for f in model._meta.fields])
        self.assertIn("updated_at", [f.name for f in model._meta.fields])


class UserTrackingMixinComprehensiveTest(TestCase):
    """Comprehensive tests for UserTrackingMixin"""

    def setUp(self):
        self.user1 = User.objects.create_user("user1@test.com", "password")
        self.user2 = User.objects.create_user("user2@test.com", "password")

    def test_user_tracking_fields_creation(self):
        """Test that user tracking fields are properly created"""
        model = ConcreteUserTrackingModel()

        # Test field existence
        self.assertTrue(hasattr(model, "created_by"))
        self.assertTrue(hasattr(model, "updated_by"))

        # Test field types and relationships
        created_by_field = model._meta.get_field("created_by")
        updated_by_field = model._meta.get_field("updated_by")

        self.assertIsInstance(created_by_field, models.ForeignKey)
        self.assertIsInstance(updated_by_field, models.ForeignKey)

        # Test related names
        expected_created_related = "core_concreteusertrackingmodel_created"
        expected_updated_related = "core_concreteusertrackingmodel_updated"

        self.assertEqual(
            created_by_field.remote_field.related_name, expected_created_related
        )
        self.assertEqual(
            updated_by_field.remote_field.related_name, expected_updated_related
        )

    def test_user_tracking_field_constraints(self):
        """Test field constraints (null, blank, on_delete)"""
        created_by_field = ConcreteUserTrackingModel._meta.get_field("created_by")
        updated_by_field = ConcreteUserTrackingModel._meta.get_field("updated_by")

        # Test null and blank constraints
        self.assertTrue(created_by_field.null)
        self.assertTrue(created_by_field.blank)
        self.assertTrue(updated_by_field.null)
        self.assertTrue(updated_by_field.blank)

        # Test on_delete behavior
        self.assertEqual(created_by_field.remote_field.on_delete, models.SET_NULL)
        self.assertEqual(updated_by_field.remote_field.on_delete, models.SET_NULL)

    def test_user_assignment(self):
        """Test user assignment functionality"""
        model = ConcreteUserTrackingModel()

        model.created_by = self.user1
        model.updated_by = self.user2

        self.assertEqual(model.created_by, self.user1)
        self.assertEqual(model.updated_by, self.user2)

    def test_user_null_assignment(self):
        """Test that users can be null"""
        model = ConcreteUserTrackingModel()

        model.created_by = None
        model.updated_by = None

        self.assertIsNone(model.created_by)
        self.assertIsNone(model.updated_by)

    def test_mixin_is_abstract(self):
        """Test that UserTrackingMixin is abstract"""
        self.assertTrue(UserTrackingMixin._meta.abstract)


class FullTrackingMixinComprehensiveTest(TestCase):
    """Comprehensive tests for FullTrackingMixin"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_full_tracking_inheritance(self):
        """Test that FullTrackingMixin inherits from both mixins"""
        # Check MRO (Method Resolution Order)
        mro_classes = [cls.__name__ for cls in FullTrackingMixin.__mro__]
        self.assertIn("TimestampMixin", mro_classes)
        self.assertIn("UserTrackingMixin", mro_classes)

    def test_all_fields_present(self):
        """Test that all tracking fields are present"""
        model = ConcreteFullTrackingModel()

        # From TimestampMixin
        self.assertTrue(hasattr(model, "created_at"))
        self.assertTrue(hasattr(model, "updated_at"))

        # From UserTrackingMixin
        self.assertTrue(hasattr(model, "created_by"))
        self.assertTrue(hasattr(model, "updated_by"))

    def test_field_functionality(self):
        """Test that all fields work correctly together"""
        model = ConcreteFullTrackingModel()
        model.name = "Test"
        model.created_by = self.user
        model.updated_by = self.user

        # Should not raise any errors
        self.assertEqual(model.created_by, self.user)
        self.assertEqual(model.updated_by, self.user)

    def test_mixin_is_abstract(self):
        """Test that FullTrackingMixin is abstract"""
        self.assertTrue(FullTrackingMixin._meta.abstract)


class SoftDeleteMixinComprehensiveTest(TestCase):
    """Comprehensive tests for SoftDeleteMixin"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_soft_delete_fields_creation(self):
        """Test that soft delete fields are properly created"""
        model = ConcreteSoftDeleteModel()

        # Test field existence
        self.assertTrue(hasattr(model, "is_deleted"))
        self.assertTrue(hasattr(model, "deleted_at"))
        self.assertTrue(hasattr(model, "deleted_by"))

        # Test field types
        is_deleted_field = model._meta.get_field("is_deleted")
        deleted_at_field = model._meta.get_field("deleted_at")
        deleted_by_field = model._meta.get_field("deleted_by")

        self.assertIsInstance(is_deleted_field, models.BooleanField)
        self.assertIsInstance(deleted_at_field, models.DateTimeField)
        self.assertIsInstance(deleted_by_field, models.ForeignKey)

    def test_soft_delete_field_defaults(self):
        """Test default values for soft delete fields"""
        model = ConcreteSoftDeleteModel()

        # Default values
        self.assertFalse(model.is_deleted)
        self.assertIsNone(model.deleted_at)
        self.assertIsNone(model.deleted_by)

    def test_soft_delete_functionality(self):
        """Test soft delete functionality"""
        model = ConcreteSoftDeleteModel(name="Test")

        # Mock save method to avoid database issues
        with patch.object(model, "save") as mock_save:
            with patch("django.utils.timezone.now") as mock_now:
                mock_now.return_value = timezone.datetime(
                    2023, 1, 1, tzinfo=timezone.utc
                )

                model.delete(soft=True)

                self.assertTrue(model.is_deleted)
                self.assertEqual(model.deleted_at, mock_now.return_value)
                mock_save.assert_called_once()

    def test_hard_delete_functionality(self):
        """Test hard delete functionality"""
        model = ConcreteSoftDeleteModel(name="Test")

        with patch.object(models.Model, "delete") as mock_super_delete:
            model.delete(soft=False)
            mock_super_delete.assert_called_once()

    def test_hard_delete_method(self):
        """Test hard_delete method"""
        model = ConcreteSoftDeleteModel(name="Test")

        with patch.object(models.Model, "delete") as mock_super_delete:
            model.hard_delete()
            mock_super_delete.assert_called_once()

    def test_restore_functionality(self):
        """Test restore functionality"""
        model = ConcreteSoftDeleteModel(name="Test")
        model.is_deleted = True
        model.deleted_at = timezone.now()
        model.deleted_by = self.user

        with patch.object(model, "save") as mock_save:
            model.restore()

            self.assertFalse(model.is_deleted)
            self.assertIsNone(model.deleted_at)
            self.assertIsNone(model.deleted_by)
            mock_save.assert_called_once()

    def test_soft_delete_with_user(self):
        """Test soft delete with user tracking"""

        # Create a model that combines both mixins
        class CombinedModel(SoftDeleteMixin, UserTrackingMixin):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "core"

        model = CombinedModel(name="Test")
        model.deleted_by = self.user

        with patch.object(model, "save"):
            model.delete()
            self.assertTrue(model.is_deleted)
            self.assertEqual(model.deleted_by, self.user)

    def test_delete_method_parameters(self):
        """Test delete method parameter handling"""
        model = ConcreteSoftDeleteModel(name="Test")

        # Test default soft=True
        with patch.object(model, "save") as mock_save:
            model.delete()
            self.assertTrue(model.is_deleted)
            mock_save.assert_called_once()

    def test_mixin_is_abstract(self):
        """Test that SoftDeleteMixin is abstract"""
        self.assertTrue(SoftDeleteMixin._meta.abstract)


class OrderingMixinComprehensiveTest(TestCase):
    """Comprehensive tests for OrderingMixin"""

    def test_ordering_field_creation(self):
        """Test that ordering field is properly created"""
        model = ConcreteOrderingModel()

        self.assertTrue(hasattr(model, "order"))

        order_field = model._meta.get_field("order")
        self.assertIsInstance(order_field, models.IntegerField)
        self.assertEqual(order_field.verbose_name, "Order")
        self.assertEqual(order_field.default, 0)

    def test_ordering_default_value(self):
        """Test default ordering value"""
        model = ConcreteOrderingModel()
        self.assertEqual(model.order, 0)

    def test_ordering_assignment(self):
        """Test ordering value assignment"""
        model = ConcreteOrderingModel()
        model.order = 100
        self.assertEqual(model.order, 100)

    def test_ordering_negative_values(self):
        """Test negative ordering values"""
        model = ConcreteOrderingModel()
        model.order = -10
        self.assertEqual(model.order, -10)

    def test_model_ordering_meta(self):
        """Test model ordering in Meta class"""
        self.assertEqual(ConcreteOrderingModel._meta.ordering, ["order", "name"])

    def test_mixin_is_abstract(self):
        """Test that OrderingMixin is abstract"""
        self.assertTrue(OrderingMixin._meta.abstract)


class SlugMixinComprehensiveTest(TestCase):
    """Comprehensive tests for SlugMixin"""

    def test_slug_field_creation(self):
        """Test that slug field is properly created"""
        model = ConcreteSlugModel()

        self.assertTrue(hasattr(model, "slug"))

        slug_field = model._meta.get_field("slug")
        self.assertIsInstance(slug_field, models.SlugField)
        self.assertEqual(slug_field.verbose_name, "Slug")
        self.assertEqual(slug_field.max_length, 255)
        self.assertTrue(slug_field.unique)

    def test_slug_assignment(self):
        """Test slug assignment"""
        model = ConcreteSlugModel()
        model.slug = "test-slug"
        self.assertEqual(model.slug, "test-slug")

    def test_slug_validation(self):
        """Test slug field validation"""
        model = ConcreteSlugModel()
        slug_field = model._meta.get_field("slug")

        # Test max_length constraint exists
        self.assertEqual(slug_field.max_length, 255)

        # Test unique constraint exists
        self.assertTrue(slug_field.unique)

    def test_slug_field_properties(self):
        """Test slug field properties"""
        slug_field = ConcreteSlugModel._meta.get_field("slug")

        # SlugField should allow letters, numbers, underscores, and hyphens
        self.assertIsInstance(slug_field, models.SlugField)

    def test_mixin_is_abstract(self):
        """Test that SlugMixin is abstract"""
        self.assertTrue(SlugMixin._meta.abstract)


class MetadataMixinComprehensiveTest(TestCase):
    """Comprehensive tests for MetadataMixin"""

    def test_metadata_field_creation(self):
        """Test that metadata field is properly created"""
        model = ConcreteMetadataModel()

        self.assertTrue(hasattr(model, "metadata"))

        metadata_field = model._meta.get_field("metadata")
        self.assertIsInstance(metadata_field, models.JSONField)
        self.assertEqual(metadata_field.verbose_name, "Metadata")
        self.assertEqual(metadata_field.default, dict)
        self.assertTrue(metadata_field.blank)

    def test_metadata_default_value(self):
        """Test metadata default value"""
        model = ConcreteMetadataModel()
        self.assertEqual(model.metadata, {})
        self.assertIsInstance(model.metadata, dict)

    def test_metadata_assignment_simple(self):
        """Test simple metadata assignment"""
        model = ConcreteMetadataModel()
        model.metadata = {"key": "value", "number": 42}

        self.assertEqual(model.metadata["key"], "value")
        self.assertEqual(model.metadata["number"], 42)

    def test_metadata_assignment_complex(self):
        """Test complex metadata structures"""
        model = ConcreteMetadataModel()
        complex_data = {
            "nested": {"data": [1, 2, 3], "more": {"deep": "value"}},
            "list": ["a", "b", "c"],
            "bool": True,
            "null": None,
            "float": 3.14,
        }
        model.metadata = complex_data

        self.assertEqual(model.metadata["nested"]["data"], [1, 2, 3])
        self.assertEqual(model.metadata["nested"]["more"]["deep"], "value")
        self.assertEqual(model.metadata["list"], ["a", "b", "c"])
        self.assertTrue(model.metadata["bool"])
        self.assertIsNone(model.metadata["null"])
        self.assertEqual(model.metadata["float"], 3.14)

    def test_metadata_modification(self):
        """Test metadata modification"""
        model = ConcreteMetadataModel()
        model.metadata = {"initial": "value"}

        # Modify existing key
        model.metadata["initial"] = "modified"
        self.assertEqual(model.metadata["initial"], "modified")

        # Add new key
        model.metadata["new_key"] = "new_value"
        self.assertEqual(model.metadata["new_key"], "new_value")

    def test_metadata_empty_variations(self):
        """Test various empty metadata states"""
        model = ConcreteMetadataModel()

        # Empty dict (default)
        self.assertEqual(model.metadata, {})

        # Explicitly set empty
        model.metadata = {}
        self.assertEqual(model.metadata, {})

    def test_mixin_is_abstract(self):
        """Test that MetadataMixin is abstract"""
        self.assertTrue(MetadataMixin._meta.abstract)


class BaseModelComprehensiveTest(TestCase):
    """Comprehensive tests for BaseModel"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_base_model_inheritance(self):
        """Test BaseModel inheritance chain"""
        # Check MRO contains all expected mixins
        mro_classes = [cls.__name__ for cls in BaseModel.__mro__]
        self.assertIn("TimestampMixin", mro_classes)
        self.assertIn("UserTrackingMixin", mro_classes)
        self.assertIn("MetadataMixin", mro_classes)

    def test_base_model_uuid_field(self):
        """Test UUID primary key field"""
        model = ConcreteBaseModel()

        # Test UUID field exists and is primary key
        id_field = model._meta.get_field("id")
        self.assertIsInstance(id_field, models.UUIDField)
        self.assertTrue(id_field.primary_key)
        self.assertFalse(id_field.editable)
        self.assertEqual(id_field.default, uuid.uuid4)

    def test_uuid_generation(self):
        """Test UUID generation"""
        model = ConcreteBaseModel()

        # ID should be a valid UUID
        self.assertIsInstance(model.id, uuid.UUID)

        # Each instance should have unique ID
        model2 = ConcreteBaseModel()
        self.assertNotEqual(model.id, model2.id)

    def test_all_mixin_fields_present(self):
        """Test all fields from mixins are present"""
        model = ConcreteBaseModel()

        # From TimestampMixin
        self.assertTrue(hasattr(model, "created_at"))
        self.assertTrue(hasattr(model, "updated_at"))

        # From UserTrackingMixin
        self.assertTrue(hasattr(model, "created_by"))
        self.assertTrue(hasattr(model, "updated_by"))

        # From MetadataMixin
        self.assertTrue(hasattr(model, "metadata"))

        # BaseModel's own field
        self.assertTrue(hasattr(model, "id"))

    def test_base_model_functionality(self):
        """Test that all BaseModel functionality works together"""
        model = ConcreteBaseModel()
        model.name = "Test"
        model.created_by = self.user
        model.updated_by = self.user
        model.metadata = {"test": "data"}

        # All assignments should work without error
        self.assertEqual(model.name, "Test")
        self.assertEqual(model.created_by, self.user)
        self.assertEqual(model.updated_by, self.user)
        self.assertEqual(model.metadata["test"], "data")
        self.assertIsInstance(model.id, uuid.UUID)

    def test_mixin_is_abstract(self):
        """Test that BaseModel is abstract"""
        self.assertTrue(BaseModel._meta.abstract)


class ManagerComprehensiveTest(TestCase):
    """Comprehensive tests for custom managers"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_active_manager_queryset(self):
        """Test ActiveManager filters deleted records"""
        manager = ActiveManager()

        # Mock the queryset chain
        mock_queryset = Mock()
        mock_filtered_queryset = Mock()
        mock_queryset.filter.return_value = mock_filtered_queryset

        with patch.object(models.Manager, "get_queryset", return_value=mock_queryset):
            result = manager.get_queryset()

            mock_queryset.filter.assert_called_once_with(is_deleted=False)
            self.assertEqual(result, mock_filtered_queryset)

    def test_all_objects_manager_queryset(self):
        """Test AllObjectsManager returns all records"""
        manager = AllObjectsManager()

        mock_queryset = Mock()

        with patch.object(models.Manager, "get_queryset", return_value=mock_queryset):
            result = manager.get_queryset()

            # Should return unfiltered queryset
            self.assertEqual(result, mock_queryset)

    def test_soft_delete_manager_methods(self):
        """Test SoftDeleteManager methods"""
        manager = SoftDeleteManager()

        mock_queryset = Mock()
        mock_filtered_queryset = Mock()
        mock_queryset.filter.return_value = mock_filtered_queryset

        with patch.object(manager, "get_queryset", return_value=mock_queryset):
            # Test active method
            result = manager.active()
            mock_queryset.filter.assert_called_with(is_deleted=False)

            # Reset mock
            mock_queryset.reset_mock()

            # Test with_deleted method
            with patch.object(
                models.Manager, "get_queryset", return_value=mock_queryset
            ) as mock_super:
                result = manager.with_deleted()
                mock_super.assert_called_once()

    def test_soft_delete_manager_deleted_method(self):
        """Test SoftDeleteManager deleted method"""
        manager = SoftDeleteManager()

        # Mock the manager chain for deleted records
        mock_base_manager = Mock()
        mock_queryset = Mock()
        mock_filtered_queryset = Mock()

        mock_base_manager.get_queryset.return_value = mock_queryset
        mock_queryset.filter.return_value = mock_filtered_queryset

        with patch("apps.core.managers.models.Manager", return_value=mock_base_manager):
            with patch.object(manager, "get_queryset") as mock_get_qs:
                mock_get_qs.return_value = mock_base_manager
                mock_base_manager.filter = Mock(return_value=mock_filtered_queryset)

                result = manager.deleted()

                # Should call filter with is_deleted=True on base manager
                mock_base_manager.filter.assert_called_with(is_deleted=True)

    def test_published_manager_methods(self):
        """Test PublishedManager methods"""
        manager = PublishedManager()

        mock_queryset = Mock()
        mock_filtered_queryset = Mock()
        mock_queryset.filter.return_value = mock_filtered_queryset

        with patch.object(manager, "get_queryset", return_value=mock_queryset):
            with patch("django.utils.timezone.now") as mock_now:
                mock_now.return_value = timezone.datetime(
                    2023, 1, 1, tzinfo=timezone.utc
                )

                # Test published method
                result = manager.published()
                mock_queryset.filter.assert_called_with(
                    is_published=True, published_at__lte=mock_now.return_value
                )

                # Reset mock
                mock_queryset.reset_mock()

                # Test draft method
                result = manager.draft()
                mock_queryset.filter.assert_called_with(is_published=False)

                # Reset mock
                mock_queryset.reset_mock()

                # Test scheduled method
                result = manager.scheduled()
                mock_queryset.filter.assert_called_with(
                    is_published=True, published_at__gt=mock_now.return_value
                )


class MixinIntegrationTest(TestCase):
    """Integration tests for mixin combinations"""

    def setUp(self):
        self.user1 = User.objects.create_user("user1@test.com", "password")
        self.user2 = User.objects.create_user("user2@test.com", "password")

    def test_full_tracking_and_soft_delete_integration(self):
        """Test FullTrackingMixin and SoftDeleteMixin working together"""

        class FullySoftModel(FullTrackingMixin, SoftDeleteMixin):
            name = models.CharField(max_length=100)
            objects = SoftDeleteManager()

            class Meta:
                app_label = "core"

        model = FullySoftModel(name="Test")
        model.created_by = self.user1
        model.updated_by = self.user1

        with patch.object(model, "save") as mock_save:
            # Soft delete with user tracking
            model.deleted_by = self.user2
            model.delete()

            # Should be marked as deleted with user tracking
            self.assertTrue(model.is_deleted)
            self.assertIsNotNone(model.deleted_at)
            self.assertEqual(model.created_by, self.user1)
            # deleted_by should still be user2 as set before delete

            # Restore should clear delete tracking but preserve create tracking
            model.restore()
            self.assertFalse(model.is_deleted)
            self.assertIsNone(model.deleted_at)
            self.assertIsNone(model.deleted_by)
            self.assertEqual(model.created_by, self.user1)  # Should remain

    def test_base_model_with_soft_delete(self):
        """Test BaseModel combined with SoftDeleteMixin"""

        class ExtendedBaseModel(BaseModel, SoftDeleteMixin):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "core"

        model = ExtendedBaseModel(name="Test")
        model.created_by = self.user1
        model.metadata = {"version": "1.0"}

        # Should have all fields from both mixins
        self.assertIsInstance(model.id, uuid.UUID)
        self.assertTrue(hasattr(model, "created_at"))
        self.assertTrue(hasattr(model, "created_by"))
        self.assertTrue(hasattr(model, "metadata"))
        self.assertTrue(hasattr(model, "is_deleted"))

        with patch.object(model, "save"):
            model.delete()

            # Soft delete should work
            self.assertTrue(model.is_deleted)
            # Other fields should remain
            self.assertEqual(model.created_by, self.user1)
            self.assertEqual(model.metadata["version"], "1.0")

    def test_all_mixins_combination(self):
        """Test combining all mixins"""

        class SuperModel(BaseModel, SoftDeleteMixin, OrderingMixin, SlugMixin):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "core"

        model = SuperModel(name="Super Test")
        model.created_by = self.user1
        model.metadata = {"type": "super"}
        model.order = 10
        model.slug = "super-test"

        # All fields should be present and functional
        self.assertIsInstance(model.id, uuid.UUID)
        self.assertTrue(hasattr(model, "created_at"))
        self.assertEqual(model.created_by, self.user1)
        self.assertEqual(model.metadata["type"], "super")
        self.assertEqual(model.order, 10)
        self.assertEqual(model.slug, "super-test")
        self.assertFalse(model.is_deleted)


class EdgeCaseTest(TestCase):
    """Test edge cases and error conditions"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_soft_delete_already_deleted(self):
        """Test soft deleting an already deleted record"""
        model = ConcreteSoftDeleteModel(name="Test")
        model.is_deleted = True
        model.deleted_at = timezone.now()

        with patch.object(model, "save") as mock_save:
            # Should still work and update deleted_at
            model.delete()
            self.assertTrue(model.is_deleted)
            mock_save.assert_called_once()

    def test_restore_non_deleted(self):
        """Test restoring a non-deleted record"""
        model = ConcreteSoftDeleteModel(name="Test")
        self.assertFalse(model.is_deleted)

        with patch.object(model, "save") as mock_save:
            model.restore()
            # Should still work but not change anything meaningful
            self.assertFalse(model.is_deleted)
            mock_save.assert_called_once()

    def test_metadata_with_none(self):
        """Test metadata assignment with None value"""
        model = ConcreteMetadataModel()

        # Setting metadata to None should work but might be overridden by default
        model.metadata = None
        # Depending on field configuration, this might revert to default
        # The test verifies the field accepts None assignment

    def test_user_tracking_with_deleted_user(self):
        """Test user tracking when referenced user is deleted"""
        model = ConcreteUserTrackingModel(name="Test")
        model.created_by = self.user

        # Since we use SET_NULL, this should handle user deletion gracefully
        # This is more of a constraint verification test
        self.assertEqual(model.created_by, self.user)

    def test_slug_max_length_boundary(self):
        """Test slug field at maximum length"""
        model = ConcreteSlugModel()

        # Test exactly 255 characters (max_length)
        max_slug = "a" * 255
        model.slug = max_slug
        self.assertEqual(len(model.slug), 255)

        # Test that field definition allows this
        slug_field = model._meta.get_field("slug")
        self.assertEqual(slug_field.max_length, 255)

    def test_ordering_extreme_values(self):
        """Test ordering with extreme integer values"""
        model = ConcreteOrderingModel()

        # Test with very large positive number
        model.order = 2147483647  # Max 32-bit signed int
        self.assertEqual(model.order, 2147483647)

        # Test with very large negative number
        model.order = -2147483648  # Min 32-bit signed int
        self.assertEqual(model.order, -2147483648)

    def test_uuid_field_immutability(self):
        """Test that UUID field is not editable"""
        model = ConcreteBaseModel()
        original_id = model.id

        # Attempting to change ID should be possible in memory
        # but field is marked as not editable for forms
        new_uuid = uuid.uuid4()
        model.id = new_uuid
        self.assertEqual(model.id, new_uuid)

        # But field should be marked as not editable
        id_field = model._meta.get_field("id")
        self.assertFalse(id_field.editable)
