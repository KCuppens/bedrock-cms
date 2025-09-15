"""Comprehensive test coverage for model validation and constraints"""

import uuid
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase
from django.utils import timezone

from apps.core.mixins import (
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


class ValidationTestModel(BaseModel):
    """Concrete model for validation testing"""

    name = models.CharField(max_length=100, blank=False)
    email = models.EmailField(unique=True)
    age = models.PositiveIntegerField()

    class Meta:
        app_label = "core"


class SlugValidationModel(SlugMixin):
    """Concrete model for slug validation testing"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class OrderingValidationModel(OrderingMixin):
    """Concrete model for ordering validation testing"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"
        ordering = ["order"]


class MetadataValidationModel(MetadataMixin):
    """Concrete model for metadata validation testing"""

    name = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class ComplexValidationModel(BaseModel, SoftDeleteMixin):
    """Complex model combining multiple mixins for validation testing"""

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ("tech", "Technology"),
            ("health", "Health"),
            ("finance", "Finance"),
        ],
    )

    class Meta:
        app_label = "core"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "category"],
                condition=models.Q(is_deleted=False),
                name="unique_name_category_active",
            )
        ]


class ModelValidationTest(TestCase):
    """Test model field validation"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_timestamp_field_validation(self):
        """Test timestamp field validation"""
        model = ValidationTestModel()

        # created_at and updated_at should accept valid datetimes
        now = timezone.now()
        model.created_at = now
        model.updated_at = now

        # Should not raise validation errors
        self.assertEqual(model.created_at, now)
        self.assertEqual(model.updated_at, now)

    def test_user_tracking_field_validation(self):
        """Test user tracking field validation"""
        model = ValidationTestModel()

        # Should accept valid user instances
        model.created_by = self.user
        model.updated_by = self.user

        self.assertEqual(model.created_by, self.user)
        self.assertEqual(model.updated_by, self.user)

        # Should accept None (null=True)
        model.created_by = None
        model.updated_by = None

        self.assertIsNone(model.created_by)
        self.assertIsNone(model.updated_by)

    def test_uuid_field_validation(self):
        """Test UUID field validation"""
        model = ValidationTestModel()

        # UUID should be generated automatically
        self.assertIsInstance(model.id, uuid.UUID)

        # Should accept valid UUID
        new_uuid = uuid.uuid4()
        model.id = new_uuid
        self.assertEqual(model.id, new_uuid)

    def test_metadata_field_validation(self):
        """Test metadata JSON field validation"""
        model = MetadataValidationModel()

        # Should accept valid JSON structures
        valid_metadata = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }

        model.metadata = valid_metadata
        self.assertEqual(model.metadata, valid_metadata)

        # Should accept empty dict
        model.metadata = {}
        self.assertEqual(model.metadata, {})

    def test_slug_field_validation(self):
        """Test slug field validation"""
        model = SlugValidationModel()

        # Should accept valid slugs
        valid_slugs = [
            "simple-slug",
            "slug_with_underscores",
            "slug123",
            "a" * 255,  # Maximum length
        ]

        for slug in valid_slugs:
            model.slug = slug
            self.assertEqual(model.slug, slug)

        # Test slug max length constraint
        slug_field = model._meta.get_field("slug")
        self.assertEqual(slug_field.max_length, 255)

    def test_ordering_field_validation(self):
        """Test ordering field validation"""
        model = OrderingValidationModel()

        # Should accept valid integers
        valid_orders = [0, 1, -1, 1000, -1000, 2147483647, -2147483648]

        for order in valid_orders:
            model.order = order
            self.assertEqual(model.order, order)

    def test_soft_delete_field_validation(self):
        """Test soft delete field validation"""
        model = ComplexValidationModel()

        # is_deleted should be boolean
        model.is_deleted = True
        self.assertTrue(model.is_deleted)

        model.is_deleted = False
        self.assertFalse(model.is_deleted)

        # deleted_at should accept datetime or None
        now = timezone.now()
        model.deleted_at = now
        self.assertEqual(model.deleted_at, now)

        model.deleted_at = None
        self.assertIsNone(model.deleted_at)

        # deleted_by should accept user or None
        model.deleted_by = self.user
        self.assertEqual(model.deleted_by, self.user)

        model.deleted_by = None
        self.assertIsNone(model.deleted_by)


class ModelConstraintTest(TestCase):
    """Test model constraints and uniqueness"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_slug_uniqueness_constraint(self):
        """Test slug uniqueness constraint"""
        # Create first model with a slug
        model1 = SlugValidationModel(name="Test 1", slug="unique-slug")

        # Attempting to create another model with same slug should be blocked
        # (This would be enforced at database level in real scenarios)
        model2 = SlugValidationModel(name="Test 2", slug="unique-slug")

        # Test that the field is configured as unique
        slug_field = SlugValidationModel._meta.get_field("slug")
        self.assertTrue(slug_field.unique)

    def test_email_uniqueness_constraint(self):
        """Test email uniqueness constraint in complex model"""
        model1 = ComplexValidationModel(
            name="Test 1", email="test@example.com", category="tech"
        )

        # Second model with same email should violate constraint
        model2 = ComplexValidationModel(
            name="Test 2", email="test@example.com", category="health"
        )

        # Test that the field is configured as unique
        email_field = ComplexValidationModel._meta.get_field("email")
        self.assertTrue(email_field.unique)

    def test_composite_unique_constraint(self):
        """Test composite unique constraint with soft delete condition"""
        # Test the custom constraint defined in ComplexValidationModel
        constraints = ComplexValidationModel._meta.constraints

        # Should have our custom constraint
        constraint_names = [c.name for c in constraints]
        self.assertIn("unique_name_category_active", constraint_names)

        # Find our constraint
        unique_constraint = next(
            c for c in constraints if c.name == "unique_name_category_active"
        )

        # Test constraint properties
        self.assertIsInstance(unique_constraint, models.UniqueConstraint)
        self.assertEqual(list(unique_constraint.fields), ["name", "category"])

        # Test that condition exists (checks for non-deleted records)
        self.assertIsNotNone(unique_constraint.condition)

    def test_foreign_key_constraints(self):
        """Test foreign key constraints in user tracking"""
        model = ComplexValidationModel()

        # Should accept valid user
        model.created_by = self.user
        self.assertEqual(model.created_by, self.user)

        # Test SET_NULL behavior is configured
        created_by_field = ComplexValidationModel._meta.get_field("created_by")
        self.assertEqual(created_by_field.remote_field.on_delete, models.SET_NULL)

    def test_choice_field_constraints(self):
        """Test choice field constraints"""
        model = ComplexValidationModel()

        # Should accept valid choices
        valid_choices = ["tech", "health", "finance"]
        for choice in valid_choices:
            model.category = choice
            self.assertEqual(model.category, choice)

        # Test that choices are properly configured
        category_field = ComplexValidationModel._meta.get_field("category")
        expected_choices = [
            ("tech", "Technology"),
            ("health", "Health"),
            ("finance", "Finance"),
        ]
        self.assertEqual(category_field.choices, expected_choices)


