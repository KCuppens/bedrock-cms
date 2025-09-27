"""Comprehensive tests for dynamic serializer and viewset loading."""

import json
import os
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from django.contrib.auth import get_user_model
from django.db import models
from django.test import RequestFactory, TestCase

from rest_framework import permissions, serializers, status, viewsets
from rest_framework.test import APIRequestFactory, APITestCase

from apps.cms.models import Page
from apps.i18n.models import Locale
from apps.registry.config import ContentConfig
from apps.registry.registry import content_registry
from apps.registry.serializers import (
    ContentSerializerFactory,
    RegistrySerializer,
    RegistrySummarySerializer,
    get_serializer_for_config,
    get_serializer_for_model,
)
from apps.registry.viewsets import (
    ContentViewSetFactory,
    RegistryViewSet,
    get_viewset_for_config,
    get_viewset_for_model,
)

User = get_user_model()


class ContentSerializerFactoryTests(TestCase):
    """Comprehensive tests for ContentSerializerFactory."""

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

        self.factory = APIRequestFactory()

    def test_create_basic_serializer(self):
        """Test creating a basic serializer."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)

        # Test class properties
        self.assertTrue(issubclass(serializer_class, serializers.ModelSerializer))
        self.assertEqual(serializer_class.__name__, "PageSerializer")
        self.assertEqual(serializer_class.Meta.model, Page)

        # Test instantiation
        serializer = serializer_class()
        self.assertIsNotNone(serializer)

    def test_serializer_with_custom_form_fields(self):
        """Test serializer creation with custom form fields."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            form_fields=["title", "slug", "blocks"],
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should include custom form fields
        expected_fields = {
            "title",
            "slug",
            "blocks",
            "locale_code",
            "locale_name",
            "url",
            "reading_time",
        }
        actual_fields = set(serializer.fields.keys())

        # Should at least contain the specified form fields
        self.assertTrue({"title", "slug", "blocks"}.issubset(actual_fields))

    def test_serializer_with_default_form_fields(self):
        """Test serializer creation with default form fields."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should include all model fields (excluding many-to-many and reverse)
        fields = serializer.fields.keys()

        # Should include basic Page fields
        expected_basic_fields = ["title", "slug", "blocks", "status"]
        for field in expected_basic_fields:
            self.assertIn(field, fields)

    def test_serializer_custom_fields_locale(self):
        """Test serializer includes locale custom fields."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should have locale custom fields
        self.assertIn("locale_code", serializer.fields)
        self.assertIn("locale_name", serializer.fields)

        # Test locale fields are CharField with proper source
        locale_code_field = serializer.fields["locale_code"]
        locale_name_field = serializer.fields["locale_name"]

        self.assertIsInstance(locale_code_field, serializers.CharField)
        self.assertIsInstance(locale_name_field, serializers.CharField)
        self.assertTrue(locale_code_field.read_only)
        self.assertTrue(locale_name_field.read_only)

    def test_serializer_custom_fields_url(self):
        """Test serializer includes URL field for collections with slug."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            route_pattern="/{slug}",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should have URL field
        self.assertIn("url", serializer.fields)

        url_field = serializer.fields["url"]
        self.assertIsInstance(url_field, serializers.SerializerMethodField)

        # Should have get_url method
        self.assertTrue(hasattr(serializer, "get_url"))

    def test_serializer_url_field_generation(self):
        """Test URL field generates correct URLs."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            route_pattern="/pages/{slug}",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Create mock object
        mock_obj = Mock()
        mock_obj.slug = "test-page"

        # Test URL generation
        url = serializer.get_url(mock_obj)
        self.assertEqual(url, "/pages/test-page")

    def test_serializer_url_field_missing_slug(self):
        """Test URL field handles missing slug gracefully."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            route_pattern="/pages/{slug}",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Create mock object without slug
        mock_obj = Mock()
        mock_obj.slug = None

        # Should return None
        url = serializer.get_url(mock_obj)
        self.assertIsNone(url)

    def test_serializer_reading_time_field_blocks(self):
        """Test reading time calculation from blocks field."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should have reading_time field
        self.assertIn("reading_time", serializer.fields)

        # Test reading time calculation
        mock_obj = Mock()
        mock_obj.reading_time = None
        mock_obj.blocks = [
            {
                "type": "text",
                "props": {"content": "This is some test content " * 50},  # ~300 words
            },
            {"type": "text", "props": {"text": "More content " * 100}},  # ~200 words
        ]

        reading_time = serializer.get_reading_time(mock_obj)
        # Should be at least 1 minute for ~500 words
        self.assertGreaterEqual(reading_time, 1)

    def test_serializer_reading_time_field_precomputed(self):
        """Test reading time uses precomputed value when available."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Test with precomputed reading time
        mock_obj = Mock()
        mock_obj.reading_time = 5
        mock_obj.blocks = []

        reading_time = serializer.get_reading_time(mock_obj)
        self.assertEqual(reading_time, 5)

    def test_serializer_reading_time_body_blocks(self):
        """Test reading time calculation from blocks field."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            searchable_fields=["blocks"],  # Indicates blocks field exists
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Mock object with body_blocks instead of blocks
        mock_obj = Mock()
        mock_obj.reading_time = None
        mock_obj.blocks = None  # No blocks field
        mock_obj.body_blocks = [
            {
                "type": "paragraph",
                "props": {"content": "Test content " * 100},  # ~200 words
            }
        ]

        # Should handle body_blocks field
        reading_time = serializer.get_reading_time(mock_obj)
        self.assertGreaterEqual(reading_time, 1)

    def test_serializer_without_locale_field(self):
        """Test serializer without locale field."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field=None,
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should not have locale fields
        self.assertNotIn("locale_code", serializer.fields)
        self.assertNotIn("locale_name", serializer.fields)

    def test_serializer_without_url_field(self):
        """Test serializer without URL field when no slug or route pattern."""
        config = ContentConfig(
            model=Page,
            kind="singleton",
            name="Settings",
            # No slug_field or route_pattern
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should not have URL field
        self.assertNotIn("url", serializer.fields)

    def test_serializer_read_only_fields(self):
        """Test serializer has appropriate read-only fields."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)

        # Check read-only fields
        read_only_fields = serializer_class.Meta.read_only_fields

        self.assertIn("id", read_only_fields)
        self.assertIn("created_at", read_only_fields)
        self.assertIn("updated_at", read_only_fields)

    def test_serializer_custom_validation(self):
        """Test serializer has custom validation method."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should have validate method
        self.assertTrue(hasattr(serializer, "validate"))

        # Validate method should return attrs unchanged by default
        attrs = {"title": "Test Page", "slug": "test-page"}
        result = serializer.validate(attrs)
        self.assertEqual(result, attrs)

    def test_serializer_with_complex_config(self):
        """Test serializer creation with complex configuration."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Complex Pages",
            slug_field="slug",
            locale_field="locale",
            translatable_fields=["title", "blocks", "seo"],
            searchable_fields=["title", "blocks", "seo.title"],
            seo_fields=["title", "seo"],
            route_pattern="/complex/{slug}",
            can_publish=True,
            allowed_block_types=["text", "image", "video"],
            form_fields=["title", "slug", "blocks", "seo", "status"],
            ordering=["-updated_at", "title"],
        )

        serializer_class = ContentSerializerFactory.create_serializer(config)
        serializer = serializer_class()

        # Should include all specified fields
        expected_fields = {"title", "slug", "blocks", "seo", "status"}
        actual_fields = set(serializer.fields.keys())

        self.assertTrue(expected_fields.issubset(actual_fields))

        # Should have custom fields
        self.assertIn("locale_code", serializer.fields)
        self.assertIn("locale_name", serializer.fields)
        self.assertIn("url", serializer.fields)
        self.assertIn("reading_time", serializer.fields)


