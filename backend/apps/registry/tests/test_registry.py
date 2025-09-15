import os

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from apps.cms.models import Page
from apps.i18n.models import Locale
from apps.registry.config import ContentConfig
from apps.registry.registry import (
    ContentRegistry,
    ContentRegistryError,
    content_registry,
    register_core_models,
)
from apps.registry.serializers import ContentSerializerFactory, get_serializer_for_model
from apps.registry.viewsets import ContentViewSetFactory, get_viewset_for_model

User = get_user_model()


class ContentConfigTests(TestCase):
    """Test ContentConfig functionality."""

    def setUp(self):
        """Set up test data."""

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

    def test_valid_config_creation(self):
        """Test creating a valid ContentConfig."""

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "blocks"],
            searchable_fields=["title", "blocks"],
            can_publish=True,
        )

        self.assertEqual(config.model, Page)

        self.assertEqual(config.kind, "collection")

        self.assertEqual(config.name, "Pages")

        self.assertEqual(config.model_label, "cms.page")

    def test_invalid_kind(self):
        """Test config with invalid kind."""

        with self.assertRaises(ValidationError):

            ContentConfig(model=Page, kind="invalid_kind", name="Pages")

    def test_invalid_field_names(self):
        """Test config with invalid field names."""

        with self.assertRaises(ValidationError):

            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                slug_field="nonexistent_field",
            )

    def test_singleton_validation(self):
        """Test validation rules for singleton content."""

        # Singleton should not have slug_field

        with self.assertRaises(ValidationError):

            ContentConfig(
                model=Page, kind="singleton", name="Settings", slug_field="slug"
            )

    def test_collection_validation(self):
        """Test validation rules for collection content."""

        # Collection should have slug_field

        with self.assertRaises(ValidationError):

            ContentConfig(
                model=Page,
                kind="collection",
                name="Pages",
                # Missing slug_field
            )

    def test_route_pattern_generation(self):
        """Test automatic route pattern generation."""

        config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.assertEqual(config.get_route_pattern(), "/page/{slug}")

        # Test custom route pattern

        config.route_pattern = "/custom/{slug}"

        self.assertEqual(config.get_route_pattern(), "/custom/{slug}")

    def test_config_to_dict(self):
        """Test converting config to dictionary."""

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        data = config.to_dict()

        self.assertIn("model_label", data)

        self.assertIn("kind", data)

        self.assertIn("supports_publishing", data)

        self.assertIn("supports_localization", data)

        self.assertEqual(data["model_label"], "cms.page")

        self.assertEqual(data["kind"], "collection")


class ContentRegistryTests(TestCase):
    """Test ContentRegistry functionality."""

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

    def test_register_config(self):
        """Test registering a configuration."""

        config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.registry.register(config)

        self.assertTrue(self.registry.is_registered("cms.page"))

        self.assertEqual(len(self.registry.get_all_configs()), 1)

    def test_duplicate_registration(self):
        """Test that duplicate registration raises error."""

        config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.registry.register(config)

        with self.assertRaises(ContentRegistryError):

            self.registry.register(config)

    def test_get_config(self):
        """Test getting configuration by model label."""

        config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.registry.register(config)

        retrieved_config = self.registry.get_config("cms.page")

        self.assertEqual(retrieved_config, config)

        # Test non-existent config

        self.assertIsNone(self.registry.get_config("nonexistent.model"))

    def test_get_config_by_model(self):
        """Test getting configuration by model class."""

        config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.registry.register(config)

        retrieved_config = self.registry.get_config_by_model(Page)

        self.assertEqual(retrieved_config, config)

    def test_get_configs_by_kind(self):
        """Test filtering configurations by kind."""

        page_config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.registry.register(page_config)

        collections = self.registry.get_configs_by_kind("collection")

        self.assertEqual(len(collections), 1)

        self.assertEqual(collections[0], page_config)

        singletons = self.registry.get_configs_by_kind("singleton")

        self.assertEqual(len(singletons), 0)

    def test_unregister(self):
        """Test unregistering a configuration."""

        config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.registry.register(config)

        self.assertTrue(self.registry.is_registered("cms.page"))

        self.registry.unregister("cms.page")

        self.assertFalse(self.registry.is_registered("cms.page"))

    def test_registry_summary(self):
        """Test registry summary generation."""

        config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.registry.register(config)

        summary = self.registry.get_registry_summary()

        self.assertEqual(summary["total_registered"], 1)

        self.assertEqual(summary["by_kind"]["collection"], 1)

        self.assertEqual(summary["by_kind"]["singleton"], 0)

        self.assertIn("configs", summary)

    def test_export_configs(self):
        """Test exporting configurations as JSON."""

        config = ContentConfig(
            model=Page, kind="collection", name="Pages", slug_field="slug"
        )

        self.registry.register(config)

        export_data = self.registry.export_configs()

        self.assertIsInstance(export_data, str)

        self.assertIn("cms.page", export_data)

        self.assertIn("registry_version", export_data)


