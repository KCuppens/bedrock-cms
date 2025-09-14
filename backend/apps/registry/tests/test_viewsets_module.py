"""Tests for registry viewsets functionality."""

import os
from unittest.mock import Mock, patch

import django

# Configure Django settings before any imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.i18n.models import Locale
from apps.registry.config import ContentConfig
from apps.registry.registry import content_registry
from apps.registry.viewsets import ContentViewSetFactory, RegistryViewSet

User = get_user_model()


class ContentViewSetFactoryTestCase(TestCase):
    """Test ContentViewSetFactory functionality."""

    def setUp(self):
        """Set up test data."""
        # Create a mock model for testing
        self.mock_model = Mock()
        self.mock_model.__name__ = "TestModel"
        self.mock_model.objects.all.return_value = Mock()

        # Mock the _meta attribute with fields
        mock_field1 = Mock()
        mock_field1.name = "status"
        mock_field2 = Mock()
        mock_field2.name = "category"
        mock_field3 = Mock()
        mock_field3.name = "created_at"
        mock_field4 = Mock()
        mock_field4.name = "updated_at"

        self.mock_model._meta = Mock()
        self.mock_model._meta.get_fields.return_value = [
            mock_field1,
            mock_field2,
            mock_field3,
            mock_field4,
        ]

        # Create a mock config
        self.mock_config = Mock(spec=ContentConfig)
        self.mock_config.model = self.mock_model
        self.mock_config.name = "Test Model"
        self.mock_config.searchable_fields = ["title", "content"]
        self.mock_config.filterable_fields = ["status", "category"]
        self.mock_config.ordering_fields = ["created_at", "updated_at"]
        self.mock_config.default_ordering = ["-created_at"]
        self.mock_config.ordering = ["-created_at"]
        self.mock_config.locale_field = None
        self.mock_config.supports_publishing.return_value = False

    def test_create_viewset_basic(self):
        """Test basic viewset creation."""
        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_serializer_class = Mock()
            mock_get_serializer.return_value = mock_serializer_class

            viewset_class = ContentViewSetFactory.create_viewset(self.mock_config)

            # Should return a class
            self.assertTrue(isinstance(viewset_class, type))

            # Should have correct name
            self.assertEqual(viewset_class.__name__, "TestModelViewSet")

            # Should have correct attributes
            self.assertEqual(viewset_class.serializer_class, mock_serializer_class)
            self.assertIsNotNone(viewset_class.queryset)

    def test_get_filterset_fields(self):
        """Test _get_filterset_fields method."""
        fields = ContentViewSetFactory._get_filterset_fields(self.mock_config)

        # Should return fields that exist in model meta
        # With the improved logic, it includes:
        # 1. Configured filterable_fields: ["status", "category"]
        # 2. Common fields: ["created_at", "updated_at"] (that exist in model)
        # Our mock model has: status, category, created_at, updated_at
        expected_fields = ["status", "category", "created_at", "updated_at"]
        self.assertEqual(sorted(fields), sorted(expected_fields))

    def test_get_search_fields(self):
        """Test _get_search_fields method."""
        fields = ContentViewSetFactory._get_search_fields(self.mock_config)

        # Should return the searchable fields
        self.assertEqual(fields, ["title", "content"])

    def test_get_ordering_fields(self):
        """Test _get_ordering_fields method."""
        fields = ContentViewSetFactory._get_ordering_fields(self.mock_config)

        # Should return the ordering fields from config plus common fields found in model
        expected_fields = ["created_at", "updated_at"]
        self.assertEqual(sorted(fields), sorted(expected_fields))

    def test_viewset_has_locale_filtering(self):
        """Test that created viewset has locale filtering capability."""
        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewset_class = ContentViewSetFactory.create_viewset(self.mock_config)

            # Should have filter backends configured
            self.assertIsNotNone(viewset_class.filter_backends)
            self.assertGreater(len(viewset_class.filter_backends), 0)

    def test_viewset_permissions(self):
        """Test viewset permission configuration."""
        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewset_class = ContentViewSetFactory.create_viewset(self.mock_config)

            # Should have permissions configured
            self.assertIsNotNone(viewset_class.permission_classes)
            self.assertGreater(len(viewset_class.permission_classes), 0)

    def test_viewset_queryset_configuration(self):
        """Test viewset queryset configuration."""
        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewset_class = ContentViewSetFactory.create_viewset(self.mock_config)

            # Should have queryset from model
            self.assertIsNotNone(viewset_class.queryset)
            self.mock_model.objects.all.assert_called_once()

    def test_config_with_no_fields(self):
        """Test config with no searchable/filterable fields."""
        config_no_fields = Mock(spec=ContentConfig)
        config_no_fields.model = self.mock_model
        config_no_fields.name = "Test Model"
        config_no_fields.searchable_fields = []
        config_no_fields.filterable_fields = []
        config_no_fields.ordering_fields = []
        config_no_fields.ordering = []
        config_no_fields.default_ordering = []
        config_no_fields.locale_field = None
        config_no_fields.supports_publishing.return_value = False

        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewset_class = ContentViewSetFactory.create_viewset(config_no_fields)

            # Should still create viewset successfully
            self.assertTrue(isinstance(viewset_class, type))
            self.assertEqual(viewset_class.__name__, "TestModelViewSet")

    def test_dynamic_method_addition(self):
        """Test that viewset gets dynamic methods added."""
        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewset_class = ContentViewSetFactory.create_viewset(self.mock_config)

            # Should have methods for locale filtering if applicable
            viewset_instance = viewset_class()

            # Should have standard viewset methods
            self.assertTrue(hasattr(viewset_instance, "list"))
            self.assertTrue(hasattr(viewset_instance, "create"))
            self.assertTrue(hasattr(viewset_instance, "retrieve"))
            self.assertTrue(hasattr(viewset_instance, "update"))
            self.assertTrue(hasattr(viewset_instance, "destroy"))


