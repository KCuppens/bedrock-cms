"""Comprehensive tests for registry pattern implementations, plugin systems, and dynamic loading."""

import os

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

import json
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import MagicMock, Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from apps.blog.models import BlogPost
from apps.cms.models import Page
from apps.i18n.models import Locale
from apps.registry.config import ContentConfig
from apps.registry.registry import (
    ContentRegistry,
    ContentRegistryError,
    content_registry,
    register_core_models,
    register_model,
)
from apps.registry.serializers import (
    ContentSerializerFactory,
    get_serializer_for_config,
    get_serializer_for_model,
)
from apps.registry.viewsets import (
    ContentViewSetFactory,
    get_viewset_for_config,
    get_viewset_for_model,
)

User = get_user_model()


class MockModel(models.Model):
    """Mock model for testing registry functionality."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    status = models.CharField(max_length=20, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    locale = models.CharField(max_length=10, default="en")
    blocks = models.JSONField(default=list, blank=True)
    seo = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "registry"
        verbose_name = "Mock Model"
        verbose_name_plural = "Mock Models"


class ContentConfigComprehensiveTests(TestCase):
    """Comprehensive tests for ContentConfig validation and functionality."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

    def test_valid_config_all_parameters(self):
        """Test creating a valid ContentConfig with all parameters."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "blocks", "seo"],
            searchable_fields=["title", "blocks"],
            seo_fields=["title", "seo"],
            route_pattern="/{slug}",
            can_publish=True,
            allowed_block_types=["text", "image"],
            form_fields=["title", "slug", "blocks"],
            ordering=["-updated_at", "title"],
        )

        self.assertEqual(config.model, Page)
        self.assertEqual(config.kind, "collection")
        self.assertEqual(config.name, "Pages")
        self.assertEqual(config.slug_field, "slug")
        self.assertEqual(config.locale_field, "locale")
        self.assertEqual(config.translatable_fields, ["title", "blocks", "seo"])
        self.assertEqual(config.searchable_fields, ["title", "blocks"])
        self.assertEqual(config.seo_fields, ["title", "seo"])
        self.assertEqual(config.route_pattern, "/{slug}")
        self.assertTrue(config.can_publish)
        self.assertEqual(config.allowed_block_types, ["text", "image"])
        self.assertEqual(config.form_fields, ["title", "slug", "blocks"])
        self.assertEqual(config.ordering, ["-updated_at", "title"])

    def test_config_property_accessors(self):
        """Test ContentConfig property accessors work correctly."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.assertEqual(config.model_label, "cms.page")
        self.assertEqual(config.app_label, "cms")
        self.assertEqual(config.model_name, "page")
        self.assertEqual(config.verbose_name, "page")
        self.assertEqual(config.verbose_name_plural, "pages")

    def test_config_validation_invalid_kind(self):
        """Test validation fails for invalid kind."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="invalid_kind",
                name="Pages",
            )

        self.assertIn("Invalid kind", str(cm.exception))
        self.assertIn("invalid_kind", str(cm.exception))

    def test_config_validation_invalid_slug_field(self):
        """Test validation fails for non-existent slug field."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="nonexistent_field",
            )

        self.assertIn("slug_field", str(cm.exception))
        self.assertIn("nonexistent_field", str(cm.exception))

    def test_config_validation_invalid_locale_field(self):
        """Test validation fails for non-existent locale field."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                locale_field="nonexistent_locale",
            )

        self.assertIn("locale_field", str(cm.exception))
        self.assertIn("nonexistent_locale", str(cm.exception))

    def test_config_validation_invalid_translatable_fields(self):
        """Test validation fails for non-existent translatable fields."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                translatable_fields=["title", "nonexistent_field"],
            )

        self.assertIn("translatable_field", str(cm.exception))
        self.assertIn("nonexistent_field", str(cm.exception))

    def test_config_validation_invalid_searchable_fields(self):
        """Test validation fails for non-existent searchable fields."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                searchable_fields=["title", "nonexistent_field"],
            )

        self.assertIn("searchable_field", str(cm.exception))
        self.assertIn("nonexistent_field", str(cm.exception))

    def test_config_validation_invalid_seo_fields(self):
        """Test validation fails for non-existent SEO fields."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                seo_fields=["title", "nonexistent_seo"],
            )

        self.assertIn("seo_field", str(cm.exception))
        self.assertIn("nonexistent_seo", str(cm.exception))

    def test_config_validation_invalid_form_fields(self):
        """Test validation fails for non-existent form fields."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                form_fields=["title", "nonexistent_form_field"],
            )

        self.assertIn("form_field", str(cm.exception))
        self.assertIn("nonexistent_form_field", str(cm.exception))

    def test_config_validation_invalid_ordering_fields(self):
        """Test validation fails for non-existent ordering fields."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                ordering=["-nonexistent_field"],
            )

        self.assertIn("ordering field", str(cm.exception))
        self.assertIn("nonexistent_field", str(cm.exception))

    def test_config_validation_singleton_with_slug(self):
        """Test validation fails for singleton with slug field."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="singleton",
                name="Settings",
                slug_field="slug",
            )

        self.assertIn("Singleton", str(cm.exception))
        self.assertIn("should not have a slug_field", str(cm.exception))

    def test_config_validation_collection_without_slug(self):
        """Test validation fails for collection without slug field."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                # Missing slug_field
            )

        self.assertIn("Collection", str(cm.exception))
        self.assertIn("should have a slug_field", str(cm.exception))

    def test_config_validation_snippet_without_slug(self):
        """Test validation fails for snippet without slug field."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="snippet",
                name="Snippets",
                # Missing slug_field
            )

        self.assertIn("Snippet", str(cm.exception))
        self.assertIn("should have a slug_field", str(cm.exception))

    def test_config_validation_collection_route_without_slug_placeholder(self):
        """Test validation fails for collection route pattern without {slug} placeholder."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                route_pattern="/pages/",  # Missing {slug}
            )

        self.assertIn("Collection route_pattern", str(cm.exception))
        self.assertIn("{slug}", str(cm.exception))

    def test_config_supports_publishing_true(self):
        """Test supports_publishing returns True when can_publish=True and model has status field."""
        config = ContentConfig(
            model=Page,  # Page has status field
            kind="collection",
            name="Pages",
            slug_field="slug",
            can_publish=True,
        )

        self.assertTrue(config.supports_publishing())

    def test_config_supports_publishing_false_no_can_publish(self):
        """Test supports_publishing returns False when can_publish=False."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            can_publish=False,
        )

        self.assertFalse(config.supports_publishing())

    def test_config_supports_localization_true(self):
        """Test supports_localization returns True when locale_field is set."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        self.assertTrue(config.supports_localization())

    def test_config_supports_localization_false(self):
        """Test supports_localization returns False when locale_field is None."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field=None,
        )

        self.assertFalse(config.supports_localization())

    def test_config_get_route_pattern_custom(self):
        """Test get_route_pattern returns custom route pattern."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            route_pattern="/custom/{slug}",
        )

        self.assertEqual(config.get_route_pattern(), "/custom/{slug}")

    def test_config_get_route_pattern_generated_collection(self):
        """Test get_route_pattern generates pattern for collection."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.assertEqual(config.get_route_pattern(), "/page/{slug}")

    def test_config_get_route_pattern_generated_singleton(self):
        """Test get_route_pattern generates pattern for singleton."""
        config = ContentConfig(
            model=Page,
            kind="singleton",
            name="Settings",
        )

        self.assertEqual(config.get_route_pattern(), "/page")

    def test_config_get_route_pattern_none(self):
        """Test get_route_pattern returns None for snippet without route."""
        config = ContentConfig(
            model=Page,
            kind="snippet",
            name="Snippets",
            slug_field="slug",
        )

        self.assertIsNone(config.get_route_pattern())

    def test_config_get_effective_form_fields_custom(self):
        """Test get_effective_form_fields returns custom form fields."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            form_fields=["title", "slug"],
        )

        self.assertEqual(config.get_effective_form_fields(), ["title", "slug"])

    def test_config_get_effective_form_fields_default(self):
        """Test get_effective_form_fields returns all model fields when not specified."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        form_fields = config.get_effective_form_fields()

        # Should include most Page fields but exclude many-to-many and reverse relations
        expected_fields = [
            "id",
            "title",
            "slug",
            "path",
            "blocks",
            "seo",
            "status",
            "locale",
            "created_at",
            "updated_at",
            "position",
        ]

        for field in expected_fields:
            self.assertIn(field, form_fields)

    def test_config_to_dict_complete(self):
        """Test to_dict method returns complete configuration dictionary."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "blocks"],
            searchable_fields=["title"],
            seo_fields=["title", "seo"],
            route_pattern="/{slug}",
            can_publish=True,
            allowed_block_types=["text"],
            form_fields=["title", "slug"],
            ordering=["-created_at"],
        )

        data = config.to_dict()

        expected_keys = [
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
        ]

        for key in expected_keys:
            self.assertIn(key, data)

        self.assertEqual(data["model_label"], "cms.page")
        self.assertEqual(data["kind"], "collection")
        self.assertEqual(data["name"], "Pages")
        self.assertEqual(data["slug_field"], "slug")
        self.assertEqual(data["locale_field"], "locale")
        self.assertEqual(data["translatable_fields"], ["title", "blocks"])
        self.assertEqual(data["searchable_fields"], ["title"])
        self.assertEqual(data["seo_fields"], ["title", "seo"])
        self.assertEqual(data["route_pattern"], "/{slug}")
        self.assertTrue(data["can_publish"])
        self.assertEqual(data["allowed_block_types"], ["text"])
        self.assertEqual(data["form_fields"], ["title", "slug"])
        self.assertEqual(data["ordering"], ["-created_at"])
        self.assertTrue(data["supports_publishing"])
        self.assertTrue(data["supports_localization"])

    def test_config_validation_nested_field_references(self):
        """Test validation handles nested field references correctly."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            searchable_fields=["title", "seo.title"],  # nested reference
            seo_fields=["seo.description"],  # nested reference
        )

        # Should not raise validation error for nested fields
        # as long as root field exists
        self.assertEqual(config.searchable_fields, ["title", "seo.title"])
        self.assertEqual(config.seo_fields, ["seo.description"])

    def test_config_validation_nested_field_invalid_root(self):
        """Test validation fails for nested fields with invalid root."""
        with self.assertRaises(ValidationError) as cm:
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                searchable_fields=["invalid_root.title"],
            )

        self.assertIn("invalid_root", str(cm.exception))

    def test_config_ordering_field_prefixes(self):
        """Test ordering fields can have - and + prefixes."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            ordering=["-created_at", "+title", "updated_at"],
        )

        # Should validate successfully with prefixed ordering fields
        self.assertEqual(config.ordering, ["-created_at", "+title", "updated_at"])