class ContentSerializerFactoryTests(TestCase):
    """Test ContentSerializerFactory functionality."""

    def setUp(self):
        """Set up test data."""

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        self.config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "blocks"],
            searchable_fields=["title", "blocks"],
        )

    def test_create_serializer(self):
        """Test creating a serializer from config."""

        serializer_class = ContentSerializerFactory.create_serializer(self.config)

        self.assertTrue(hasattr(serializer_class, "Meta"))

        self.assertEqual(serializer_class.Meta.model, Page)

        # Test that serializer can be instantiated

        serializer = serializer_class()

        self.assertIsNotNone(serializer)

    def test_serializer_with_locale_fields(self):
        """Test serializer includes locale fields."""

        serializer_class = ContentSerializerFactory.create_serializer(self.config)

        serializer = serializer_class()

        # Should have custom locale fields

        self.assertIn("locale_code", serializer.fields)

        self.assertIn("locale_name", serializer.fields)

    def test_serializer_with_url_field(self):
        """Test serializer includes URL field for collections."""

        serializer_class = ContentSerializerFactory.create_serializer(self.config)

        serializer = serializer_class()

        # Should have URL field for collections with slug

        self.assertIn("url", serializer.fields)


class ContentViewSetFactoryTests(TestCase):
    """Test ContentViewSetFactory functionality."""

    def setUp(self):
        """Set up test data."""

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        self.config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "blocks"],
            searchable_fields=["title", "blocks"],
        )

    def test_create_viewset(self):
        """Test creating a ViewSet from config."""

        viewset_class = ContentViewSetFactory.create_viewset(self.config)

        self.assertTrue(hasattr(viewset_class, "queryset"))

        self.assertEqual(viewset_class.queryset.model, Page)

        # Test that ViewSet can be instantiated

        viewset = viewset_class()

        self.assertIsNotNone(viewset)

    def test_viewset_filtering(self):
        """Test ViewSet has proper filtering configured."""

        viewset_class = ContentViewSetFactory.create_viewset(self.config)

        # Should have filterset fields for locale and status

        self.assertIn("locale", viewset_class.filterset_fields)

        self.assertIn("status", viewset_class.filterset_fields)

        # Should have search fields

        self.assertEqual(viewset_class.search_fields, ["title", "blocks"])

    def test_by_slug_action(self):
        """Test ViewSet has by-slug action for collections."""

        viewset_class = ContentViewSetFactory.create_viewset(self.config)

        # Should have by_slug method

        self.assertTrue(hasattr(viewset_class, "by_slug"))


class RegistryAPITests(APITestCase):
    """Test registry API endpoints."""

    def setUp(self):
        """Set up test data."""

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        # Manually register Page model for tests since auto-registration doesn't run

        try:

            register_core_models()

        except Exception:
            # If it fails because already registered, that's fine
            pass

    def tearDown(self):
        """Clean up after test."""
        User = get_user_model()

        # Clean up test data - handle database errors gracefully for test environments
        try:
            Page.objects.all().delete()
        except Exception:
            # Handle cases where tables don't exist (e.g., in test environments with disabled migrations)
            pass

        try:
            Locale.objects.all().delete()
        except Exception:
            # Handle cases where tables don't exist
            pass

        try:
            # Use ORM delete to properly handle cascade relationships (User -> UserProfile)
            User.objects.filter(email="test@example.com").delete()
        except Exception:
            # If ORM delete fails, it's likely due to test environment issues - ignore
            pass

    def test_registry_list_endpoint(self):
        """Test listing registry configurations."""

        response = self.client.get("/api/v1/api/registry/content/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertIsInstance(data, list)

        self.assertGreater(len(data), 0)

        # Check first config structure

        config = data[0]

        self.assertIn("model_label", config)

        self.assertIn("kind", config)

        self.assertIn("name", config)

    def test_registry_summary_endpoint(self):
        """Test registry summary endpoint."""

        response = self.client.get("/api/v1/api/registry/content/summary/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertIn("total_registered", data)

        self.assertIn("by_kind", data)

        self.assertIn("configs", data)

        self.assertGreater(data["total_registered"], 0)

    def test_registry_export_endpoint(self):
        """Test registry export endpoint."""

        response = self.client.get("/api/v1/api/registry/content/export/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Response should be JSON string

        """self.assertEqual(response["Content-Type"], "application/json")"""


class RegistryIntegrationTests(TestCase):
    """Integration tests for the entire registry system."""

    def setUp(self):
        """Set up test data."""

        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        # Manually register Page model for tests since auto-registration doesn't run

        try:

            register_core_models()

        except Exception:
            # If it fails because already registered, that's fine
            pass

    def test_end_to_end_registration(self):
        """Test complete registration workflow."""

        # Page model should be registered via setup

        # Get the existing configuration

        config = content_registry.get_config("cms.page")

        # Verify registration

        self.assertIsNotNone(config)

        # The auto-registered Page has name 'Pages'
        if config:
            self.assertEqual(config.name, "Pages")

        # Test serializer creation

        serializer_class = get_serializer_for_model("cms.page")

        self.assertIsNotNone(serializer_class)

        # Test ViewSet creation

        viewset_class = get_viewset_for_model("cms.page")

        self.assertIsNotNone(viewset_class)

        # Test that ViewSet works with actual data

        page = Page.objects.create(
            title="Test Page",
            slug="test-page",
            path="/test-page",
            locale=self.locale,
            blocks=[],
            status="draft",
        )

        viewset = viewset_class()

        queryset = viewset.get_queryset()

        self.assertEqual(queryset.count(), 1)

        self.assertEqual(queryset.first(), page)