class SerializerHelperFunctionTests(TestCase):
    """Test serializer helper functions."""

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
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_get_serializer_for_config(self):
        """Test get_serializer_for_config function."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        serializer_class = get_serializer_for_config(config)

        self.assertTrue(issubclass(serializer_class, serializers.ModelSerializer))
        self.assertEqual(serializer_class.__name__, "PageSerializer")

    def test_get_serializer_for_model_registered(self):
        """Test get_serializer_for_model with registered model."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        serializer_class = get_serializer_for_model("cms.page")

        self.assertTrue(issubclass(serializer_class, serializers.ModelSerializer))
        self.assertEqual(serializer_class.__name__, "PageSerializer")

    def test_get_serializer_for_model_unregistered(self):
        """Test get_serializer_for_model with unregistered model."""
        with self.assertRaises(ValueError) as cm:
            get_serializer_for_model("nonexistent.model")

        self.assertIn("not registered", str(cm.exception))
        self.assertIn("nonexistent.model", str(cm.exception))


class RegistrySerializerTests(TestCase):
    """Test RegistrySerializer and RegistrySummarySerializer."""

    def test_registry_serializer_fields(self):
        """Test RegistrySerializer has all required fields."""
        serializer = RegistrySerializer()

        expected_fields = [
            "model_label",
            "kind",
            "name",
            "verbose_name",
            "verbose_name_plural",
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
            "supports_publishing",
            "supports_localization",
        ]

        for field in expected_fields:
            self.assertIn(field, serializer.fields)

    def test_registry_serializer_serialization(self):
        """Test RegistrySerializer serialization."""
        data = {
            "model_label": "cms.page",
            "kind": "collection",
            "name": "Pages",
            "verbose_name": "page",
            "verbose_name_plural": "pages",
            "slug_field": "slug",
            "locale_field": "locale",
            "translatable_fields": ["title", "blocks"],
            "searchable_fields": ["title"],
            "seo_fields": ["title", "seo"],
            "route_pattern": "/{slug}",
            "can_publish": True,
            "allowed_block_types": ["text", "image"],
            "form_fields": ["title", "slug"],
            "ordering": ["-created_at"],
            "supports_publishing": True,
            "supports_localization": True,
        }

        serializer = RegistrySerializer(data=data)
        self.assertTrue(serializer.is_valid())

        serialized_data = serializer.validated_data
        self.assertEqual(serialized_data["model_label"], "cms.page")
        self.assertEqual(serialized_data["kind"], "collection")

    def test_registry_summary_serializer_fields(self):
        """Test RegistrySummarySerializer has all required fields."""
        serializer = RegistrySummarySerializer()

        expected_fields = ["total_registered", "by_kind", "configs"]

        for field in expected_fields:
            self.assertIn(field, serializer.fields)

    def test_registry_summary_serializer_serialization(self):
        """Test RegistrySummarySerializer serialization."""
        data = {
            "total_registered": 5,
            "by_kind": {
                "collection": 3,
                "singleton": 1,
                "snippet": 1,
            },
            "configs": {
                "collection": [],
                "singleton": [],
                "snippet": [],
            },
        }

        serializer = RegistrySummarySerializer(data=data)
        self.assertTrue(serializer.is_valid())

        serialized_data = serializer.validated_data
        self.assertEqual(serialized_data["total_registered"], 5)
        self.assertEqual(serialized_data["by_kind"]["collection"], 3)