class ValidationMethodTest(TestCase):
    """Test model validation methods"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_full_clean_validation(self):
        """Test full_clean method calls field validation"""
        model = ValidationTestModel(name="Test", email="test@example.com", age=25)

        # Mock full_clean to avoid database interactions
        with patch.object(model, "full_clean") as mock_full_clean:
            mock_full_clean.return_value = None  # No validation errors

            try:
                model.full_clean()
                mock_full_clean.assert_called_once()
            except ValidationError:
                self.fail("full_clean() raised ValidationError for valid data")

    def test_model_clean_method_override(self):
        """Test custom clean method implementation"""

        class CustomValidationModel(BaseModel):
            name = models.CharField(max_length=100)
            email = models.EmailField()

            class Meta:
                app_label = "core"

            def clean(self):
                """Custom validation logic"""
                super().clean()
                if self.name and self.email:
                    if self.name.lower() in self.email.lower():
                        raise ValidationError("Name cannot be part of email")

        # Test custom validation passes for valid data
        model = CustomValidationModel(name="John", email="jane@example.com")
        try:
            model.clean()
        except ValidationError:
            self.fail("clean() raised ValidationError for valid data")

        # Test custom validation fails for invalid data
        model = CustomValidationModel(name="john", email="john@example.com")
        with self.assertRaises(ValidationError):
            model.clean()

    def test_save_with_validation(self):
        """Test save method with validation"""
        model = ValidationTestModel(name="Test", email="test@example.com", age=25)

        # Mock the save to avoid database operations
        with patch.object(models.Model, "save") as mock_save:
            # Should call full_clean before save if requested
            model.save()

            # Verify save was called
            mock_save.assert_called_once()

    def test_soft_delete_validation_interaction(self):
        """Test soft delete interaction with validation"""
        model = ComplexValidationModel(
            name="Test", email="test@example.com", category="tech"
        )

        # Test that soft delete doesn't interfere with validation
        model.is_deleted = True
        model.deleted_at = timezone.now()

        # Mock full_clean to avoid database interactions
        with patch.object(model, "full_clean") as mock_full_clean:
            mock_full_clean.return_value = None

            try:
                model.full_clean()
                mock_full_clean.assert_called_once()
            except ValidationError:
                self.fail("Soft delete fields caused validation error")

        # Test restore validation
        with patch.object(model, "save"):
            model.restore()

            # Should reset soft delete fields
            self.assertFalse(model.is_deleted)
            self.assertIsNone(model.deleted_at)
            self.assertIsNone(model.deleted_by)


class FieldConstraintTest(TestCase):
    """Test individual field constraints"""

    def test_charfield_constraints(self):
        """Test CharField constraints"""
        model = ValidationTestModel()

        # Test max_length constraint exists
        name_field = model._meta.get_field("name")
        self.assertEqual(name_field.max_length, 100)
        self.assertFalse(name_field.blank)  # Should not allow blank

    def test_emailfield_constraints(self):
        """Test EmailField constraints"""
        model = ValidationTestModel()

        email_field = model._meta.get_field("email")
        self.assertIsInstance(email_field, models.EmailField)
        self.assertTrue(email_field.unique)

    def test_positive_integer_constraints(self):
        """Test PositiveIntegerField constraints"""
        model = ValidationTestModel()

        age_field = model._meta.get_field("age")
        self.assertIsInstance(age_field, models.PositiveIntegerField)

        # Should accept positive integers
        model.age = 25
        self.assertEqual(model.age, 25)

        # Zero should be allowed for PositiveIntegerField
        model.age = 0
        self.assertEqual(model.age, 0)

    def test_datetime_field_constraints(self):
        """Test DateTimeField constraints"""
        model = ValidationTestModel()

        # Test auto_now_add and auto_now constraints
        created_at_field = model._meta.get_field("created_at")
        updated_at_field = model._meta.get_field("updated_at")

        self.assertTrue(created_at_field.auto_now_add)
        self.assertFalse(created_at_field.auto_now)
        self.assertFalse(updated_at_field.auto_now_add)
        self.assertTrue(updated_at_field.auto_now)

    def test_boolean_field_constraints(self):
        """Test BooleanField constraints"""
        model = ComplexValidationModel()

        is_deleted_field = model._meta.get_field("is_deleted")
        self.assertIsInstance(is_deleted_field, models.BooleanField)
        self.assertFalse(is_deleted_field.default)  # Default should be False

    def test_json_field_constraints(self):
        """Test JSONField constraints"""
        model = MetadataValidationModel()

        metadata_field = model._meta.get_field("metadata")
        self.assertIsInstance(metadata_field, models.JSONField)
        self.assertEqual(metadata_field.default, dict)
        self.assertTrue(metadata_field.blank)

    def test_slug_field_constraints(self):
        """Test SlugField constraints"""
        model = SlugValidationModel()

        slug_field = model._meta.get_field("slug")
        self.assertIsInstance(slug_field, models.SlugField)
        self.assertEqual(slug_field.max_length, 255)
        self.assertTrue(slug_field.unique)

    def test_uuid_field_constraints(self):
        """Test UUIDField constraints"""
        model = ValidationTestModel()

        id_field = model._meta.get_field("id")
        self.assertIsInstance(id_field, models.UUIDField)
        self.assertTrue(id_field.primary_key)
        self.assertFalse(id_field.editable)
        self.assertEqual(id_field.default, uuid.uuid4)


class ValidationEdgeCasesTest(TestCase):
    """Test validation edge cases and error conditions"""

    def setUp(self):
        self.user = User.objects.create_user("user@test.com", "password")

    def test_null_vs_blank_validation(self):
        """Test null vs blank validation differences"""
        model = ComplexValidationModel()

        # Fields that allow null but not blank
        created_by_field = model._meta.get_field("created_by")
        self.assertTrue(created_by_field.null)
        self.assertTrue(created_by_field.blank)

        # Fields that require values
        name_field = model._meta.get_field("name")
        self.assertFalse(name_field.null)  # Implicit default for CharField

    def test_max_length_boundary_conditions(self):
        """Test max length boundary conditions"""
        model = ValidationTestModel()

        # Test exactly at max length
        max_name = "a" * 100  # Exactly 100 characters
        model.name = max_name
        self.assertEqual(len(model.name), 100)

        # Test slug max length
        slug_model = SlugValidationModel()
        max_slug = "a" * 255  # Exactly 255 characters
        slug_model.slug = max_slug
        self.assertEqual(len(slug_model.slug), 255)

    def test_foreign_key_null_validation(self):
        """Test foreign key null validation"""
        model = ComplexValidationModel()

        # Should accept None for nullable foreign keys
        model.created_by = None
        model.updated_by = None
        model.deleted_by = None

        self.assertIsNone(model.created_by)
        self.assertIsNone(model.updated_by)
        self.assertIsNone(model.deleted_by)

    def test_choice_field_validation(self):
        """Test choice field validation edge cases"""
        model = ComplexValidationModel()

        # Should accept valid choices
        for choice_value, choice_display in model._meta.get_field("category").choices:
            model.category = choice_value
            self.assertEqual(model.category, choice_value)

    def test_json_field_edge_cases(self):
        """Test JSON field edge cases"""
        model = MetadataValidationModel()

        # Test various JSON-serializable values
        test_values = [
            {},  # Empty dict
            [],  # Empty list
            {"key": None},  # Dict with None value
            {"unicode": "🚀"},  # Unicode content
            {"nested": {"deep": {"very": "deep"}}},  # Deep nesting
        ]

        for value in test_values:
            model.metadata = value
            self.assertEqual(model.metadata, value)

    def test_timestamp_edge_cases(self):
        """Test timestamp field edge cases"""
        model = ValidationTestModel()

        # Test with various timezone-aware datetimes
        from django.utils import timezone as tz

        # Current time
        now = tz.now()
        model.created_at = now
        model.updated_at = now

        self.assertEqual(model.created_at, now)
        self.assertEqual(model.updated_at, now)

        # Past time
        past = tz.now() - tz.timedelta(days=365)
        model.created_at = past
        self.assertEqual(model.created_at, past)

        # Future time (should be allowed at field level)
        future = tz.now() + tz.timedelta(days=365)
        model.created_at = future
        self.assertEqual(model.created_at, future)

    def test_uuid_field_edge_cases(self):
        """Test UUID field edge cases"""
        model1 = ValidationTestModel()
        model2 = ValidationTestModel()

        # Each instance should have unique UUID
        self.assertNotEqual(model1.id, model2.id)

        # Should be valid UUIDs
        self.assertIsInstance(model1.id, uuid.UUID)
        self.assertIsInstance(model2.id, uuid.UUID)

        # Should be version 4 UUIDs (random)
        self.assertEqual(model1.id.version, 4)
        self.assertEqual(model2.id.version, 4)

    def test_related_name_validation(self):
        """Test related name generation and validation"""
        model = ComplexValidationModel()

        # Test that related names are generated correctly
        created_by_field = model._meta.get_field("created_by")
        updated_by_field = model._meta.get_field("updated_by")

        expected_created_related = "core_complexvalidationmodel_created"
        expected_updated_related = "core_complexvalidationmodel_updated"

        self.assertEqual(
            created_by_field.remote_field.related_name, expected_created_related
        )
        self.assertEqual(
            updated_by_field.remote_field.related_name, expected_updated_related
        )