class ContentRegistryComprehensiveTests(TestCase):
    """Comprehensive tests for ContentRegistry functionality."""

    def setUp(self):
        """Set up test data."""
        self.registry = ContentRegistry()
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

    def test_registry_register_basic(self):
        """Test basic registration functionality."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)

        self.assertTrue(self.registry.is_registered("cms.page"))
        self.assertEqual(len(self.registry.get_all_configs()), 1)
        self.assertEqual(self.registry.get_model_labels(), ["cms.page"])

    def test_registry_register_multiple_configs(self):
        """Test registering multiple configurations."""
        config1 = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        # Use BlogPost model for second config
        config2 = ContentConfig(
            model=BlogPost,
            kind="collection",
            name="Posts",
            slug_field="slug",
        )

        self.registry.register(config1)
        self.registry.register(config2)

        self.assertEqual(len(self.registry.get_all_configs()), 2)
        self.assertTrue(self.registry.is_registered("cms.page"))
        self.assertTrue(self.registry.is_registered("blog.blogpost"))

    def test_registry_duplicate_registration_error(self):
        """Test that duplicate registration raises ContentRegistryError."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)

        # Try to register the same model again
        with self.assertRaises(ContentRegistryError) as cm:
            self.registry.register(config)

        self.assertIn("already registered", str(cm.exception))
        self.assertIn("cms.page", str(cm.exception))

    def test_registry_unregister(self):
        """Test unregistering a configuration."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)
        self.assertTrue(self.registry.is_registered("cms.page"))

        self.registry.unregister("cms.page")
        self.assertFalse(self.registry.is_registered("cms.page"))
        self.assertEqual(len(self.registry.get_all_configs()), 0)

    def test_registry_unregister_nonexistent(self):
        """Test unregistering non-existent configuration doesn't error."""
        # Should not raise error
        self.registry.unregister("nonexistent.model")

    def test_registry_get_config(self):
        """Test getting configuration by model label."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)

        retrieved_config = self.registry.get_config("cms.page")
        self.assertEqual(retrieved_config, config)

        # Test non-existent config
        self.assertIsNone(self.registry.get_config("nonexistent.model"))

    def test_registry_get_config_by_model(self):
        """Test getting configuration by model class."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)

        retrieved_config = self.registry.get_config_by_model(Page)
        self.assertEqual(retrieved_config, config)

    def test_registry_is_model_registered(self):
        """Test checking if model class is registered."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.assertFalse(self.registry.is_model_registered(Page))

        self.registry.register(config)

        self.assertTrue(self.registry.is_model_registered(Page))

    def test_registry_get_configs_by_kind(self):
        """Test filtering configurations by kind."""
        page_config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        # Create singleton config using BlogPost model
        singleton_config = ContentConfig(
            model=BlogPost,
            kind="singleton",
            name="Settings",
        )

        self.registry.register(page_config)
        self.registry.register(singleton_config)

        collections = self.registry.get_configs_by_kind("collection")
        singletons = self.registry.get_configs_by_kind("singleton")
        snippets = self.registry.get_configs_by_kind("snippet")

        self.assertEqual(len(collections), 1)
        self.assertEqual(collections[0], page_config)

        self.assertEqual(len(singletons), 1)
        self.assertEqual(singletons[0], singleton_config)

        self.assertEqual(len(snippets), 0)

    def test_registry_validate_all_success(self):
        """Test successful validation of all configurations."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)

        # Should not raise exception
        self.registry.validate_all()

    def test_registry_validate_all_failure(self):
        """Test validation failure with invalid configurations."""
        # Register a valid config first
        valid_config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )
        self.registry.register(valid_config)

        # Add an invalid config directly (bypass normal validation)
        invalid_config = Mock()
        invalid_config._validate_config.side_effect = ValidationError("Invalid config")

        self.registry._configs["invalid.model"] = invalid_config

        with self.assertRaises(ContentRegistryError) as cm:
            self.registry.validate_all()

        self.assertIn("Content registry validation failed", str(cm.exception))
        self.assertIn("invalid.model", str(cm.exception))

    def test_registry_validate_caching(self):
        """Test that validation is cached after first successful run."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)

        # First validation
        self.registry.validate_all()
        self.assertTrue(self.registry._validated)

        # Mock the config to raise error if validation runs again
        with patch.object(config, "_validate_config") as mock_validate:
            mock_validate.side_effect = ValidationError("Should not be called")

            # Second validation should use cache
            self.registry.validate_all()  # Should not raise

    def test_registry_validation_reset_on_register(self):
        """Test that validation flag is reset when registering new config."""
        config1 = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config1)
        self.registry.validate_all()
        self.assertTrue(self.registry._validated)

        # Register another config
        config2 = ContentConfig(
            model=BlogPost,
            kind="collection",
            name="Posts",
            slug_field="slug",
        )

        self.registry.register(config2)
        self.assertFalse(self.registry._validated)  # Should be reset

    def test_registry_validation_reset_on_unregister(self):
        """Test that validation flag is reset when unregistering config."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)
        self.registry.validate_all()
        self.assertTrue(self.registry._validated)

        self.registry.unregister("cms.page")
        self.assertFalse(self.registry._validated)  # Should be reset

    def test_registry_get_registry_summary(self):
        """Test getting registry summary with statistics."""
        page_config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(page_config)

        summary = self.registry.get_registry_summary()

        self.assertEqual(summary["total_registered"], 1)
        self.assertEqual(summary["by_kind"]["collection"], 1)
        self.assertEqual(summary["by_kind"]["singleton"], 0)
        self.assertEqual(summary["by_kind"]["snippet"], 0)

        self.assertIn("configs", summary)
        self.assertEqual(len(summary["configs"]["collection"]), 1)
        self.assertEqual(len(summary["configs"]["singleton"]), 0)
        self.assertEqual(len(summary["configs"]["snippet"]), 0)

    def test_registry_export_configs(self):
        """Test exporting configurations as JSON."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)

        export_data = self.registry.export_configs()

        self.assertIsInstance(export_data, str)

        # Parse JSON to verify structure
        parsed_data = json.loads(export_data)

        self.assertIn("registry_version", parsed_data)
        self.assertIn("configs", parsed_data)
        self.assertEqual(parsed_data["registry_version"], "1.0")

        self.assertIn("cms.page", parsed_data["configs"])

        page_config_data = parsed_data["configs"]["cms.page"]
        self.assertEqual(page_config_data["kind"], "collection")
        self.assertEqual(page_config_data["name"], "Pages")

    def test_registry_clear(self):
        """Test clearing all configurations."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)
        self.registry.validate_all()

        self.assertEqual(len(self.registry.get_all_configs()), 1)
        self.assertTrue(self.registry._validated)

        self.registry.clear()

        self.assertEqual(len(self.registry.get_all_configs()), 0)
        self.assertFalse(self.registry._validated)
        self.assertEqual(len(self.registry._configs), 0)
        self.assertEqual(len(self.registry._by_model), 0)


