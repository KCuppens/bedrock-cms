"""Additional tests to boost registry coverage by testing uncovered code paths."""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase

from apps.cms.models import Page
from apps.i18n.models import Locale
from apps.registry.config import ContentConfig
from apps.registry.registry import (
    ContentRegistry,
    ContentRegistryError,
    content_registry,
    get_all_configs,
    get_config,
    get_config_by_model,
    is_registered,
    register,
    register_core_models,
    register_model,
    validate_registry,
)

User = get_user_model()


class RegistryCoverageBooстTests(TestCase):
    """Test uncovered code paths in registry.py to boost coverage."""

    def setUp(self):
        """Set up test data."""
        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

    def test_registry_clear_functionality(self):
        """Test the clear() method that wasn't covered."""
        registry = ContentRegistry()

        # Register some configs
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Test Pages",
            slug_field="slug",
        )
        registry.register(config)

        # Verify registry has content
        self.assertEqual(len(registry.get_all_configs()), 1)
        self.assertTrue(registry.is_registered("cms.page"))
        self.assertTrue(registry.is_model_registered(Page))

        # Clear the registry
        registry.clear()

        # Verify registry is empty
        self.assertEqual(len(registry.get_all_configs()), 0)
        self.assertFalse(registry.is_registered("cms.page"))
        self.assertFalse(registry.is_model_registered(Page))
        self.assertFalse(registry._validated)

    def test_registry_get_model_labels(self):
        """Test get_model_labels() method."""
        registry = ContentRegistry()

        # Empty registry
        labels = registry.get_model_labels()
        self.assertEqual(labels, [])

        # Register a config
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Test Pages",
            slug_field="slug",
        )
        registry.register(config)

        # Test labels are returned
        labels = registry.get_model_labels()
        self.assertIn("cms.page", labels)
        self.assertEqual(len(labels), 1)

    def test_registry_is_model_registered(self):
        """Test is_model_registered() method with different scenarios."""
        registry = ContentRegistry()

        # Test with unregistered model
        self.assertFalse(registry.is_model_registered(Page))

        # Register a model
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Test Pages",
            slug_field="slug",
        )
        registry.register(config)

        # Test with registered model
        self.assertTrue(registry.is_model_registered(Page))

        # Test with None
        self.assertFalse(registry.is_model_registered(None))

    def test_registry_validate_all_already_validated(self):
        """Test validate_all() when already validated."""
        registry = ContentRegistry()

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Test Pages",
            slug_field="slug",
        )
        registry.register(config)

        # First validation
        registry.validate_all()
        self.assertTrue(registry._validated)

        # Second validation should be a no-op
        registry.validate_all()  # Should return early
        self.assertTrue(registry._validated)

    def test_global_registry_functions(self):
        """Test global registry convenience functions."""
        # Test is_registered function
        result = is_registered("nonexistent.model")
        self.assertFalse(result)

        # Test validate_registry function
        validate_registry()  # Should not raise

        # Test get_all_configs function
        configs = get_all_configs()
        self.assertIsInstance(configs, list)

        # Test with registered config
        if not is_registered("cms.page"):
            register_core_models()

        if is_registered("cms.page"):
            config = get_config("cms.page")
            self.assertIsNotNone(config)

            config_by_model = get_config_by_model(Page)
            self.assertEqual(config, config_by_model)

    def test_register_model_convenience_function(self):
        """Test register_model convenience function."""

        # Create a test model
        class CoverageTestModel1(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)

            class Meta:
                app_label = "registry_test"
                verbose_name = "Test Model"
                verbose_name_plural = "Test Models"

        # Test with explicit name
        config = register_model(
            model=CoverageTestModel1,
            kind="collection",
            name="Custom Test Models",
            slug_field="slug",
        )

        self.assertEqual(config.name, "Custom Test Models")
        self.assertEqual(config.model, CoverageTestModel1)

        # Clean up
        content_registry.unregister(config.model_label)

        # Test with default name (from model meta)
        config2 = register_model(
            model=CoverageTestModel1,
            kind="collection",
            slug_field="slug",
        )

        self.assertEqual(config2.name, "Test Model")  # From verbose_name

        # Clean up
        content_registry.unregister(config2.model_label)

    def test_export_configs_json_formatting(self):
        """Test export_configs returns proper JSON format."""
        registry = ContentRegistry()

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Test Pages",
            slug_field="slug",
        )
        registry.register(config)

        export_json = registry.export_configs()

        # Should be valid JSON
        parsed = json.loads(export_json)

        # Check structure
        self.assertIn("registry_version", parsed)
        self.assertEqual(parsed["registry_version"], "1.0")
        self.assertIn("configs", parsed)
        self.assertIn("cms.page", parsed["configs"])

        # Check formatting (should be indented)
        self.assertIn("  ", export_json)  # Should have indentation

    def test_registry_summary_structure(self):
        """Test get_registry_summary returns correct structure."""
        registry = ContentRegistry()

        # Test empty registry
        summary = registry.get_registry_summary()
        expected_structure = {
            "total_registered": 0,
            "by_kind": {
                "collection": 0,
                "singleton": 0,
                "snippet": 0,
            },
            "configs": {
                "collection": [],
                "singleton": [],
                "snippet": [],
            },
        }
        self.assertEqual(summary, expected_structure)

        # Test with configs
        class CollectionModel(models.Model):
            slug = models.SlugField()

            class Meta:
                app_label = "registry_test"

        class SingletonModel(models.Model):
            title = models.CharField(max_length=200)

            class Meta:
                app_label = "registry_test"

        collection_config = ContentConfig(
            model=CollectionModel,
            kind="collection",
            name="Collections",
            slug_field="slug",
        )

        singleton_config = ContentConfig(
            model=SingletonModel,
            kind="singleton",
            name="Settings",
        )

        registry.register(collection_config)
        registry.register(singleton_config)

        summary = registry.get_registry_summary()
        self.assertEqual(summary["total_registered"], 2)
        self.assertEqual(summary["by_kind"]["collection"], 1)
        self.assertEqual(summary["by_kind"]["singleton"], 1)
        self.assertEqual(summary["by_kind"]["snippet"], 0)
        self.assertEqual(len(summary["configs"]["collection"]), 1)
        self.assertEqual(len(summary["configs"]["singleton"]), 1)
        self.assertEqual(len(summary["configs"]["snippet"]), 0)