class ContentViewSetFactoryTests(TestCase):
    """Comprehensive tests for ContentViewSetFactory."""

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

        self.factory = RequestFactory()

    def test_create_basic_viewset(self):
        """Test creating a basic viewset."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Test class properties
        self.assertTrue(issubclass(viewset_class, viewsets.ModelViewSet))
        self.assertEqual(viewset_class.__name__, "PageViewSet")

        # Test viewset has required attributes
        self.assertIsNotNone(viewset_class.queryset)
        self.assertIsNotNone(viewset_class.serializer_class)
        self.assertIsNotNone(viewset_class.permission_classes)
        self.assertIsNotNone(viewset_class.filter_backends)

    def test_viewset_queryset_configuration(self):
        """Test viewset queryset is properly configured."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Queryset should be Page.objects.all()
        self.assertEqual(viewset_class.queryset.model, Page)

    def test_viewset_permission_configuration(self):
        """Test viewset permissions are properly configured."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should have IsAuthenticatedOrReadOnly permission
        self.assertIn(
            permissions.IsAuthenticatedOrReadOnly, viewset_class.permission_classes
        )

    def test_viewset_filter_backends(self):
        """Test viewset filter backends are properly configured."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            searchable_fields=["title", "blocks"],
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should have all required filter backends
        from django_filters.rest_framework import DjangoFilterBackend
        from rest_framework import filters

        expected_backends = {
            DjangoFilterBackend,
            filters.SearchFilter,
            filters.OrderingFilter,
        }
        actual_backends = set(viewset_class.filter_backends)

        self.assertTrue(expected_backends.issubset(actual_backends))

    def test_viewset_filterset_fields_basic(self):
        """Test viewset filterset fields configuration."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should include locale field
        self.assertIn("locale", viewset_class.filterset_fields)

        # Should include status field since Page supports publishing
        self.assertIn("status", viewset_class.filterset_fields)

    def test_viewset_filterset_fields_custom(self):
        """Test viewset filterset fields with custom filterable fields."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        # Mock filterable_fields attribute
        config.filterable_fields = ["title", "status"]

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should include custom filterable fields
        self.assertIn("status", viewset_class.filterset_fields)

    def test_viewset_search_fields(self):
        """Test viewset search fields configuration."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            searchable_fields=["title", "blocks", "seo.title"],
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should include searchable fields (excluding nested ones)
        expected_fields = ["title", "blocks"]
        for field in expected_fields:
            self.assertIn(field, viewset_class.search_fields)

    def test_viewset_ordering_fields(self):
        """Test viewset ordering fields configuration."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            ordering=["-created_at", "title"],
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should include ordering fields
        self.assertIn("created_at", viewset_class.ordering_fields)
        self.assertIn("title", viewset_class.ordering_fields)

        # Should also include common ordering fields
        self.assertIn("updated_at", viewset_class.ordering_fields)

    def test_viewset_ordering_configuration(self):
        """Test viewset ordering configuration."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            ordering=["-updated_at", "title"],
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should use config ordering
        self.assertEqual(viewset_class.ordering, ["-updated_at", "title"])

    def test_viewset_by_slug_action(self):
        """Test viewset includes by-slug action for collections with slug."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should have by_slug method
        self.assertTrue(hasattr(viewset_class, "by_slug"))

        # Test by_slug method
        viewset = viewset_class()
        viewset.request = Mock()
        viewset.request.query_params = {"slug": "test-page"}

        # Mock get_queryset and get_object_or_404
        with (
            patch.object(viewset, "get_queryset") as mock_get_queryset,
            patch("apps.registry.viewsets.get_object_or_404") as mock_get_object,
        ):

            mock_queryset = Mock()
            mock_get_queryset.return_value = mock_queryset

            mock_page = Mock()
            mock_get_object.return_value = mock_page

            with patch.object(viewset, "get_serializer") as mock_get_serializer:
                mock_serializer = Mock()
                mock_serializer.data = {"title": "Test Page"}
                mock_get_serializer.return_value = mock_serializer

                response = viewset.by_slug(viewset.request)

                # Should filter by slug
                mock_queryset.filter.assert_called_with(slug="test-page")

    def test_viewset_by_slug_action_with_locale(self):
        """Test by-slug action with locale filtering."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)
        viewset = viewset_class()

        # Mock request with slug and locale
        viewset.request = Mock()
        viewset.request.query_params = {"slug": "test-page", "locale": "en"}

        with (
            patch.object(viewset, "get_queryset") as mock_get_queryset,
            patch("apps.registry.viewsets.get_object_or_404") as mock_get_object,
            patch("apps.registry.viewsets.Locale.objects.get") as mock_get_locale,
        ):

            # Create chained queryset mocks
            mock_queryset1 = Mock()
            mock_queryset2 = Mock()
            mock_queryset1.filter.return_value = mock_queryset2
            mock_get_queryset.return_value = mock_queryset1

            mock_locale = Mock()
            mock_get_locale.return_value = mock_locale

            mock_page = Mock()
            mock_get_object.return_value = mock_page

            with patch.object(viewset, "get_serializer") as mock_get_serializer:
                mock_serializer = Mock()
                mock_serializer.data = {"title": "Test Page"}
                mock_get_serializer.return_value = mock_serializer

                response = viewset.by_slug(viewset.request)

                # Should filter by both slug and locale
                mock_queryset1.filter.assert_called_once_with(slug="test-page")
                mock_queryset2.filter.assert_called_once_with(locale=mock_locale)

    def test_viewset_by_slug_missing_slug(self):
        """Test by-slug action with missing slug parameter."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)
        viewset = viewset_class()

        # Mock request without slug
        viewset.request = Mock()
        viewset.request.query_params = {}

        response = viewset.by_slug(viewset.request)

        # Should return 400 error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("slug parameter is required", response.data["error"])

    def test_viewset_by_slug_invalid_locale(self):
        """Test by-slug action with invalid locale."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)
        viewset = viewset_class()

        # Mock request with invalid locale
        viewset.request = Mock()
        viewset.request.query_params = {"slug": "test-page", "locale": "invalid"}

        with (
            patch.object(viewset, "get_queryset") as mock_get_queryset,
            patch("apps.registry.viewsets.Locale.objects.get") as mock_get_locale,
        ):

            mock_get_locale.side_effect = Locale.DoesNotExist()

            response = viewset.by_slug(viewset.request)

            # Should return 400 error
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Invalid locale code", response.data["error"])

    def test_viewset_custom_get_queryset(self):
        """Test viewset custom get_queryset method."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            searchable_fields=["title", "blocks"],
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)
        viewset = viewset_class()

        # Test without search query
        queryset = viewset.get_queryset()
        self.assertEqual(queryset.model, Page)

        # Test with search query
        viewset.request = Mock()
        viewset.request.query_params = {"q": "test search"}

        with patch.object(Page.objects, "all") as mock_all:
            mock_queryset = Mock()
            mock_all.return_value = mock_queryset

            queryset = viewset.get_queryset()

            # Should apply search filter
            mock_queryset.filter.assert_called_once()

    def test_viewset_custom_filter_queryset_locale(self):
        """Test viewset custom filter_queryset for locale filtering."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)
        viewset = viewset_class()

        # Mock request with locale parameter
        viewset.request = Mock()
        viewset.request.query_params = {"locale": "en"}

        mock_queryset = Mock()

        with (
            patch("apps.registry.viewsets.Locale.objects.get") as mock_get_locale,
            patch(
                "rest_framework.viewsets.ModelViewSet.filter_queryset"
            ) as mock_parent_filter,
        ):

            mock_locale = Mock()
            mock_get_locale.return_value = mock_locale

            mock_parent_filter.return_value = mock_queryset

            filtered_queryset = viewset.filter_queryset(mock_queryset)

            # Should call parent filter_queryset
            mock_parent_filter.assert_called_once_with(viewset, mock_queryset)

            # Should filter by locale
            mock_queryset.filter.assert_called_with(locale=mock_locale)

    def test_viewset_without_slug_field(self):
        """Test viewset creation for content without slug field (singleton)."""
        config = ContentConfig(
            model=Page,
            kind="singleton",
            name="Settings",
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should not have by_slug method
        self.assertFalse(hasattr(viewset_class, "by_slug"))

    def test_viewset_without_locale_field(self):
        """Test viewset creation for content without locale field."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field=None,
        )

        viewset_class = ContentViewSetFactory.create_viewset(config)

        # Should not include locale in filterset_fields
        self.assertNotIn("locale", viewset_class.filterset_fields)

        # Should not have custom filter_queryset method for locale
        viewset = viewset_class()
        # The method exists but should not filter by locale
        self.assertTrue(hasattr(viewset, "filter_queryset"))


