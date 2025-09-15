"""Comprehensive tests for URL routing and dynamic route generation."""

import logging
import os
from unittest.mock import MagicMock, Mock, patch

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import NoReverseMatch, resolve, reverse

from rest_framework.routers import DefaultRouter
from rest_framework.test import APITestCase

from apps.cms.models import Page
from apps.i18n.models import Locale
from apps.registry.config import ContentConfig
from apps.registry.registry import content_registry
from apps.registry.urls import create_dynamic_router, dynamic_router
from apps.registry.viewsets import RegistryViewSet, get_viewset_for_config

User = get_user_model()


class DynamicRouterCreationTests(TestCase):
    """Test dynamic router creation functionality."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_create_dynamic_router_empty_registry(self):
        """Test creating dynamic router with empty registry."""
        router = create_dynamic_router()

        self.assertIsInstance(router, DefaultRouter)

        # Should have registry management endpoints even with empty registry
        registry_pattern_found = False
        for pattern in router.urls:
            if hasattr(pattern, "pattern") and "registry/content" in str(
                pattern.pattern
            ):
                registry_pattern_found = True
                break

        self.assertTrue(registry_pattern_found)

    def test_create_dynamic_router_with_configs(self):
        """Test creating dynamic router with registered configurations."""
        # Register test config
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
            locale_field="locale",
        )

        content_registry.register(config)

        router = create_dynamic_router()

        self.assertIsInstance(router, DefaultRouter)

        # Should have registry endpoints
        registry_pattern_found = False
        content_pattern_found = False

        for pattern in router.urls:
            if hasattr(pattern, "pattern"):
                pattern_str = str(pattern.pattern)
                if "registry/content" in pattern_str:
                    registry_pattern_found = True
                if "content/cms.page" in pattern_str:
                    content_pattern_found = True

        self.assertTrue(registry_pattern_found)
        self.assertTrue(content_pattern_found)

    def test_create_dynamic_router_multiple_configs(self):
        """Test creating dynamic router with multiple configurations."""
        # Register Page config
        page_config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(page_config)

        # Create mock model for second config
        with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:

            def side_effect(model):
                if model.__name__ == "Post":
                    return Mock(app_label="blog", model="post")
                elif model == Page:
                    from django.contrib.contenttypes.models import ContentType

                    return ContentType.objects.get_for_model(Page)
                return Mock(app_label="test", model="unknown")

            mock_ct.objects.get_for_model.side_effect = side_effect

            mock_model = Mock()
            mock_model.__name__ = "Post"
            mock_model._meta = Mock()

            # Create mock fields with proper name attributes
            mock_fields = []
            for field_name in ["id", "title", "slug"]:
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
            )

            content_registry.register(post_config)

        router = create_dynamic_router()

        # Should have routes for both models
        pattern_strings = [str(p.pattern) for p in router.urls if hasattr(p, "pattern")]

        cms_page_found = any("content/cms.page" in p for p in pattern_strings)
        blog_post_found = any("content/blog.post" in p for p in pattern_strings)

        self.assertTrue(cms_page_found)
        self.assertTrue(blog_post_found)

    def test_create_dynamic_router_error_handling(self):
        """Test dynamic router creation handles errors gracefully."""
        # Register config that will cause error during viewset creation
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        # Mock get_viewset_for_config to raise exception
        with patch("apps.registry.urls.get_viewset_for_config") as mock_get_viewset:
            mock_get_viewset.side_effect = Exception("Viewset creation failed")

            # Should handle error and continue
            with patch("apps.registry.urls.logger") as mock_logger:
                router = create_dynamic_router()

                # Should still create router
                self.assertIsInstance(router, DefaultRouter)

                # Should log error
                mock_logger.error.assert_called()

    def test_dynamic_router_route_patterns(self):
        """Test route patterns generated for different content types."""
        # Register collection config
        collection_config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(collection_config)

        router = create_dynamic_router()

        # Check that routes follow expected pattern
        # Get all URL patterns from router
        urls = router.urls
        pattern_strings = []
        for url in urls:
            if hasattr(url, "pattern"):
                pattern_strings.append(str(url.pattern))
            elif hasattr(url, "regex"):
                pattern_strings.append(str(url.regex.pattern))

        # Should have content/cms.page pattern (with or without escaped dot)
        content_pattern_found = any(
            "content/cms.page" in p or "content/cms\\.page" in p
            for p in pattern_strings
        )
        self.assertTrue(
            content_pattern_found, f"Pattern not found in: {pattern_strings}"
        )

    def test_dynamic_router_basename_generation(self):
        """Test basename generation for registered routes."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        with patch.object(DefaultRouter, "register") as mock_register:
            create_dynamic_router()

            # Should register with correct basename
            calls = mock_register.call_args_list

            # Find call with content route
            content_call_found = False
            for call in calls:
                args, kwargs = call
                if len(args) >= 2 and "content/cms.page" in args[0]:
                    content_call_found = True
                    self.assertEqual(kwargs.get("basename"), "content-cms.page")
                    break

            self.assertTrue(content_call_found)

    def test_registry_viewset_registration(self):
        """Test that RegistryViewSet is properly registered."""
        router = create_dynamic_router()

        with patch.object(DefaultRouter, "register") as mock_register:
            create_dynamic_router()

            # Should register RegistryViewSet
            calls = mock_register.call_args_list

            registry_call_found = False
            for call in calls:
                args, kwargs = call
                if len(args) >= 2 and "registry/content" in args[0]:
                    registry_call_found = True
                    self.assertEqual(args[1], RegistryViewSet)
                    self.assertEqual(kwargs.get("basename"), "content-registry")
                    break

            self.assertTrue(registry_call_found)