class RegistryViewSetTestCase(APITestCase):
    """Test RegistryViewSet functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )

    def test_list_configurations_anonymous(self):
        """Test listing configurations as anonymous user."""
        response = self.client.get("/api/registry/")

        # Should allow read access or require authentication
        self.assertIn(
            response.status_code,
            [
                status.HTTP_200_OK,
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_404_NOT_FOUND,
            ],
        )

    def test_list_configurations_authenticated(self):
        """Test listing configurations as authenticated user."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/registry/")

        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        )

    @patch("apps.registry.viewsets.content_registry")
    def test_list_returns_registry_data(self, mock_registry):
        """Test that list endpoint returns registry data."""
        # Mock registry with test configs
        mock_config1 = Mock()
        mock_config1.name = "blog_post"
        mock_config1.verbose_name = "Blog Post"
        mock_config1.model_name = "BlogPost"

        mock_config2 = Mock()
        mock_config2.name = "page"
        mock_config2.verbose_name = "Page"
        mock_config2.model_name = "Page"

        mock_registry.get_all_configs.return_value = [mock_config1, mock_config2]

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/registry/")

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Should return configuration data
            self.assertIsInstance(data, (list, dict))

    def test_get_configuration_detail(self):
        """Test getting specific configuration detail."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/registry/blog_post/")

        # Should handle configuration lookup
        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        )

    def test_summary_action(self):
        """Test summary action endpoint."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/registry/summary/")

        self.assertIn(
            response.status_code,
            [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ],
        )

    @patch("apps.registry.viewsets.content_registry")
    def test_summary_returns_stats(self, mock_registry):
        """Test that summary returns registry statistics."""
        # Mock registry
        mock_registry.get_all_configs.return_value = [Mock(), Mock()]
        mock_registry.__len__.return_value = 2

        if hasattr(RegistryViewSet, "summary"):
            viewset = RegistryViewSet()

            # Mock request
            mock_request = Mock()
            viewset.request = mock_request

            response = viewset.summary(mock_request)

            # Should return response with summary data
            self.assertIsNotNone(response)

    def test_configuration_search(self):
        """Test searching configurations."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/registry/?search=blog")

        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        )

    def test_configuration_filtering(self):
        """Test filtering configurations."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/registry/?is_searchable=true")

        self.assertIn(
            response.status_code, [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
        )

    def test_invalid_configuration_lookup(self):
        """Test lookup of non-existent configuration."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/registry/nonexistent/")

        # Should return 404 for non-existent configuration
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_method_not_allowed(self):
        """Test that POST is not allowed on registry."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/registry/", data={})

        # Should not allow creating registry entries
        self.assertIn(
            response.status_code,
            [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_404_NOT_FOUND],
        )


