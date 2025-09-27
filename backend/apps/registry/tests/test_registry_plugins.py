"""Tests for registry plugin discovery patterns, dynamic loading, and complex validation scenarios."""

import importlib
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, Mock, patch

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase, override_settings
from django.test.utils import isolate_apps

from apps.cms.models import Page
from apps.i18n.models import Locale
from apps.registry.config import ContentConfig
from apps.registry.registry import (
    ContentRegistry,
    ContentRegistryError,
    content_registry,
    register,
    register_core_models,
    register_model,
)


class PluginDiscoveryTests(TestCase):
    """Test plugin discovery and dynamic loading patterns."""

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

    def test_dynamic_model_registration_from_apps(self):
        """Test dynamically registering models from Django apps."""
        # Mock a new app with models
        mock_app_config = Mock()
        mock_app_config.name = "test_plugin"
        mock_app_config.label = "test_plugin"

        # Create a mock model
        class PluginModel(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)
            content = models.TextField()

            class Meta:
                app_label = "test_plugin"
                verbose_name = "Plugin Model"
                verbose_name_plural = "Plugin Models"

        # Mock the apps.get_models() to return our plugin model
        with patch.object(apps, "get_models") as mock_get_models:
            mock_get_models.return_value = [PluginModel]

            # Mock apps.get_app_configs() to include our test app
            with patch.object(apps, "get_app_configs") as mock_get_app_configs:
                mock_get_app_configs.return_value = [mock_app_config]

                # Function to discover and register models from apps
                def discover_and_register_models():
                    """Discover models from all apps and register them."""
                    registry = ContentRegistry()

                    for app_config in apps.get_app_configs():
                        if app_config.name.startswith("test_"):
                            for model in apps.get_models(app_config):
                                if hasattr(model, "_meta"):
                                    # Auto-determine configuration based on model fields
                                    has_slug = any(
                                        field.name == "slug"
                                        for field in model._meta.get_fields()
                                    )
                                    has_status = any(
                                        field.name == "status"
                                        for field in model._meta.get_fields()
                                    )

                                    kind = "collection" if has_slug else "singleton"
                                    slug_field = "slug" if has_slug else None

                                    config = ContentConfig(
                                        model=model,
                                        kind=kind,
                                        name=model._meta.verbose_name_plural
                                        or model._meta.verbose_name,
                                        slug_field=slug_field,
                                        can_publish=has_status,
                                    )
                                    registry.register(config)

                    return registry

                # Test the discovery process
                registry = discover_and_register_models()

                # Verify the plugin model was registered
                self.assertEqual(len(registry.get_all_configs()), 1)
                config = registry.get_config("test_plugin.pluginmodel")
                self.assertIsNotNone(config)
                self.assertEqual(config.name, "Plugin Models")
                self.assertEqual(config.kind, "collection")
                self.assertEqual(config.slug_field, "slug")

    def test_plugin_registration_with_decorators(self):
        """Test plugin registration using decorator pattern."""
        registry = ContentRegistry()

        def register_content(kind, **kwargs):
            """Decorator for registering content models."""

            def decorator(model_class):
                config = ContentConfig(
                    model=model_class,
                    kind=kind,
                    name=kwargs.get("name", model_class._meta.verbose_name),
                    **{k: v for k, v in kwargs.items() if k != "name"},
                )
                registry.register(config)
                return model_class

            return decorator

        # Use decorator to register model
        @register_content(
            kind="collection",
            name="Decorated Articles",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "content"],
            searchable_fields=["title", "content"],
        )
        class DecoratedArticle(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)
            content = models.TextField()
            locale = models.CharField(max_length=10)

            class Meta:
                app_label = "test_plugin"
                verbose_name = "Decorated Article"

        # Verify registration worked
        self.assertEqual(len(registry.get_all_configs()), 1)
        config = registry.get_config("test_plugin.decoratedarticle")
        self.assertIsNotNone(config)
        self.assertEqual(config.name, "Decorated Articles")

    def test_plugin_metadata_extraction(self):
        """Test extracting metadata from plugin models for auto-configuration."""

        class SmartPluginModel(models.Model):
            # Standard CMS fields
            title = models.CharField(max_length=200, verbose_name="Title")
            slug = models.SlugField(unique=True, verbose_name="URL Slug")
            content = models.TextField(verbose_name="Main Content")
            excerpt = models.TextField(blank=True, verbose_name="Excerpt")

            # Publishing fields
            status = models.CharField(max_length=20, default="draft")
            published_at = models.DateTimeField(null=True, blank=True)

            # Localization
            locale = models.CharField(max_length=10, default="en")

            # SEO fields
            seo_title = models.CharField(max_length=200, blank=True)
            seo_description = models.TextField(blank=True)

            # Metadata fields
            tags = models.TextField(blank=True)  # JSON field
            featured_image = models.TextField(blank=True)  # Image URL

            # Timestamps
            created_at = models.DateTimeField(auto_now_add=True)
            updated_at = models.DateTimeField(auto_now=True)

            class Meta:
                app_label = "test_plugin"
                verbose_name = "Smart Plugin"
                verbose_name_plural = "Smart Plugins"

        def extract_config_from_model(model_class):
            """Extract configuration from model metadata."""
            field_names = [field.name for field in model_class._meta.get_fields()]

            # Determine kind based on fields
            has_slug = "slug" in field_names
            kind = "collection" if has_slug else "singleton"

            # Extract translatable fields (text fields)
            translatable_fields = []
            searchable_fields = []
            seo_fields = []

            for field in model_class._meta.get_fields():
                if isinstance(field, (models.CharField, models.TextField)):
                    if "seo" in field.name.lower():
                        seo_fields.append(field.name)
                    elif field.name in ["title", "content", "excerpt", "description"]:
                        translatable_fields.append(field.name)
                        searchable_fields.append(field.name)
                    elif field.name in ["tags"]:
                        searchable_fields.append(field.name)

            # Determine ordering
            ordering = []
            if "published_at" in field_names:
                ordering.append("-published_at")
            elif "created_at" in field_names:
                ordering.append("-created_at")

            if "title" in field_names:
                ordering.append("title")

            return ContentConfig(
                model=model_class,
                kind=kind,
                name=model_class._meta.verbose_name_plural,
                slug_field="slug" if has_slug else None,
                locale_field="locale" if "locale" in field_names else None,
                translatable_fields=translatable_fields,
                searchable_fields=searchable_fields,
                seo_fields=seo_fields or ["title"],
                can_publish="status" in field_names,
                ordering=ordering,
            )

        # Test metadata extraction
        config = extract_config_from_model(SmartPluginModel)

        self.assertEqual(config.kind, "collection")
        self.assertEqual(config.slug_field, "slug")
        self.assertEqual(config.locale_field, "locale")
        self.assertIn("title", config.translatable_fields)
        self.assertIn("content", config.translatable_fields)
        self.assertIn("excerpt", config.translatable_fields)
        self.assertIn("title", config.searchable_fields)
        self.assertIn("content", config.searchable_fields)
        self.assertIn("tags", config.searchable_fields)
        self.assertIn("seo_title", config.seo_fields)
        self.assertIn("seo_description", config.seo_fields)
        self.assertTrue(config.can_publish)
        self.assertIn("-published_at", config.ordering)
        self.assertIn("title", config.ordering)

    def test_conditional_plugin_loading(self):
        """Test conditional loading of plugins based on settings or environment."""
        from apps.cms.models import Page

        def load_plugins_conditionally(registry, enabled_plugins=None):
            """Load plugins based on conditions."""
            enabled_plugins = enabled_plugins or []

            available_plugins = {
                "blog": lambda: ContentConfig(
                    model=Page, kind="singleton", name="Blog Settings"
                ),
                "ecommerce": lambda: ContentConfig(
                    model=Page,
                    kind="collection",
                    name="Products",
                    slug_field="slug",
                ),
                "newsletter": lambda: ContentConfig(
                    model=Page, kind="singleton", name="Newsletter Settings"
                ),
            }

            for plugin_name in enabled_plugins:
                if plugin_name in available_plugins:
                    try:
                        config = available_plugins[plugin_name]()
                        # Modify model label to make each unique
                        original_model = config.model
                        unique_model = type(
                            f"{original_model.__name__}_{plugin_name}",
                            (original_model,),
                            {"__module__": original_model.__module__},
                        )
                        config.model = unique_model
                        registry.register(config)
                    except Exception as e:
                        print(f"Failed to load plugin {plugin_name}: {e}")

        # Test loading different combinations of plugins
        registry = ContentRegistry()

        # Load only blog plugin
        load_plugins_conditionally(registry, ["blog"])
        self.assertEqual(len(registry.get_all_configs()), 1)
        self.assertEqual(len(registry.get_configs_by_kind("singleton")), 1)

        # Clear and load blog + ecommerce
        registry.clear()
        load_plugins_conditionally(registry, ["blog", "ecommerce"])
        self.assertEqual(len(registry.get_all_configs()), 2)
        self.assertEqual(len(registry.get_configs_by_kind("singleton")), 1)
        self.assertEqual(len(registry.get_configs_by_kind("collection")), 1)

        # Clear and load all plugins
        registry.clear()
        load_plugins_conditionally(registry, ["blog", "ecommerce", "newsletter"])
        self.assertEqual(len(registry.get_all_configs()), 3)
        self.assertEqual(len(registry.get_configs_by_kind("singleton")), 2)
        self.assertEqual(len(registry.get_configs_by_kind("collection")), 1)

    @patch("importlib.import_module")
    def test_dynamic_module_loading_for_plugins(self, mock_import):
        """Test dynamic loading of plugin modules."""

        # Create a mock plugin module
        mock_plugin_module = ModuleType("test_plugin")

        class PluginContent(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)

            class Meta:
                app_label = "dynamic_plugin"

        # Add the model to the mock module
        mock_plugin_module.PluginContent = PluginContent
        mock_plugin_module.REGISTRY_CONFIG = {
            "model": PluginContent,
            "kind": "collection",
            "name": "Dynamic Plugin Content",
            "slug_field": "slug",
        }

        mock_import.return_value = mock_plugin_module

        def load_plugin_from_module(module_path):
            """Load plugin configuration from a module."""
            try:
                module = importlib.import_module(module_path)

                if hasattr(module, "REGISTRY_CONFIG"):
                    config_data = module.REGISTRY_CONFIG
                    config = ContentConfig(**config_data)
                    return config
                else:
                    # Try to find models in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, models.Model):
                            # Auto-configure based on model
                            has_slug = any(
                                field.name == "slug"
                                for field in attr._meta.get_fields()
                            )
                            return ContentConfig(
                                model=attr,
                                kind="collection" if has_slug else "singleton",
                                name=attr._meta.verbose_name_plural or attr.__name__,
                                slug_field="slug" if has_slug else None,
                            )
            except ImportError:
                return None

        # Test loading plugin from module path
        config = load_plugin_from_module("test_plugin")
        self.assertIsNotNone(config)
        self.assertEqual(config.name, "Dynamic Plugin Content")
        self.assertEqual(config.kind, "collection")
        self.assertEqual(config.slug_field, "slug")

        # Verify the import was called
        mock_import.assert_called_with("test_plugin")