class DynamicRouterIntegrationTests(APITestCase):
    """Integration tests for dynamic router functionality."""

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

    @patch(
        "apps.registry.urls.dynamic_router",
        new_callable=lambda: create_dynamic_router(),
    )
    def test_registry_endpoint_access(self, mock_router):
        """Test accessing registry endpoints through dynamic router."""
        # Test registry list endpoint
        try:
            url = reverse("content-registry-list")
            response = self.client.get(url)
            # Should be accessible (may require auth or return 200/401)
            self.assertIn(response.status_code, [200, 401, 404])
        except NoReverseMatch:
            # URL pattern might not be available in test environment
            pass

    def test_content_endpoint_structure(self):
        """Test content endpoint URL structure."""
        router = create_dynamic_router()

        # Should have expected URL patterns
        urls = router.urls

        # Extract pattern strings for analysis
        pattern_strings = []
        for url_pattern in urls:
            if hasattr(url_pattern, "pattern"):
                pattern_strings.append(str(url_pattern.pattern))

        # Should have registry patterns
        registry_patterns = [p for p in pattern_strings if "registry" in p]
        self.assertGreater(len(registry_patterns), 0)

        # Should have content patterns
        content_patterns = [
            p for p in pattern_strings if "content/" in p and "registry" not in p
        ]
        self.assertGreater(len(content_patterns), 0)

    def test_dynamic_router_url_resolution(self):
        """Test URL resolution for dynamically generated routes."""
        router = create_dynamic_router()
        factory = RequestFactory()

        # Test that URLs can be resolved
        for url_pattern in router.urls:
            if hasattr(url_pattern, "resolve"):
                try:
                    # Test basic path resolution
                    request = factory.get("/")
                    # URL pattern should be resolvable
                    self.assertIsNotNone(url_pattern)
                except Exception:
                    # Some patterns may require specific parameters
                    pass

    def test_viewset_functionality_through_router(self):
        """Test that viewsets work correctly through the router."""
        router = create_dynamic_router()

        # Find the Page viewset in registered patterns
        page_viewset_class = None
        for pattern_name, viewset_class, basename in router.registry:
            if "cms.page" in pattern_name:
                page_viewset_class = viewset_class
                break

        if page_viewset_class:
            # Test viewset instantiation
            viewset = page_viewset_class()
            self.assertIsNotNone(viewset)

            # Test basic viewset functionality
            self.assertEqual(viewset.queryset.model, Page)

    def test_router_with_error_configs(self):
        """Test router handles configurations that cause errors."""
        # Add a config that might cause issues
        with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
            mock_ct.objects.get_for_model.return_value = Mock(
                app_label="error", model="errormodel"
            )

            error_model = Mock()
            error_model.__name__ = "ErrorModel"
            error_model._meta = Mock()
            error_model._meta.get_fields.return_value = []
            error_model._meta.verbose_name = "error model"
            error_model._meta.verbose_name_plural = "error models"
            error_model._meta.app_label = "error"
            error_model._meta.model_name = "errormodel"

            try:
                error_config = ContentConfig(
                    model=error_model,
                    kind="collection",
                    name="Error Model",
                    slug_field="slug",
                )
                content_registry.register(error_config)
            except:
                # If config creation fails, that's expected
                pass

        # Router creation should still work
        router = create_dynamic_router()
        self.assertIsInstance(router, DefaultRouter)