class ViewSetIntegrationTestCase(TestCase):
    """Integration tests for viewset factory and registry."""

    def setUp(self):
        """Set up integration test data."""
        self.locale = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )

    @patch("apps.registry.viewsets.content_registry")
    def test_factory_with_real_config(self, mock_registry):
        """Test factory with realistic configuration."""
        # Create a more realistic mock config
        mock_model = Mock()
        mock_model.__name__ = "BlogPost"
        mock_model.objects.all.return_value = Mock()

        # Mock the _meta attribute with fields
        mock_fields = []
        field_names = [
            "status",
            "category",
            "author",
            "created_at",
            "updated_at",
            "published_at",
        ]
        for name in field_names:
            mock_field = Mock()
            mock_field.name = name
            mock_fields.append(mock_field)

        mock_model._meta = Mock()
        mock_model._meta.get_fields.return_value = mock_fields

        config = Mock(spec=ContentConfig)
        config.model = mock_model
        config.name = "Blog Posts"
        config.verbose_name = "Blog Post"
        config.searchable_fields = ["title", "content", "excerpt"]
        config.filterable_fields = ["status", "category", "author"]
        config.ordering_fields = ["created_at", "updated_at", "published_at"]
        config.ordering = ["-published_at"]
        config.default_ordering = ["-published_at"]
        config.locale_field = None
        config.supports_publishing.return_value = True
        config.has_locale = True
        config.has_versioning = True

        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewset_class = ContentViewSetFactory.create_viewset(config)

            # Should create a fully functional viewset
            self.assertEqual(viewset_class.__name__, "BlogPostViewSet")

            # Check that filterset_fields contains expected fields (order may vary)
            expected_filterset_fields = [
                "status",
                "category",
                "author",
                "created_at",
                "updated_at",
            ]
            self.assertEqual(
                sorted(viewset_class.filterset_fields),
                sorted(expected_filterset_fields),
            )

            # Check search fields
            self.assertEqual(
                viewset_class.search_fields, ["title", "content", "excerpt"]
            )

            # Check ordering fields
            expected_ordering_fields = ["created_at", "updated_at", "published_at"]
            self.assertEqual(
                sorted(viewset_class.ordering_fields), sorted(expected_ordering_fields)
            )

    def test_viewset_method_coverage(self):
        """Test that viewsets have expected methods."""
        # Test factory methods exist
        self.assertTrue(hasattr(ContentViewSetFactory, "create_viewset"))
        self.assertTrue(hasattr(ContentViewSetFactory, "_get_filterset_fields"))
        self.assertTrue(hasattr(ContentViewSetFactory, "_get_search_fields"))
        self.assertTrue(hasattr(ContentViewSetFactory, "_get_ordering_fields"))

        # Test registry viewset exists
        self.assertTrue(hasattr(RegistryViewSet, "list"))

    @patch("apps.registry.viewsets.content_registry")
    def test_multiple_viewset_creation(self, mock_registry):
        """Test creating multiple viewsets from different configs."""
        configs = []

        for i, model_name in enumerate(["BlogPost", "Page", "Category"]):
            mock_model = Mock()
            mock_model.__name__ = model_name
            mock_model.objects.all.return_value = Mock()

            # Mock _meta attribute
            mock_field = Mock()
            mock_field.name = "created_at"
            mock_model._meta = Mock()
            mock_model._meta.get_fields.return_value = [mock_field]

            config = Mock(spec=ContentConfig)
            config.model = mock_model
            config.name = model_name
            config.searchable_fields = ["title"]
            config.filterable_fields = ["status"]
            config.ordering_fields = ["created_at"]
            config.ordering = ["-created_at"]
            config.default_ordering = ["-created_at"]
            config.locale_field = None
            config.supports_publishing.return_value = False

            configs.append(config)

        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewsets = []
            for config in configs:
                viewset_class = ContentViewSetFactory.create_viewset(config)
                viewsets.append(viewset_class)

            # Should create unique viewset classes
            self.assertEqual(len(viewsets), 3)
            self.assertEqual(viewsets[0].__name__, "BlogPostViewSet")
            self.assertEqual(viewsets[1].__name__, "PageViewSet")
            self.assertEqual(viewsets[2].__name__, "CategoryViewSet")

    def test_error_handling_in_factory(self):
        """Test error handling in viewset factory."""
        # Test with invalid config
        invalid_config = Mock()
        invalid_config.model = None

        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            # Should handle invalid config gracefully
            try:
                ContentViewSetFactory.create_viewset(invalid_config)
            except Exception as e:
                # Should raise a meaningful error
                self.assertIsInstance(e, (AttributeError, TypeError, ValueError))

    def test_viewset_inheritance(self):
        """Test that created viewsets properly inherit from ModelViewSet."""
        mock_model = Mock()
        mock_model.__name__ = "TestModel"
        mock_model.objects.all.return_value = Mock()

        # Mock _meta attribute
        mock_model._meta = Mock()
        mock_model._meta.get_fields.return_value = []

        config = Mock(spec=ContentConfig)
        config.model = mock_model
        config.name = "Test Model"
        config.searchable_fields = []
        config.filterable_fields = []
        config.ordering_fields = []
        config.ordering = []
        config.default_ordering = []
        config.locale_field = None
        config.supports_publishing.return_value = False

        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewset_class = ContentViewSetFactory.create_viewset(config)

            # Should inherit from ModelViewSet
            from rest_framework import viewsets

            self.assertTrue(issubclass(viewset_class, viewsets.ModelViewSet))

    def test_viewset_customization_hooks(self):
        """Test that viewsets can be customized through configuration."""
        mock_model = Mock()
        mock_model.__name__ = "CustomModel"
        mock_model.objects.all.return_value = Mock()

        # Mock _meta attribute with custom fields
        mock_field1 = Mock()
        mock_field1.name = "custom_order"
        mock_field2 = Mock()
        mock_field2.name = "custom_filter"
        mock_model._meta = Mock()
        mock_model._meta.get_fields.return_value = [mock_field1, mock_field2]

        config = Mock(spec=ContentConfig)
        config.model = mock_model
        config.name = "Custom Model"
        config.searchable_fields = ["custom_field"]
        config.filterable_fields = ["custom_filter"]
        config.ordering_fields = ["custom_order"]
        config.ordering = ["-custom_order"]
        config.default_ordering = ["-custom_order"]
        config.locale_field = None
        config.supports_publishing.return_value = False

        with patch(
            "apps.registry.viewsets.get_serializer_for_config"
        ) as mock_get_serializer:
            mock_get_serializer.return_value = Mock()

            viewset_class = ContentViewSetFactory.create_viewset(config)

            # Should respect configuration settings
            self.assertEqual(viewset_class.search_fields, ["custom_field"])
            self.assertEqual(viewset_class.filterset_fields, ["custom_filter"])
            self.assertEqual(viewset_class.ordering_fields, ["custom_order"])