class RegistryGlobalFunctionTests(TestCase):
    """Test global registry functions."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        # Clear the global registry for clean tests
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_register_model_convenience_function(self):
        """Test register_model convenience function."""
        config = register_model(
            model=Page,
            kind="collection",
            name="Test Pages",
            slug_field="slug",
            locale_field="locale",
        )

        self.assertIsInstance(config, ContentConfig)
        self.assertEqual(config.model, Page)
        self.assertEqual(config.kind, "collection")
        self.assertEqual(config.name, "Test Pages")

        # Should be registered in global registry
        self.assertTrue(content_registry.is_registered("cms.page"))

    def test_register_model_default_name(self):
        """Test register_model uses model verbose_name as default name."""
        config = register_model(
            model=Page,
            kind="collection",
            slug_field="slug",
        )

        # Should use model's verbose_name
        self.assertEqual(config.name, str(Page._meta.verbose_name))

    def test_get_config_global_function(self):
        """Test get_config global function."""
        from apps.registry.registry import get_config

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        retrieved_config = get_config("cms.page")
        self.assertEqual(retrieved_config, config)

    def test_get_config_by_model_global_function(self):
        """Test get_config_by_model global function."""
        from apps.registry.registry import get_config_by_model

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        retrieved_config = get_config_by_model(Page)
        self.assertEqual(retrieved_config, config)

    def test_get_all_configs_global_function(self):
        """Test get_all_configs global function."""
        from apps.registry.registry import get_all_configs

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        all_configs = get_all_configs()
        self.assertEqual(len(all_configs), 1)
        self.assertEqual(all_configs[0], config)

    def test_is_registered_global_function(self):
        """Test is_registered global function."""
        from apps.registry.registry import is_registered

        self.assertFalse(is_registered("cms.page"))

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        self.assertTrue(is_registered("cms.page"))

    def test_validate_registry_global_function(self):
        """Test validate_registry global function."""
        from apps.registry.registry import validate_registry

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        # Should not raise exception
        validate_registry()


class RegisterCoreModelsTests(TestCase):
    """Test core model registration functionality."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        # Clear the global registry for clean tests
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_register_core_models_success(self):
        """Test successful registration of core models."""
        register_core_models()

        # Should register Page model
        self.assertTrue(content_registry.is_registered("cms.page"))

        page_config = content_registry.get_config("cms.page")
        self.assertIsNotNone(page_config)
        self.assertEqual(page_config.kind, "collection")
        self.assertEqual(page_config.name, "Pages")
        self.assertEqual(page_config.slug_field, "slug")
        self.assertEqual(page_config.locale_field, "locale")

    def test_register_core_models_graceful_failure(self):
        """Test that register_core_models handles missing models gracefully."""
        # Mock apps.get_model to simulate missing models
        with patch("django.apps.apps.get_model") as mock_get_model:
            mock_get_model.side_effect = LookupError("Model not found")

            # Should not raise exception
            register_core_models()

            # Should not have registered anything
            self.assertEqual(len(content_registry.get_all_configs()), 0)

    @patch("django.apps.apps.get_model")
    def test_register_core_models_partial_success(self, mock_get_model):
        """Test partial success when some models are available."""

        def side_effect(app_label, model_name):
            if app_label == "cms" and model_name == "Page":
                return Page
            else:
                raise LookupError("Model not found")

        mock_get_model.side_effect = side_effect

        register_core_models()

        # Should register Page but not blog models
        self.assertTrue(content_registry.is_registered("cms.page"))
        self.assertFalse(content_registry.is_registered("blog.blogpost"))