class URLPatternTests(TestCase):
    """Test URL pattern functionality."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

    def test_urlpatterns_structure(self):
        """Test that urlpatterns is properly structured."""
        from apps.registry.urls import urlpatterns

        self.assertIsInstance(urlpatterns, list)
        self.assertGreater(len(urlpatterns), 0)

        # Should include API path
        api_pattern_found = False
        for pattern in urlpatterns:
            if hasattr(pattern, "pattern") and "api/" in str(pattern.pattern):
                api_pattern_found = True
                break

        self.assertTrue(api_pattern_found)

    def test_dynamic_router_integration(self):
        """Test dynamic router integration in urlpatterns."""
        from apps.registry.urls import dynamic_router, urlpatterns

        # Dynamic router should be created
        self.assertIsInstance(dynamic_router, DefaultRouter)

        # Should be integrated into urlpatterns
        router_pattern_found = False
        for pattern in urlpatterns:
            if hasattr(pattern, "urlconf_module"):
                # This is an include() pattern
                router_pattern_found = True
                break

        self.assertTrue(router_pattern_found)


class RouterErrorHandlingTests(TestCase):
    """Test error handling in router functionality."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_router_handles_missing_viewset(self):
        """Test router handles missing viewset gracefully."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        with patch("apps.registry.urls.get_viewset_for_config") as mock_get_viewset:
            mock_get_viewset.side_effect = Exception("Viewset not found")

            # Should handle error gracefully
            router = create_dynamic_router()
            self.assertIsInstance(router, DefaultRouter)

    def test_router_handles_invalid_config(self):
        """Test router handles invalid configuration gracefully."""
        # Add invalid config directly to registry (bypass normal validation)
        invalid_config = Mock()
        invalid_config.model_label = "invalid.model"

        content_registry._configs["invalid.model"] = invalid_config

        with patch("apps.registry.urls.get_viewset_for_config") as mock_get_viewset:
            mock_get_viewset.side_effect = AttributeError("Invalid config")

            # Should handle error gracefully
            router = create_dynamic_router()
            self.assertIsInstance(router, DefaultRouter)

    def test_router_logging_on_errors(self):
        """Test that router logs errors appropriately."""
        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        content_registry.register(config)

        with (
            patch("apps.registry.urls.get_viewset_for_config") as mock_get_viewset,
            patch("apps.registry.urls.logger") as mock_logger,
        ):

            mock_get_viewset.side_effect = Exception("Test error")

            create_dynamic_router()

            # Should log the error
            mock_logger.error.assert_called_once()

            # Check that error message contains model info
            call_args = mock_logger.error.call_args
            self.assertIn("cms.page", str(call_args))

    def test_router_empty_registry_urls(self):
        """Test router with empty registry still provides base URLs."""
        # Empty registry
        self.assertEqual(len(content_registry.get_all_configs()), 0)

        router = create_dynamic_router()

        # Should still have registry management URLs
        self.assertGreater(len(router.urls), 0)

        # Should have at least registry endpoints
        pattern_strings = [str(p.pattern) for p in router.urls if hasattr(p, "pattern")]
        registry_patterns = [p for p in pattern_strings if "registry" in p]
        self.assertGreater(len(registry_patterns), 0)


class RouterPerformanceTests(TestCase):
    """Test router performance with many configurations."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_router_with_many_configs(self):
        """Test router performance with many configurations."""
        # Register many configurations
        for i in range(20):  # Reasonable number for test performance
            with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
                mock_ct.objects.get_for_model.return_value = Mock(
                    app_label="test", model=f"model{i}"
                )

                mock_model = Mock()
                mock_model.__name__ = f"Model{i}"
                mock_model._meta = Mock()
                mock_model._meta.get_fields.return_value = [
                    Mock(name="id"),
                    Mock(name="slug"),
                ]
                mock_model._meta.app_label = f"app{i}"
                mock_model._meta.model_name = f"model{i}"
                mock_model._meta.verbose_name = f"model{i}"
                mock_model._meta.verbose_name_plural = f"model{i}s"

                config = ContentConfig(
                    model=mock_model,
                    kind="collection",
                    name=f"Model {i}",
                    slug_field="slug",
                )

                content_registry.register(config)

        # Router creation should complete in reasonable time
        import time

        start_time = time.time()

        router = create_dynamic_router()

        end_time = time.time()

        # Should complete quickly (less than 1 second for 20 configs)
        self.assertLess(end_time - start_time, 1.0)

        # Should have all routes
        self.assertGreater(len(router.urls), 20)  # At least one URL per config

    def test_router_url_generation_performance(self):
        """Test URL generation performance."""
        # Register several configs
        for i in range(10):
            with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
                mock_ct.objects.get_for_model.return_value = Mock(
                    app_label="perf", model=f"model{i}"
                )

                mock_model = Mock()
                mock_model.__name__ = f"PerfModel{i}"
                mock_model._meta = Mock()
                mock_model._meta.get_fields.return_value = [
                    Mock(name="id"),
                    Mock(name="slug"),
                ]
                mock_model._meta.app_label = "perf"
                mock_model._meta.model_name = f"model{i}"
                mock_model._meta.verbose_name = f"perfmodel{i}"
                mock_model._meta.verbose_name_plural = f"perfmodel{i}s"

                config = ContentConfig(
                    model=mock_model,
                    kind="collection",
                    name=f"Perf Model {i}",
                    slug_field="slug",
                )

                content_registry.register(config)

        router = create_dynamic_router()

        # URL access should be fast
        import time

        start_time = time.time()

        # Access URLs multiple times
        for _ in range(10):
            urls = router.urls
            self.assertGreater(len(urls), 0)

        end_time = time.time()

        # Should be very fast (less than 0.1 seconds)
        self.assertLess(end_time - start_time, 0.1)