class ComplexValidationTests(TestCase):
    """Test complex validation scenarios and edge cases."""

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

    def test_nested_field_validation(self):
        """Test validation of nested field references."""

        class ModelWithJSONField(models.Model):
            title = models.CharField(max_length=200)
            metadata = models.JSONField(default=dict)  # JSON field
            created_at = models.DateTimeField(auto_now_add=True)  # Add created_at field

            class Meta:
                app_label = "registry"

        # Test with nested field references in searchable_fields
        config = ContentConfig(
            model=ModelWithJSONField,
            kind="singleton",
            name="JSON Model",
            locale_field=None,  # Explicitly set to None since this model doesn't have locale
            searchable_fields=["title", "metadata.description", "metadata.tags"],
            seo_fields=["title", "metadata.seo.title"],
        )

        # Should not raise validation error for nested fields
        self.assertEqual(
            config.searchable_fields, ["title", "metadata.description", "metadata.tags"]
        )
        self.assertEqual(config.seo_fields, ["title", "metadata.seo.title"])

    def test_complex_ordering_field_validation(self):
        """Test validation of complex ordering field specifications."""

        class ModelWithComplexFields(models.Model):
            title = models.CharField(max_length=200)
            priority = models.IntegerField(default=0)
            created_at = models.DateTimeField(auto_now_add=True)
            updated_at = models.DateTimeField(auto_now=True)

            class Meta:
                app_label = "registry"

        # Test various ordering field formats
        valid_ordering_specs = [
            ["-created_at", "title"],
            ["+priority", "-updated_at"],
            ["priority", "title", "-created_at"],
            ["-priority", "+title"],  # Explicit positive prefix
        ]

        for ordering in valid_ordering_specs:
            config = ContentConfig(
                model=ModelWithComplexFields,
                kind="singleton",
                name="Complex Model",
                ordering=ordering,
            )
            self.assertEqual(config.ordering, ordering)

    def test_invalid_ordering_field_validation(self):
        """Test validation fails for invalid ordering fields."""

        class SimpleModel(models.Model):
            title = models.CharField(max_length=200)

            class Meta:
                app_label = "registry"

        invalid_ordering_specs = [
            ["nonexistent_field"],
            ["-nonexistent_field"],
            ["+nonexistent_field"],
            ["title", "another_nonexistent"],
        ]

        for ordering in invalid_ordering_specs:
            with self.assertRaises(ValidationError) as cm:
                ContentConfig(
                    model=SimpleModel,
                    kind="singleton",
                    name="Simple Model",
                    ordering=ordering,
                )

            self.assertIn("ordering field", str(cm.exception))

    def test_field_validation_with_inheritance(self):
        """Test field validation with model inheritance."""

        class BaseContentModel(models.Model):
            title = models.CharField(max_length=200)
            created_at = models.DateTimeField(auto_now_add=True)

            class Meta:
                app_label = "registry"
                abstract = True

        class DerivedContentModel(BaseContentModel):
            content = models.TextField()
            slug = models.SlugField(unique=True)
            locale = models.CharField(max_length=10, blank=True)  # Add locale field
            seo = models.CharField(max_length=200, blank=True)  # Add seo field

            class Meta:
                app_label = "registry"

        # Should be able to reference fields from both base and derived classes
        config = ContentConfig(
            model=DerivedContentModel,
            kind="collection",
            name="Derived Content",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=[
                "title",
                "content",
            ],  # title from base, content from derived
            searchable_fields=["title", "content"],
            seo_fields=["title", "seo"],  # Explicitly set seo_fields
            ordering=["-created_at", "title"],  # created_at from base, title from base
        )

        self.assertEqual(config.slug_field, "slug")
        self.assertIn("title", config.translatable_fields)
        self.assertIn("content", config.translatable_fields)

    def test_validation_with_foreign_key_fields(self):
        """Test validation with foreign key and related fields."""

        class CategoryModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "registry"

        class ArticleWithRelations(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)
            category = models.ForeignKey(CategoryModel, on_delete=models.CASCADE)
            created_at = models.DateTimeField(auto_now_add=True)  # Add created_at field

            class Meta:
                app_label = "registry"

        # Test that foreign key fields are recognized for ordering
        config = ContentConfig(
            model=ArticleWithRelations,
            kind="collection",
            name="Articles",
            slug_field="slug",
            locale_field=None,  # Explicitly set to None
            ordering=["category", "title"],  # Should work with FK field
        )

        self.assertEqual(config.ordering, ["category", "title"])

        # Test with related field lookups in ordering
        # This should fail validation since we only check direct fields
        with self.assertRaises(ValidationError):
            config2 = ContentConfig(
                model=ArticleWithRelations,
                kind="collection",
                name="Articles",
                slug_field="slug",
                ordering=["category__name", "title"],  # Related field lookup
            )

    def test_form_fields_validation_comprehensive(self):
        """Test comprehensive form fields validation."""

        class ComplexFormModel(models.Model):
            # Various field types
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)
            content = models.TextField()
            excerpt = models.TextField(blank=True)
            is_featured = models.BooleanField(default=False)
            view_count = models.IntegerField(default=0)
            price = models.DecimalField(
                max_digits=10, decimal_places=2, null=True, blank=True
            )
            published_at = models.DateTimeField(null=True, blank=True)
            created_at = models.DateTimeField(auto_now_add=True)
            locale = models.CharField(max_length=10, blank=True)  # Add locale field
            seo = models.CharField(max_length=200, blank=True)  # Add seo field

            class Meta:
                app_label = "registry"

        # Test with specific form fields
        config = ContentConfig(
            model=ComplexFormModel,
            kind="collection",
            name="Complex Form",
            slug_field="slug",
            locale_field="locale",
            seo_fields=["title", "seo"],  # Explicitly set seo_fields
            form_fields=["title", "slug", "content", "is_featured", "price"],
        )

        effective_fields = config.get_effective_form_fields()
        self.assertEqual(
            effective_fields, ["title", "slug", "content", "is_featured", "price"]
        )

        # Test with no form_fields specified (should return all fields)
        config2 = ContentConfig(
            model=ComplexFormModel,
            kind="collection",
            name="Complex Form",
            slug_field="slug",
        )

        effective_fields2 = config2.get_effective_form_fields()
        # Should include all direct fields except relations
        expected_fields = {
            "title",
            "slug",
            "content",
            "excerpt",
            "is_featured",
            "view_count",
            "price",
            "published_at",
            "created_at",
            "id",
            "locale",
            "seo",
        }
        self.assertEqual(set(effective_fields2), expected_fields)

    def test_route_pattern_validation_edge_cases(self):
        """Test route pattern validation with edge cases."""

        class RouteTestModel(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)
            created_at = models.DateTimeField(auto_now_add=True)  # Add created_at field

            class Meta:
                app_label = "registry"

        # Valid route patterns for collections
        valid_patterns = [
            "/{slug}",
            "/articles/{slug}",
            "/blog/{slug}/",
            "/category/articles/{slug}",
            "/{slug}.html",
            "/api/v1/content/{slug}",
        ]

        for pattern in valid_patterns:
            config = ContentConfig(
                model=RouteTestModel,
                kind="collection",
                name="Route Test",
                slug_field="slug",
                locale_field=None,  # Explicitly set to None
                seo_fields=["title"],  # Explicitly set seo_fields
                route_pattern=pattern,
            )
            self.assertEqual(config.get_route_pattern(), pattern)

        # Invalid route patterns for collections (missing {slug})
        invalid_patterns = [
            "/articles",
            "/blog/",
            "/category/articles",
            "/static-route",
        ]

        for pattern in invalid_patterns:
            with self.assertRaises(ValidationError) as cm:
                ContentConfig(
                    model=RouteTestModel,
                    kind="collection",
                    name="Route Test",
                    slug_field="slug",
                    route_pattern=pattern,
                )

            self.assertIn("route_pattern should contain '{slug}'", str(cm.exception))

    def test_supports_methods_edge_cases(self):
        """Test supports_* methods with edge cases."""

        class EdgeCaseModel(models.Model):
            title = models.CharField(max_length=200)
            status = models.CharField(
                max_length=20, default="active"
            )  # Has status field
            locale = models.CharField(
                max_length=10, null=True, blank=True
            )  # Has locale field
            created_at = models.DateTimeField(auto_now_add=True)  # Add created_at field

            class Meta:
                app_label = "registry"

        # Test supports_publishing with can_publish=True and status field exists
        config1 = ContentConfig(
            model=EdgeCaseModel,
            kind="singleton",
            name="Edge Case 1",
            locale_field="locale",  # Explicitly set locale_field
            can_publish=True,
        )
        self.assertTrue(config1.supports_publishing())

        # Test supports_publishing with can_publish=False even though status field exists
        config2 = ContentConfig(
            model=EdgeCaseModel,
            kind="singleton",
            name="Edge Case 2",
            can_publish=False,
        )
        self.assertFalse(config2.supports_publishing())

        # Test supports_localization with locale_field set
        config3 = ContentConfig(
            model=EdgeCaseModel,
            kind="singleton",
            name="Edge Case 3",
            locale_field="locale",
        )
        self.assertTrue(config3.supports_localization())

        # Test supports_localization with locale_field=None
        config4 = ContentConfig(
            model=EdgeCaseModel,
            kind="singleton",
            name="Edge Case 4",
            locale_field=None,
        )
        self.assertFalse(config4.supports_localization())

    def test_config_dict_serialization_completeness(self):
        """Test that to_dict() includes all necessary information."""

        class CompletePluginModel(models.Model):
            title = models.CharField(max_length=200)
            slug = models.SlugField(unique=True)
            content = models.TextField()
            status = models.CharField(max_length=20)
            locale = models.CharField(max_length=10)
            created_at = models.DateTimeField(auto_now_add=True)
            seo = models.CharField(
                max_length=200, blank=True
            )  # Add seo field to satisfy default seo_fields

            class Meta:
                app_label = "registry"
                verbose_name = "Complete Plugin Model"
                verbose_name_plural = "Complete Plugin Models"

        config = ContentConfig(
            model=CompletePluginModel,
            kind="collection",
            name="Complete Config",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "content"],
            searchable_fields=["title", "content"],
            seo_fields=["title"],
            route_pattern="/complete/{slug}",
            can_publish=True,
            allowed_block_types=["text", "image"],
            form_fields=["title", "slug", "content"],
            ordering=["-created_at", "title"],
        )

        data = config.to_dict()

        # Verify all expected keys are present
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

        # Verify values
        self.assertEqual(data["model_label"], "registry.completepluginmodel")
        self.assertEqual(data["kind"], "collection")
        self.assertEqual(data["name"], "Complete Config")
        self.assertEqual(data["slug_field"], "slug")
        self.assertEqual(data["locale_field"], "locale")
        self.assertEqual(data["route_pattern"], "/complete/{slug}")
        self.assertTrue(data["can_publish"])
        self.assertTrue(data["supports_publishing"])
        self.assertTrue(data["supports_localization"])
        self.assertEqual(data["verbose_name"], "Complete Plugin Model")
        self.assertEqual(data["verbose_name_plural"], "Complete Plugin Models")

    def test_validation_error_message_clarity(self):
        """Test that validation error messages are clear and helpful."""

        class ValidationTestModel(models.Model):
            title = models.CharField(max_length=200)

            class Meta:
                app_label = "registry"

        # Test multiple validation errors at once
        try:
            ContentConfig(
                model=ValidationTestModel,
                kind="invalid_kind",  # Error 1
                name="Test",
                slug_field="nonexistent_slug",  # Error 2
                locale_field="nonexistent_locale",  # Error 3
                translatable_fields=["nonexistent_trans"],  # Error 4
                searchable_fields=["nonexistent_search"],  # Error 5
                seo_fields=["nonexistent_seo"],  # Error 6
                form_fields=["nonexistent_form"],  # Error 7
                ordering=["nonexistent_order"],  # Error 8
            )
            self.fail("Expected ValidationError was not raised")
        except ValidationError as e:
            error_message = str(e)

            # Should contain information about all validation errors
            self.assertIn("Invalid kind", error_message)
            self.assertIn("slug_field", error_message)
            self.assertIn("locale_field", error_message)
            self.assertIn("translatable_field", error_message)
            self.assertIn("searchable_field", error_message)
            self.assertIn("seo_field", error_message)
            self.assertIn("form_field", error_message)
            self.assertIn("ordering field", error_message)

            # Should mention the specific field names that are invalid
            self.assertIn("nonexistent_slug", error_message)
            self.assertIn("nonexistent_locale", error_message)
            self.assertIn("invalid_kind", error_message)