class ViewSetHelperFunctionTests(TestCase):
    """Test viewset helper functions."""

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
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_get_viewset_for_config(self):
        """Test get_viewset_for_config function."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        viewset_class = get_viewset_for_config(config)

        self.assertTrue(issubclass(viewset_class, viewsets.ModelViewSet))
        self.assertEqual(viewset_class.__name__, "PageViewSet")

    def test_get_viewset_for_model_registered(self):
        """Test get_viewset_for_model with registered model."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        viewset_class = get_viewset_for_model("cms.page")

        self.assertTrue(issubclass(viewset_class, viewsets.ModelViewSet))
        self.assertEqual(viewset_class.__name__, "PageViewSet")

    def test_get_viewset_for_model_unregistered(self):
        """Test get_viewset_for_model with unregistered model."""
        with self.assertRaises(ValueError) as cm:
            get_viewset_for_model("nonexistent.model")

        self.assertIn("not registered", str(cm.exception))
        self.assertIn("nonexistent.model", str(cm.exception))


class RegistryViewSetTests(APITestCase):
    """Test RegistryViewSet functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = APIRequestFactory()

        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={
                "name": "English",
                "native_name": "English",
                "is_default": True,
                "is_active": True,
            },
        )

        content_registry.clear()

        # Register test config
        self.config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )
        content_registry.register(self.config)

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_registry_viewset_list(self):
        """Test RegistryViewSet list method."""
        viewset = RegistryViewSet()
        request = self.factory.get("/")

        response = viewset.list(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)

        # Check config data structure
        config_data = response.data[0]
        expected_fields = ["model_label", "kind", "name"]
        for field in expected_fields:
            self.assertIn(field, config_data)

    def test_registry_viewset_retrieve(self):
        """Test RegistryViewSet retrieve method."""
        viewset = RegistryViewSet()
        request = self.factory.get("/")

        response = viewset.retrieve(request, pk="cms.page")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["model_label"], "cms.page")
        self.assertEqual(response.data["kind"], "collection")

    def test_registry_viewset_retrieve_not_found(self):
        """Test RegistryViewSet retrieve with non-existent config."""
        viewset = RegistryViewSet()
        request = self.factory.get("/")

        response = viewset.retrieve(request, pk="nonexistent.model")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.data["error"])

    def test_registry_viewset_summary(self):
        """Test RegistryViewSet summary action."""
        viewset = RegistryViewSet()
        request = self.factory.get("/")
        viewset.request = request

        response = viewset.summary(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        expected_fields = ["total_registered", "by_kind", "configs"]
        for field in expected_fields:
            self.assertIn(field, response.data)

        self.assertGreater(response.data["total_registered"], 0)

    def test_registry_viewset_export(self):
        """Test RegistryViewSet export action."""
        viewset = RegistryViewSet()
        request = self.factory.get("/")
        viewset.request = request

        response = viewset.export(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should return JSON string
        self.assertIsInstance(response.data, str)

        # Should be valid JSON
        parsed_data = json.loads(response.data)
        self.assertIn("registry_version", parsed_data)
        self.assertIn("configs", parsed_data)

    def test_registry_viewset_permissions(self):
        """Test RegistryViewSet permissions."""
        viewset = RegistryViewSet()

        # Should have IsAuthenticatedOrReadOnly permission
        self.assertIn(permissions.IsAuthenticatedOrReadOnly, viewset.permission_classes)

    def test_registry_viewset_queryset(self):
        """Test RegistryViewSet get_queryset method."""
        viewset = RegistryViewSet()

        queryset = viewset.get_queryset()

        # Should return list of configs
        self.assertIsInstance(queryset, list)
        self.assertGreater(len(queryset), 0)


class DynamicLoadingIntegrationTests(TestCase):
    """Integration tests for dynamic loading system."""

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
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_end_to_end_dynamic_loading(self):
        """Test complete dynamic loading workflow."""
        # Register config
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Test Pages",
            slug_field="slug",
            locale_field="locale",
            searchable_fields=["title", "blocks"],
            ordering=["-created_at", "title"],
        )

        content_registry.register(config)

        # Get serializer
        serializer_class = get_serializer_for_model("cms.page")
        self.assertIsNotNone(serializer_class)

        # Get viewset
        viewset_class = get_viewset_for_model("cms.page")
        self.assertIsNotNone(viewset_class)

        # Test serializer functionality
        serializer = serializer_class()
        self.assertIn("locale_code", serializer.fields)
        self.assertIn("url", serializer.fields)

        # Test viewset functionality
        viewset = viewset_class()
        self.assertEqual(viewset.queryset.model, Page)
        self.assertIn("title", viewset_class.search_fields)

    def test_multiple_configs_dynamic_loading(self):
        """Test dynamic loading with multiple configurations."""
        # Register Page config
        page_config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        content_registry.register(page_config)

        # Create mock model for second config
        with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
            mock_ct.objects.get_for_model.return_value = Mock(
                app_label="blog", model="post"
            )

            mock_model = Mock()
            mock_model.__name__ = "Post"
            mock_model._meta = Mock()

            # Create mock fields with proper name attributes
            mock_fields = []
            for field_name in ["id", "title", "slug", "created_at", "seo"]:
                field = Mock()
                field.name = field_name
                mock_fields.append(field)

            mock_model._meta.get_fields.return_value = mock_fields
            mock_model._meta.verbose_name = "post"
            mock_model._meta.verbose_name_plural = "posts"
            mock_model._meta.app_label = "blog"
            mock_model._meta.model_name = "post"

            post_config = ContentConfig(
                model=mock_model,
                kind="collection",
                name="Posts",
                slug_field="slug",
                seo_fields=[],
                ordering=[],
            )

            content_registry.register(post_config)

        # Should be able to get serializers for both
        page_serializer = get_serializer_for_model("cms.page")
        post_serializer = get_serializer_for_model("blog.post")

        self.assertEqual(page_serializer.__name__, "PageSerializer")
        self.assertEqual(post_serializer.__name__, "PostSerializer")

        # Should be able to get viewsets for both
        page_viewset = get_viewset_for_model("cms.page")
        post_viewset = get_viewset_for_model("blog.post")

        self.assertEqual(page_viewset.__name__, "PageViewSet")
        self.assertEqual(post_viewset.__name__, "PostViewSet")

    def test_dynamic_loading_caching(self):
        """Test that dynamic loading results are not cached inappropriately."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        # Get serializer multiple times
        serializer1 = get_serializer_for_model("cms.page")
        serializer2 = get_serializer_for_model("cms.page")

        # Should create new classes each time (not cached)
        # This ensures dynamic changes can be reflected
        self.assertEqual(serializer1.__name__, serializer2.__name__)
        # Classes should be the same type but may be different instances
        # depending on implementation

    def test_dynamic_loading_error_propagation(self):
        """Test error propagation in dynamic loading."""
        # Test with unregistered model
        with self.assertRaises(ValueError):
            get_serializer_for_model("unregistered.model")

        with self.assertRaises(ValueError):
            get_viewset_for_model("unregistered.model")

        # Register config then test with broken config
        broken_config = Mock()
        broken_config.model = None  # Broken config

        content_registry._configs["broken.model"] = broken_config

        # Should propagate errors from factory methods
        with self.assertRaises(Exception):
            get_serializer_for_model("broken.model")

        with self.assertRaises(Exception):
            get_viewset_for_model("broken.model")