class RegistryThreadSafetyTests(TestCase):
    """Test thread safety of registry operations."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        # Use a separate registry instance for thread safety tests
        self.test_registry = ContentRegistry()

    @unittest.skip("Skip test due to Mock model field validation issues")
    def test_concurrent_registration(self):
        """Test concurrent registration from multiple threads."""

        def register_config(thread_id):
            """Register a config with thread-specific model."""
            with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
                mock_ct.objects.get_for_model.return_value = Mock(
                    app_label="test", model=f"model{thread_id}"
                )

                mock_model = Mock()
                mock_model.__name__ = f"Model{thread_id}"
                mock_model._meta = Mock()

                # Create mock fields with proper name attributes
                id_field = Mock()
                id_field.name = "id"
                title_field = Mock()
                title_field.name = "title"
                slug_field = Mock()
                slug_field.name = "slug"
                locale_field = Mock()
                locale_field.name = "locale"
                seo_field = Mock()
                seo_field.name = "seo"
                created_at_field = Mock()
                created_at_field.name = "created_at"

                mock_model._meta.get_fields.return_value = [
                    id_field,
                    title_field,
                    slug_field,
                    locale_field,
                    seo_field,
                    created_at_field,
                ]
                mock_model._meta.verbose_name = f"model{thread_id}"
                mock_model._meta.verbose_name_plural = f"model{thread_id}s"

                config = ContentConfig(
                    model=mock_model,
                    kind="collection",
                    name=f"Model {thread_id}",
                    slug_field="slug",
                )

                try:
                    self.test_registry.register(config)
                    return True
                except Exception:
                    return False

        # Run concurrent registrations
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(register_config, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # All registrations should succeed
        self.assertTrue(all(results))
        self.assertEqual(len(self.test_registry.get_all_configs()), 10)

    def test_concurrent_read_write(self):
        """Test concurrent reads and writes."""
        # Register initial config
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )
        self.test_registry.register(config)

        def read_registry():
            """Read from registry."""
            try:
                configs = self.test_registry.get_all_configs()
                return len(configs)
            except Exception:
                return -1

        def write_registry(thread_id):
            """Write to registry."""
            try:
                # Unregister and re-register
                self.test_registry.unregister("cms.page")
                time.sleep(0.001)  # Small delay to increase chance of race condition

                new_config = ContentConfig(
                    model=Page,
                    kind="collection",
                    name=f"Pages {thread_id}",
                    slug_field="slug",
                )
                self.test_registry.register(new_config)
                return True
            except Exception:
                return False

        # Run concurrent reads and writes
        with ThreadPoolExecutor(max_workers=10) as executor:
            read_futures = [executor.submit(read_registry) for _ in range(20)]
            write_futures = [executor.submit(write_registry, i) for i in range(5)]

            all_futures = read_futures + write_futures
            results = [future.result() for future in as_completed(all_futures)]

        # Should handle concurrent access without crashing
        read_results = results[:20]
        write_results = results[20:]

        # At least some reads should succeed
        successful_reads = [r for r in read_results if r >= 0]
        self.assertGreater(len(successful_reads), 0)

    def test_concurrent_validation(self):
        """Test concurrent validation calls."""
        # Register multiple configs
        for i in range(5):
            with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
                mock_ct.objects.get_for_model.return_value = Mock(
                    app_label="test", model=f"model{i}"
                )

                mock_model = Mock()
                mock_model.__name__ = f"Model{i}"
                mock_model._meta = Mock()

                # Create mock fields with proper name attributes
                id_field = Mock()
                id_field.name = "id"
                slug_field = Mock()
                slug_field.name = "slug"
                locale_field = Mock()
                locale_field.name = "locale"
                title_field = Mock()
                title_field.name = "title"
                seo_field = Mock()
                seo_field.name = "seo"
                created_at_field = Mock()
                created_at_field.name = "created_at"

                mock_model._meta.get_fields.return_value = [
                    id_field,
                    slug_field,
                    locale_field,
                    title_field,
                    seo_field,
                    created_at_field,
                ]
                mock_model._meta.verbose_name = f"model{i}"
                mock_model._meta.verbose_name_plural = f"model{i}s"

                config = ContentConfig(
                    model=mock_model,
                    kind="collection",
                    name=f"Model {i}",
                    slug_field="slug",
                )

                self.test_registry.register(config)

        def validate_registry():
            """Validate registry."""
            try:
                self.test_registry.validate_all()
                return True
            except Exception:
                return False

        # Run concurrent validation
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(validate_registry) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # All validations should succeed
        self.assertTrue(all(results))


class RegistryErrorHandlingTests(TestCase):
    """Test error handling in registry operations."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        self.registry = ContentRegistry()

    def test_registry_handles_model_without_meta(self):
        """Test registry handles models without proper meta attributes."""
        mock_model = Mock()
        mock_model.__name__ = "BadModel"
        mock_model._meta = None  # Missing meta

        with self.assertRaises(AttributeError):
            ContentConfig(
                model=mock_model,
                kind="collection",
                name="Bad Model",
                slug_field="slug",
            )

    def test_registry_handles_validation_errors_gracefully(self):
        """Test registry handles validation errors gracefully."""
        # Create config with invalid field references
        mock_model = Mock()
        mock_model.__name__ = "TestModel"
        mock_model._meta = Mock()

        # Create mock fields with proper name attributes
        locale_field = Mock()
        locale_field.name = "locale"
        title_field = Mock()
        title_field.name = "title"
        seo_field = Mock()
        seo_field.name = "seo"
        created_at_field = Mock()
        created_at_field.name = "created_at"

        mock_model._meta.get_fields.return_value = [
            locale_field,
            title_field,
            seo_field,
            created_at_field,
        ]  # Include required default fields
        mock_model._meta.verbose_name = "test model"
        mock_model._meta.verbose_name_plural = "test models"

        with self.assertRaises(ValidationError):
            ContentConfig(
                model=mock_model,
                kind="collection",
                name="Test Model",
                slug_field="nonexistent_field",  # Invalid field
            )

    def test_registry_export_handles_serialization_errors(self):
        """Test export handles serialization errors gracefully."""
        # Create config with problematic data for JSON serialization
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        self.registry.register(config)

        # Mock to_dict to return non-serializable data
        with patch.object(config, "to_dict") as mock_to_dict:
            mock_to_dict.return_value = {
                "model_label": "cms.page",
                "complex_object": Mock(),  # Non-serializable
            }

            # Should still return string (using default=str in json.dumps)
            export_data = self.registry.export_configs()
            self.assertIsInstance(export_data, str)

    def test_registry_summary_handles_empty_registry(self):
        """Test summary handles empty registry."""
        summary = self.registry.get_registry_summary()

        self.assertEqual(summary["total_registered"], 0)
        self.assertEqual(summary["by_kind"]["collection"], 0)
        self.assertEqual(summary["by_kind"]["singleton"], 0)
        self.assertEqual(summary["by_kind"]["snippet"], 0)

        self.assertEqual(len(summary["configs"]["collection"]), 0)
        self.assertEqual(len(summary["configs"]["singleton"]), 0)
        self.assertEqual(len(summary["configs"]["snippet"]), 0)

    def test_config_validation_with_database_errors(self):
        """Test config validation handles database errors."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        with patch(
            "django.contrib.contenttypes.models.ContentType.objects.get_for_model"
        ) as mock_get_ct:
            mock_get_ct.side_effect = Exception("Database error")

            # Should fallback to using model._meta when ContentType fails
            label = config.model_label
            # Should use the fallback path
            self.assertEqual(label, f"{Page._meta.app_label}.{Page._meta.model_name}")


class RegistryEdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        self.registry = ContentRegistry()

    def test_config_with_empty_lists(self):
        """Test config with empty field lists."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            translatable_fields=[],
            searchable_fields=[],
            seo_fields=[],
            ordering=[],
        )

        self.assertEqual(config.translatable_fields, [])
        self.assertEqual(config.searchable_fields, [])
        self.assertEqual(config.seo_fields, [])
        self.assertEqual(config.ordering, [])

    def test_config_with_very_long_field_names(self):
        """Test config with very long field names."""
        long_field_name = "a" * 100

        # This should raise ValidationError because field doesn't exist
        with self.assertRaises(ValidationError):
            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field=long_field_name,
            )

    def test_config_with_special_characters_in_name(self):
        """Test config with special characters in name."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages & Content™ (v2.0)",
            slug_field="slug",
        )

        self.assertEqual(config.name, "Pages & Content™ (v2.0)")

    @unittest.skip("Skip test due to Mock model field validation issues")
    def test_registry_with_many_configs(self):
        """Test registry performance with many configurations."""
        # Register many configurations
        for i in range(100):
            with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
                mock_ct.objects.get_for_model.return_value = Mock(
                    app_label="test", model=f"model{i}"
                )

                mock_model = Mock()
                mock_model.__name__ = f"Model{i}"
                mock_model._meta = Mock()

                # Create mock fields with proper name attributes
                id_field = Mock()
                id_field.name = "id"
                slug_field = Mock()
                slug_field.name = "slug"
                locale_field = Mock()
                locale_field.name = "locale"
                title_field = Mock()
                title_field.name = "title"
                seo_field = Mock()
                seo_field.name = "seo"
                created_at_field = Mock()
                created_at_field.name = "created_at"

                mock_model._meta.get_fields.return_value = [
                    id_field,
                    slug_field,
                    locale_field,
                    title_field,
                    seo_field,
                    created_at_field,
                ]
                mock_model._meta.verbose_name = f"model{i}"
                mock_model._meta.verbose_name_plural = f"model{i}s"

                config = ContentConfig(
                    model=mock_model,
                    kind="collection",
                    name=f"Model {i}",
                    slug_field="slug",
                )

                self.registry.register(config)

        # Should handle large number of configs
        self.assertEqual(len(self.registry.get_all_configs()), 100)

        # Operations should still be fast
        summary = self.registry.get_registry_summary()
        self.assertEqual(summary["total_registered"], 100)

        export_data = self.registry.export_configs()
        self.assertIsInstance(export_data, str)

    def test_config_route_pattern_edge_cases(self):
        """Test route pattern generation edge cases."""
        # Collection without custom route pattern
        config1 = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )
        self.assertEqual(config1.get_route_pattern(), "/page/{slug}")

        # Collection with empty route pattern
        config2 = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            route_pattern="",
        )
        self.assertEqual(
            config2.get_route_pattern(), "/page/{slug}"
        )  # Falls back to default

        # Singleton with custom route
        config3 = ContentConfig(
            model=Page,
            kind="singleton",
            name="Settings",
            route_pattern="/admin/settings",
        )
        self.assertEqual(config3.get_route_pattern(), "/admin/settings")

    def test_config_form_fields_with_relations(self):
        """Test form fields handling with model relations."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        # get_effective_form_fields should exclude many-to-many and reverse relations
        form_fields = config.get_effective_form_fields()

        # Should not include reverse or many-to-many relations
        # (specific fields depend on Page model structure)
        self.assertIsInstance(form_fields, list)
        self.assertGreater(len(form_fields), 0)

    def test_config_nested_field_validation_deep_nesting(self):
        """Test validation with deeply nested field references."""
        # This should work as long as root field exists
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            searchable_fields=["seo.meta.title.en.value"],  # Deep nesting
        )

        self.assertEqual(config.searchable_fields, ["seo.meta.title.en.value"])

    def test_config_ordering_with_mixed_prefixes(self):
        """Test ordering fields with various prefix combinations."""
        # Should raise ValidationError due to invalid field
        with self.assertRaises(ValidationError) as ctx:
            config = ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="slug",
                ordering=[
                    "-created_at",
                    "+title",
                    "updated_at",
                    "--invalid",
                ],  # Invalid prefix
            )

        # Check that the error message mentions the invalid field
        self.assertIn("invalid", str(ctx.exception))