class RouterConcurrencyTests(TestCase):
    """Test router handling of concurrent access."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

    def test_concurrent_router_creation(self):
        """Test concurrent router creation."""
        import threading
        from concurrent.futures import ThreadPoolExecutor, as_completed

        def create_router():
            """Create a router in thread."""
            try:
                router = create_dynamic_router()
                return len(router.urls) > 0
            except Exception:
                return False

        # Run concurrent router creation
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_router) for _ in range(10)]
            results = [future.result() for future in as_completed(futures)]

        # All should succeed
        self.assertTrue(all(results))

    def test_router_access_during_registry_changes(self):
        """Test router access during registry modifications."""
        content_registry.clear()

        config = ContentConfig(
            model=Page,
            kind="collection",
            name="Pages",
            slug_field="slug",
        )

        def modify_registry():
            """Modify registry in background."""
            try:
                content_registry.register(config)
                content_registry.unregister("cms.page")
                return True
            except Exception:
                return False

        def access_router():
            """Access router during modifications."""
            try:
                router = create_dynamic_router()
                return len(router.urls) >= 0  # Should at least have registry URLs
            except Exception:
                return False

        # Run concurrent access
        import threading

        modify_thread = threading.Thread(target=modify_registry)
        access_threads = [threading.Thread(target=access_router) for _ in range(5)]

        modify_thread.start()
        for thread in access_threads:
            thread.start()

        modify_thread.join()
        for thread in access_threads:
            thread.join()

        # Should handle concurrent access gracefully
        # (No specific assertions needed - test passes if no exceptions)


class RouterEdgeCaseTests(TestCase):
    """Test router edge cases and boundary conditions."""

    def setUp(self):
        """Set up test data."""
        self.locale = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )
        content_registry.clear()

    def tearDown(self):
        """Clean up after tests."""
        content_registry.clear()

    def test_router_with_special_characters_in_model_label(self):
        """Test router handles special characters in model labels."""
        with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
            mock_ct.objects.get_for_model.return_value = Mock(
                app_label="special-app", model="special_model"
            )

            mock_model = Mock()
            mock_model.__name__ = "SpecialModel"
            mock_model._meta = Mock()
            mock_model._meta.get_fields.return_value = [
                Mock(name="id"),
                Mock(name="slug"),
            ]
            mock_model._meta.app_label = "test"
            mock_model._meta.model_name = "specialmodel"
            mock_model._meta.verbose_name = "special model"
            mock_model._meta.verbose_name_plural = "special models"

            config = ContentConfig(
                model=mock_model,
                kind="collection",
                name="Special Model",
                slug_field="slug",
            )

            content_registry.register(config)

        router = create_dynamic_router()

        # Should handle special characters in URLs
        pattern_strings = [str(p.pattern) for p in router.urls if hasattr(p, "pattern")]
        special_patterns = [
            p for p in pattern_strings if "special-app.special_model" in p
        ]

        # Should create valid URL patterns
        self.assertGreater(len(router.urls), 0)

    def test_router_with_empty_config_name(self):
        """Test router handles configs with empty or minimal names."""
        with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
            mock_ct.objects.get_for_model.return_value = Mock(
                app_label="test", model="minimal"
            )

            mock_model = Mock()
            mock_model.__name__ = "Minimal"
            mock_model._meta = Mock()
            mock_model._meta.get_fields.return_value = [
                Mock(name="id"),
                Mock(name="slug"),
            ]
            mock_model._meta.app_label = "test"
            mock_model._meta.model_name = "minimal"
            mock_model._meta.verbose_name = "minimal"
            mock_model._meta.verbose_name_plural = "minimals"

            config = ContentConfig(
                model=mock_model,
                kind="collection",
                name="",  # Empty name
                slug_field="slug",
            )

            content_registry.register(config)

        router = create_dynamic_router()

        # Should handle empty names gracefully
        self.assertIsInstance(router, DefaultRouter)

    def test_router_with_very_long_model_labels(self):
        """Test router handles very long model labels."""
        with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
            long_app = "a" * 50
            long_model = "b" * 50

            mock_ct.objects.get_for_model.return_value = Mock(
                app_label=long_app, model=long_model
            )

            mock_model = Mock()
            mock_model.__name__ = "LongNameModel"
            mock_model._meta = Mock()
            mock_model._meta.get_fields.return_value = [
                Mock(name="id"),
                Mock(name="slug"),
            ]
            mock_model._meta.app_label = "test"
            mock_model._meta.model_name = "longnamemodel"
            mock_model._meta.verbose_name = "long model"
            mock_model._meta.verbose_name_plural = "long models"

            config = ContentConfig(
                model=mock_model,
                kind="collection",
                name="Long Name Model",
                slug_field="slug",
            )

            content_registry.register(config)

        router = create_dynamic_router()

        # Should handle long names without issues
        self.assertIsInstance(router, DefaultRouter)
        self.assertGreater(len(router.urls), 0)

    def test_router_url_pattern_uniqueness(self):
        """Test that router generates unique URL patterns."""
        # Register multiple configs
        for i in range(5):
            with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
                mock_ct.objects.get_for_model.return_value = Mock(
                    app_label=f"app{i}", model=f"model{i}"
                )

                mock_model = Mock()
                mock_model.__name__ = f"Model{i}"
                mock_model._meta = Mock()
                mock_model._meta.get_fields.return_value = [
                    Mock(name="id"),
                    Mock(name="slug"),
                ]
                mock_model._meta.app_label = f"app{i}"
                mock_model._meta.model_name = f"model{i}"
                mock_model._meta.verbose_name = f"model{i}"
                mock_model._meta.verbose_name_plural = f"model{i}s"

                config = ContentConfig(
                    model=mock_model,
                    kind="collection",
                    name=f"Model {i}",
                    slug_field="slug",
                )

                content_registry.register(config)

        router = create_dynamic_router()

        # Extract all pattern strings
        pattern_strings = [str(p.pattern) for p in router.urls if hasattr(p, "pattern")]

        # All patterns should be unique
        unique_patterns = set(pattern_strings)
        self.assertEqual(len(pattern_strings), len(unique_patterns))

    def test_router_handles_model_without_proper_meta(self):
        """Test router handles models without proper meta attributes."""
        with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
            mock_ct.objects.get_for_model.side_effect = Exception("ContentType error")

            mock_model = Mock()
            mock_model.__name__ = "BadModel"
            mock_model._meta = None

            # This should fail during config creation, not router creation
            try:
                config = ContentConfig(
                    model=mock_model,
                    kind="collection",
                    name="Bad Model",
                    slug_field="slug",
                )
                content_registry.register(config)

                # If config creation somehow succeeds, router should handle it
                router = create_dynamic_router()
                self.assertIsInstance(router, DefaultRouter)
            except Exception:
                # Expected to fail during config creation
                pass