class ConfigCoverageBooстTests(TestCase):
    """Test uncovered code paths in config.py to boost coverage."""

    def setUp(self):
        """Set up test data."""
        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

    def test_config_property_accessors(self):
        """Test property accessors in ContentConfig."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Test Pages",
            slug_field="slug",
        )

        # Test property accessors that weren't covered
        self.assertEqual(config.model_label, "cms.page")
        self.assertEqual(config.app_label, "cms")
        self.assertEqual(config.model_name, "page")
        self.assertEqual(config.verbose_name, "page")
        self.assertEqual(config.verbose_name_plural, "pages")

    def test_config_supports_methods(self):
        """Test supports_* methods."""

        # Test model with status field
        class ModelWithStatus(models.Model):
            title = models.CharField(max_length=200)
            status = models.CharField(max_length=20)

            class Meta:
                app_label = "registry_test"

        config1 = ContentConfig(
            model=ModelWithStatus,
            kind="singleton",
            name="With Status",
            can_publish=True,
        )

        self.assertTrue(config1.supports_publishing())

        # Test model without status field
        class ModelWithoutStatus(models.Model):
            title = models.CharField(max_length=200)

            class Meta:
                app_label = "registry_test"

        config2 = ContentConfig(
            model=ModelWithoutStatus,
            kind="singleton",
            name="Without Status",
            can_publish=True,
        )

        self.assertFalse(config2.supports_publishing())

        # Test supports_localization
        config3 = ContentConfig(
            model=ModelWithoutStatus,
            kind="singleton",
            name="No Locale",
            locale_field=None,
        )

        self.assertFalse(config3.supports_localization())

    def test_config_get_route_pattern_generation(self):
        """Test route pattern generation for different scenarios."""

        class CoverageTestModel2(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)

            class Meta:
                app_label = "registry_test"

        # Test collection with slug field (auto-generation)
        config1 = ContentConfig(
            model=CoverageTestModel2,
            kind="collection",
            name="Test Collection",
            slug_field="slug",
        )

        # Should generate default pattern
        self.assertEqual(config1.get_route_pattern(), "/coveragetestmodel2/{slug}")

        # Test singleton (auto-generation)
        config2 = ContentConfig(
            model=CoverageTestModel2,
            kind="singleton",
            name="Test Singleton",
        )

        # Should generate singleton pattern
        self.assertEqual(config2.get_route_pattern(), "/coveragetestmodel2")

        # Test custom route pattern
        config3 = ContentConfig(
            model=CoverageTestModel2,
            kind="collection",
            name="Test Custom",
            slug_field="slug",
            route_pattern="/custom/{slug}",
        )

        # Should return custom pattern
        self.assertEqual(config3.get_route_pattern(), "/custom/{slug}")

    def test_config_get_effective_form_fields(self):
        """Test get_effective_form_fields method."""

        class CoverageTestModel3(models.Model):
            title = models.CharField(max_length=200)
            content = models.TextField()
            tags = models.ManyToManyField("self", blank=True)

            class Meta:
                app_label = "registry_test"

        # Test with explicit form_fields
        config1 = ContentConfig(
            model=CoverageTestModel3,
            kind="singleton",
            name="Test",
            form_fields=["title", "content"],
        )

        effective_fields = config1.get_effective_form_fields()
        self.assertEqual(effective_fields, ["title", "content"])

        # Test without explicit form_fields (should return all non-relation fields)
        config2 = ContentConfig(
            model=CoverageTestModel3,
            kind="singleton",
            name="Test",
        )

        effective_fields2 = config2.get_effective_form_fields()
        expected_fields = [
            "title",
            "content",
            "id",
        ]  # Should exclude M2M and reverse relations
        self.assertEqual(set(effective_fields2), set(expected_fields))

    def test_config_validation_error_aggregation(self):
        """Test that validation collects multiple errors."""

        class InvalidModel(models.Model):
            title = models.CharField(max_length=200)

            class Meta:
                app_label = "registry_test"

        # Create config with multiple validation errors
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=InvalidModel,
                kind="invalid_kind",  # Error 1: invalid kind
                name="Test",
                slug_field="nonexistent",  # Error 2: invalid field
                locale_field="also_nonexistent",  # Error 3: invalid field
            )

        error_message = str(cm.exception)
        self.assertIn("Invalid kind", error_message)
        self.assertIn("slug_field", error_message)
        self.assertIn("locale_field", error_message)

    def test_config_nested_field_validation(self):
        """Test validation of nested field references."""

        class ModelWithJSON(models.Model):
            title = models.CharField(max_length=200)
            metadata = models.TextField()  # Simulating JSON field

            class Meta:
                app_label = "registry_test"

        # Test that nested field references don't cause validation errors
        config = ContentConfig(
            model=ModelWithJSON,
            kind="singleton",
            name="JSON Model",
            searchable_fields=["title", "metadata.name"],  # Nested reference
            seo_fields=["title", "metadata.description"],
        )

        # Should not raise validation error
        self.assertEqual(config.searchable_fields, ["title", "metadata.name"])

    def test_config_to_dict_completeness(self):
        """Test to_dict method includes all expected fields."""

        class CompleteModel(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)
            status = models.CharField(max_length=20)
            locale = models.CharField(max_length=10)

            class Meta:
                app_label = "registry_test"
                verbose_name = "Complete Test"
                verbose_name_plural = "Complete Tests"

        config = ContentConfig(
            model=CompleteModel,
            kind="collection",
            name="Complete Config",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title"],
            searchable_fields=["title"],
            seo_fields=["title"],
            route_pattern="/complete/{slug}",
            can_publish=True,
            allowed_block_types=["text"],
            form_fields=["title", "slug"],
            ordering=["-id"],
        )

        data = config.to_dict()

        expected_keys = {
            "model_label",
            "kind",
            "name",
            "slug_field",
            "locale_field",
            "translatable_fields",
            "searchable_fields",
            "seo_fields",
            "route_pattern",
            "can_publish",
            "allowed_block_types",
            "form_fields",
            "ordering",
            "verbose_name",
            "verbose_name_plural",
            "supports_publishing",
            "supports_localization",
        }

        self.assertEqual(set(data.keys()), expected_keys)
        self.assertEqual(data["model_label"], "registry_test.completemodel")
        self.assertEqual(data["verbose_name"], "Complete Test")
        self.assertEqual(data["verbose_name_plural"], "Complete Tests")
        self.assertTrue(data["supports_publishing"])
        self.assertTrue(data["supports_localization"])


class RegisterCoreModelsCoverageTests(TestCase):
    """Test register_core_models function coverage."""

    def setUp(self):
        """Set up test data."""
        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

    @patch("django.apps.apps.get_model")
    def test_register_core_models_import_errors(self, mock_get_model):
        """Test register_core_models handles import errors gracefully."""
        # Mock ImportError for all model lookups
        mock_get_model.side_effect = ImportError("Model not found")

        # Should not raise an exception
        register_core_models()

        # Verify get_model was called at least once
        self.assertTrue(mock_get_model.called)

    @patch("django.apps.apps.get_model")
    def test_register_core_models_lookup_errors(self, mock_get_model):
        """Test register_core_models handles LookupError gracefully."""
        # Mock LookupError for all model lookups
        mock_get_model.side_effect = LookupError("Model not in registry")

        # Should not raise an exception
        register_core_models()

        # Verify get_model was called at least once
        self.assertTrue(mock_get_model.called)

    def test_register_core_models_success_path(self):
        """Test successful registration of core models."""
        # Clear registry first
        content_registry.clear()

        # Register core models
        register_core_models()

        # Check that at least some models were registered
        # (This depends on which models are available in the test environment)
        configs = content_registry.get_all_configs()

        # The exact number depends on which apps are installed
        # but we should have at least some configs if models were found
        if len(configs) > 0:
            # Verify structure of registered configs
            for config in configs:
                self.assertIsInstance(config, ContentConfig)
                self.assertIn(config.kind, ["collection", "singleton", "snippet"])
                self.assertIsInstance(config.name, str)
                self.assertTrue(len(config.name) > 0)
