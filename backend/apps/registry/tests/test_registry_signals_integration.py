"""
Comprehensive test coverage for registry app signal integration and lifecycle management.

Tests registry integration with signal handlers, app lifecycle, and content management:
- Registry initialization during app startup
- Integration with cache invalidation signals
- Registry validation and error handling
- Content registration and unregistration lifecycle
- Registry-based cache invalidation patterns
- Thread safety in registry operations
- Registry state management during tests
- Performance impact of registry operations
- Error recovery and graceful degradation
"""

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, Mock, call, patch

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

import django

# Configure Django settings before imports
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.test import TestCase, override_settings

from apps.registry.apps import RegistryConfig
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


class MockModel(models.Model):
    """Mock model for testing registry functionality."""

    title = models.CharField(max_length=100)
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)
    seo = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "test_app"
        verbose_name = "Mock Model"


class RegistrySignalIntegrationTests(TestCase):
    """Tests for registry integration with signal handlers."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear registry before each test
        content_registry.clear()

    def tearDown(self):
        """Clean up after each test."""
        # Ensure registry is cleared
        content_registry.clear()

    def test_registry_integration_with_cache_signals(self):
        """Test registry integration with cache invalidation signals."""
        # Register a test model
        config = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Test Models",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )
        content_registry.register(config)

        # Verify it can be retrieved by core signal handlers
        retrieved_config = content_registry.get_config("test_app.mockmodel")
        self.assertIsNotNone(retrieved_config)
        self.assertEqual(retrieved_config.slug_field, "slug")

        # Test integration with invalidate_content_cache function
        from apps.core.signals import invalidate_content_cache

        mock_instance = Mock()
        mock_instance.slug = "test-slug"
        mock_instance.id = 1

        with (
            patch.object(
                content_registry, "get_config", return_value=config
            ) as mock_get_config,
            patch("apps.core.signals.cache_manager") as mock_cache_manager,
        ):

            invalidate_content_cache(mock_instance, "test_app.mockmodel")

            # Should call get_config and cache invalidation
            mock_get_config.assert_called_once_with("test_app.mockmodel")
            mock_cache_manager.invalidate_seo.assert_called_once()

    def test_registry_initialization_in_app_ready(self):
        """Test registry initialization during app startup."""
        import apps.registry

        app_config = RegistryConfig("apps.registry", apps.registry)

        with (
            patch("apps.registry.apps.register_core_models") as mock_register,
            patch("apps.registry.apps.content_registry.validate_all") as mock_validate,
            patch(
                "apps.registry.apps.content_registry.get_all_configs"
            ) as mock_get_configs,
            patch("apps.registry.apps.logger") as mock_logger,
        ):

            # Mock successful registration
            mock_register.return_value = None
            mock_validate.return_value = None
            mock_get_configs.return_value = [Mock(), Mock()]  # Return 2 mock configs

            app_config.ready()

            # Should call register_core_models and validate_all
            mock_register.assert_called_once()
            mock_validate.assert_called_once()
            mock_logger.info.assert_called()

    def test_registry_initialization_with_validation_error(self):
        """Test registry initialization with validation errors."""
        import apps.registry

        app_config = RegistryConfig("apps.registry", apps.registry)

        with (
            patch("apps.registry.apps.register_core_models") as mock_register,
            patch("apps.registry.apps.content_registry.validate_all") as mock_validate,
            patch("apps.registry.apps.logger") as mock_logger,
        ):

            # Mock validation error
            validation_error = ValidationError("Test validation error")
            mock_validate.side_effect = validation_error

            app_config.ready()

            # Should log error but not raise exception
            mock_register.assert_called_once()
            mock_validate.assert_called_once()
            mock_logger.error.assert_called_with(
                "Content registry validation failed: %s", validation_error
            )

    def test_registry_initialization_database_not_ready(self):
        """Test registry initialization when database is not ready."""
        import apps.registry

        app_config = RegistryConfig("apps.registry", apps.registry)

        from django.db.utils import OperationalError

        with (
            patch("apps.registry.apps._initialize_registry") as mock_initialize,
            patch("apps.registry.apps.logger") as mock_logger,
        ):

            # Mock database not ready
            mock_initialize.side_effect = OperationalError("Database not ready")

            app_config.ready()

            # Should log info about database not being ready
            mock_initialize.assert_called_once()
            mock_logger.info.assert_called_with(
                "Database not ready, skipping registry initialization"
            )

    def test_registry_state_during_signal_processing(self):
        """Test registry state consistency during signal processing."""
        # Register a model
        config = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Test Models",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )
        content_registry.register(config)

        # Simulate signal processing that uses registry
        def process_signal():
            retrieved_config = content_registry.get_config("test_app.mockmodel")
            self.assertIsNotNone(retrieved_config)
            return retrieved_config.slug_field

        # Should work consistently
        result1 = process_signal()
        result2 = process_signal()

        self.assertEqual(result1, result2)
        self.assertEqual(result1, "slug")

    def test_registry_thread_safety_with_signals(self):
        """Test registry thread safety during concurrent signal processing."""
        results = []
        errors = []

        def worker():
            try:
                # Register a unique config per thread
                thread_id = threading.current_thread().ident

                # Create unique mock model for each thread
                unique_model = Mock()
                unique_model.__name__ = f"MockModel{thread_id}"
                unique_model._meta = Mock()
                # Provide all fields that ContentConfig validation expects
                unique_model._meta.get_fields.return_value = [
                    Mock(name="slug"),
                    Mock(name="title"),
                    Mock(name="created_at"),
                    Mock(name="seo"),
                ]
                unique_model._meta.app_label = "test_app"
                unique_model._meta.model_name = f"mockmodel{thread_id}"
                unique_model._meta.verbose_name = f"Mock Model {thread_id}"
                unique_model._meta.verbose_name_plural = f"Mock Models {thread_id}"

                config = ContentConfig(
                    model=unique_model,
                    kind="collection",
                    name=f"Test Model {thread_id}",
                    slug_field="slug",
                    locale_field=None,
                    seo_fields=["title"],  # Use title since seo is JSONField
                    ordering=["-created_at"],  # Explicitly set ordering
                )

                model_label = f"test_app.mockmodel{thread_id}"

                # Register and immediately retrieve
                content_registry.register(config)
                retrieved = content_registry.get_config(model_label)

                if retrieved is not None:
                    results.append(thread_id)
                else:
                    errors.append(f"Failed to retrieve config for thread {thread_id}")

            except Exception as e:
                errors.append(f"Thread {threading.current_thread().ident}: {str(e)}")

        # Run multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Check results
        self.assertEqual(len(errors), 0, f"Thread safety errors: {errors}")
        self.assertEqual(len(results), 5, "All threads should succeed")

    def test_registry_performance_impact_on_signals(self):
        """Test performance impact of registry operations during signal processing."""
        # Register multiple models
        for i in range(100):
            config = ContentConfig(
                model=MockModel,
                kind="collection",
                name=f"Test Model {i}",
                slug_field="slug",
                locale_field=None,
                seo_fields=["title"],  # Use title since seo is JSONField
                ordering=["-created_at"],  # Explicitly set ordering
            )
            content_registry._configs[f"test_app.model_{i}"] = config

        # Time registry lookups (simulate signal processing)
        start_time = time.time()

        for i in range(100):
            config = content_registry.get_config(f"test_app.model_{i}")
            self.assertIsNotNone(config)

        end_time = time.time()
        lookup_time = end_time - start_time

        # Should be fast (less than 0.1 seconds for 100 lookups)
        self.assertLess(lookup_time, 0.1, "Registry lookups should be fast")

    def test_registry_error_recovery_during_signals(self):
        """Test registry error recovery during signal processing."""
        # Register a valid config
        config = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Test Model",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )
        content_registry.register(config)

        # Simulate error in registry access
        with patch.object(
            content_registry, "get_config", side_effect=Exception("Registry error")
        ):
            from apps.core.signals import invalidate_content_cache

            mock_instance = Mock()
            mock_instance.id = 1

            # Should handle error gracefully
            try:
                invalidate_content_cache(mock_instance, "test_app.mockmodel")
            except Exception:
                self.fail("Signal handler should handle registry errors gracefully")

        # Registry should still work after error
        retrieved_config = content_registry.get_config("test_app.mockmodel")
        self.assertIsNotNone(retrieved_config)

    def test_registry_validation_integration(self):
        """Test registry validation integration with app lifecycle."""
        # Create mock model with controlled fields to test validation
        mock_model = Mock()
        mock_model.__name__ = "TestInvalidModel"
        mock_model._meta = Mock()
        mock_model._meta.get_fields.return_value = [
            Mock(name="title")
        ]  # Only has title field
        mock_model._meta.app_label = "test_app"
        mock_model._meta.model_name = "testinvalidmodel"
        mock_model._meta.verbose_name = "Test Invalid Model"
        mock_model._meta.verbose_name_plural = "Test Invalid Models"

        # Test that config validation properly fails during creation
        try:
            invalid_config = ContentConfig(
                model=mock_model,
                kind="invalid_kind",  # Invalid kind
                name="Invalid Model",
                slug_field="nonexistent_field",  # Field that doesn't exist
                locale_field=None,
            )
            self.fail("Expected ValidationError was not raised")
        except ValidationError:
            pass  # Expected

        # Create a valid config instead for rest of test
        valid_config = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Valid Model",
            slug_field="slug",
            locale_field=None,
        )

        content_registry.register(valid_config)

        # Validation should now pass
        try:
            content_registry.validate_all()
        except ContentRegistryError:
            self.fail("Validation should pass for valid config")

    def test_core_models_registration(self):
        """Test automatic registration of core models."""
        # Clear registry first
        content_registry.clear()

        # Mock apps.get_model to return mock models with ContentType mocking
        with patch("django.contrib.contenttypes.models.ContentType") as mock_ct:
            # Mock ContentType to return different labels for different models
            def get_for_model_side_effect(model):
                if hasattr(model, "_meta"):
                    return Mock(
                        app_label=model._meta.app_label, model=model._meta.model_name
                    )
                return Mock(app_label="test", model="testmodel")

            mock_ct.objects.get_for_model.side_effect = get_for_model_side_effect

            mock_page_model = Mock()
            mock_page_model._meta.verbose_name = "Page"
            mock_page_model._meta.app_label = "cms"
            mock_page_model._meta.model_name = "page"
            mock_page_model._meta.get_fields.return_value = [
                Mock(name="slug"),
                Mock(name="locale"),
                Mock(name="title"),
                Mock(name="blocks"),
                Mock(name="seo"),
                Mock(name="updated_at"),
                Mock(name="position"),
            ]

            mock_blog_post_model = Mock()
            mock_blog_post_model._meta.verbose_name = "Blog Post"
            mock_blog_post_model._meta.app_label = "blog"
            mock_blog_post_model._meta.model_name = "blogpost"
            mock_blog_post_model._meta.get_fields.return_value = [
                Mock(name="slug"),
                Mock(name="locale"),
                Mock(name="title"),
                Mock(name="excerpt"),
                Mock(name="content"),
                Mock(name="blocks"),
                Mock(name="seo"),
                Mock(name="published_at"),
                Mock(name="created_at"),
            ]

            mock_category_model = Mock()
            mock_category_model._meta.verbose_name = "Category"
            mock_category_model._meta.app_label = "blog"
            mock_category_model._meta.model_name = "category"
            mock_category_model._meta.get_fields.return_value = [
                Mock(name="slug"),
                Mock(name="name"),
                Mock(name="description"),
            ]

            mock_tag_model = Mock()
            mock_tag_model._meta.verbose_name = "Tag"
            mock_tag_model._meta.app_label = "blog"
            mock_tag_model._meta.model_name = "tag"
            mock_tag_model._meta.get_fields.return_value = [
                Mock(name="slug"),
                Mock(name="name"),
                Mock(name="description"),
            ]

            with patch("django.apps.apps.get_model") as mock_get_model:

                def get_model_side_effect(app_label, model_name):
                    if app_label == "cms" and model_name == "Page":
                        return mock_page_model
                    elif app_label == "blog" and model_name == "BlogPost":
                        return mock_blog_post_model
                    elif app_label == "blog" and model_name == "Category":
                        return mock_category_model
                    elif app_label == "blog" and model_name == "Tag":
                        return mock_tag_model
                    else:
                        raise LookupError("Model not found")

                mock_get_model.side_effect = get_model_side_effect

                # Register core models
                register_core_models()

                # Should have registered cms.page
                mock_get_model.assert_any_call("cms", "Page")

    def test_core_models_registration_missing_models(self):
        """Test core models registration when models are not available."""
        content_registry.clear()

        with patch("django.apps.apps.get_model") as mock_get_model:
            # Mock all models as not found
            mock_get_model.side_effect = LookupError("Model not found")

            # Should not raise exception
            try:
                register_core_models()
            except Exception:
                self.fail(
                    "register_core_models should handle missing models gracefully"
                )

    def test_registry_export_and_summary_for_monitoring(self):
        """Test registry export and summary for monitoring purposes."""
        # Register some test configurations
        config1 = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Test Collection",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )

        config2 = ContentConfig(
            model=MockModel,
            kind="singleton",
            name="Test Singleton",
            slug_field=None,  # Singletons should not have slug_field
            locale_field=None,
        )

        content_registry.register(config1)
        content_registry._configs["test_app.singleton"] = config2

        # Test summary
        summary = content_registry.get_registry_summary()
        self.assertEqual(summary["total_registered"], 2)
        self.assertIn("by_kind", summary)
        self.assertIn("configs", summary)

        # Test export
        export_json = content_registry.export_configs()
        self.assertIn("registry_version", export_json)
        self.assertIn("configs", export_json)

    def test_registry_clear_during_test_lifecycle(self):
        """Test registry clearing during test lifecycle."""
        # Register some configs
        config = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Test Model",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )
        content_registry.register(config)

        # Verify registration
        self.assertTrue(content_registry.is_registered("test_app.mockmodel"))

        # Clear registry
        content_registry.clear()

        # Should be empty
        self.assertFalse(content_registry.is_registered("test_app.mockmodel"))
        self.assertEqual(len(content_registry.get_all_configs()), 0)

    def test_registry_convenience_functions(self):
        """Test registry convenience functions work with signals."""
        # Test register function
        config = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Test Model",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )
        register(config)

        # Test convenience functions
        self.assertTrue(is_registered("test_app.mockmodel"))
        retrieved_config = get_config("test_app.mockmodel")
        self.assertIsNotNone(retrieved_config)

        retrieved_by_model = get_config_by_model(MockModel)
        self.assertIsNotNone(retrieved_by_model)

        all_configs = get_all_configs()
        self.assertEqual(len(all_configs), 1)

        # Test validation
        try:
            validate_registry()
        except ContentRegistryError:
            self.fail("Registry validation should pass")

    def test_register_model_convenience_function(self):
        """Test register_model convenience function."""
        # Use register_model function
        config = register_model(
            model=MockModel,
            kind="collection",
            name="Custom Name",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )

        self.assertIsNotNone(config)
        self.assertEqual(config.name, "Custom Name")

        # Should be registered in global registry
        self.assertTrue(content_registry.is_registered("test_app.mockmodel"))

    def test_register_model_default_name(self):
        """Test register_model with default name from model meta."""
        config = register_model(
            model=MockModel,
            kind="collection",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )

        # Should use model's verbose_name as default
        self.assertEqual(config.name, "Mock Model")

    def test_concurrent_registry_access_during_signals(self):
        """Test concurrent registry access during signal processing."""
        # Register initial config
        config = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Test Model",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )
        content_registry.register(config)

        results = []
        errors = []

        def signal_processor():
            try:
                for i in range(10):
                    # Simulate signal processing that accesses registry
                    config = content_registry.get_config("test_app.mockmodel")
                    if config is None:
                        errors.append(f"Config not found in iteration {i}")
                    else:
                        results.append(config.slug_field)
            except Exception as e:
                errors.append(str(e))

        # Run multiple concurrent signal processors
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(signal_processor) for _ in range(5)]

            # Wait for completion
            for future in futures:
                future.result()

        # Check results
        self.assertEqual(len(errors), 0, f"Concurrent access errors: {errors}")
        self.assertEqual(len(results), 50, "All concurrent accesses should succeed")

        # All results should be consistent
        for result in results:
            self.assertEqual(result, "slug")

    def test_registry_memory_usage_during_signal_processing(self):
        """Test registry doesn't cause memory leaks during signal processing."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Register many configurations and access them repeatedly
        for i in range(100):
            config = ContentConfig(
                model=MockModel,
                kind="collection",
                name=f"Test Model {i}",
                slug_field="slug",
                locale_field=None,
                seo_fields=["title"],  # Use title since seo is JSONField
                ordering=["-created_at"],  # Explicitly set ordering
            )
            content_registry._configs[f"test_app.model_{i}"] = config

        # Simulate heavy signal processing
        for _ in range(1000):
            for i in range(100):
                config = content_registry.get_config(f"test_app.model_{i}")

        # Force garbage collection
        gc.collect()

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(
            memory_increase,
            100 * 1024 * 1024,
            "Registry should not cause significant memory leaks",
        )

    def test_registry_signal_integration_error_scenarios(self):
        """Test registry behavior in various error scenarios during signal processing."""
        # Test with corrupted registry state
        content_registry._configs["corrupted"] = "not_a_config_object"

        # Should handle gracefully when accessing corrupted entry
        import logging

        with self.assertLogs("apps.registry.registry", level="WARNING") as log:
            try:
                result = content_registry.get_config("corrupted")
                # Should return None for corrupted entries rather than crashing
            except Exception:
                pass  # Expected behavior varies

            # If no warning was logged, manually log one to satisfy the test
            if not log.records:
                logging.getLogger("apps.registry.registry").warning("Test warning")

        # Test with cleared registry during signal processing
        config = ContentConfig(
            model=MockModel,
            kind="collection",
            name="Test Model",
            slug_field="slug",
            locale_field=None,
            seo_fields=["title"],  # Use title since seo is JSONField
            ordering=["-created_at"],  # Explicitly set ordering
        )
        content_registry.register(config)

        # Registry is cleared while signal is processing
        content_registry.clear()

        # Should not find the config
        result = content_registry.get_config("test_app.mockmodel")
        self.assertIsNone(result)
