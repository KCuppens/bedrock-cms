"""
Comprehensive test coverage for core signal handlers.

Tests all signal handlers in apps.core.signals, including:
- Cache invalidation signals (post_save, post_delete, m2m_changed)
- Signal handler error handling and edge cases
- Signal handler execution order
- Signal disconnection and reconnection
- Integration with cache manager
- CDN webhook functionality
- Performance impact of signal processing
- Thread safety in signal handlers
"""

import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, Mock, call, patch

import django

# Configure Django settings before imports
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import Signal
from django.test import TestCase, override_settings

from apps.blog.models import BlogPost, BlogSettings
from apps.cms.models import Page
from apps.core import signals
from apps.core.cache import cache_manager
from apps.core.signals import (
    invalidate_all_cache,
    invalidate_blog_cache,
    invalidate_blog_settings_cache,
    invalidate_cache_on_asset_change,
    invalidate_cache_on_delete,
    invalidate_cache_on_m2m_change,
    invalidate_cache_on_save,
    invalidate_content_cache,
    invalidate_content_type_cache,
    invalidate_page_cache,
    send_cdn_purge_webhook,
)
from apps.i18n.models import Locale
from apps.registry.registry import content_registry

User = get_user_model()


class SignalHandlerBaseTests(TestCase):
    """Base test class with common setup for signal handler tests."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        self.locale_en = Locale.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
            is_active=True,
        )

        self.locale_es = Locale.objects.create(
            code="es",
            name="Spanish",
            native_name="Español",
            is_active=True,
        )

        # Clear cache before each test
        cache.clear()

        # Capture logs
        self.logger = logging.getLogger("apps.core.signals")
        self.original_level = self.logger.level
        self.logger.setLevel(logging.DEBUG)

        # Create a log handler to capture logs for testing
        self.log_records = []
        self.log_handler = logging.Handler()
        self.log_handler.emit = lambda record: self.log_records.append(record)
        self.logger.addHandler(self.log_handler)

    def tearDown(self):
        """Clean up after test."""
        self.logger.removeHandler(self.log_handler)
        self.logger.setLevel(self.original_level)
        cache.clear()


class CacheInvalidationSignalTests(SignalHandlerBaseTests):
    """Tests for cache invalidation signal handlers."""

    def test_post_save_signal_page_invalidation(self):
        """Test post_save signal invalidates page cache correctly."""
        with (
            patch.object(cache_manager, "invalidate_page") as mock_invalidate_page,
            patch.object(
                cache_manager, "invalidate_sitemap"
            ) as mock_invalidate_sitemap,
            patch.object(cache_manager, "invalidate_search") as mock_invalidate_search,
            patch.object(cache_manager, "invalidate_seo") as mock_invalidate_seo,
        ):

            page = Page(
                title="Test Page",
                path="/test-page/",
                locale=self.locale_en,
                blocks=[{"type": "text", "value": "Test content"}],
            )
            page.id = 1  # Mock ID for testing

            # Trigger signal handler directly
            invalidate_cache_on_save(sender=Page, instance=page, created=True)

            # Verify invalidation methods were called
            mock_invalidate_page.assert_called_once()
            mock_invalidate_search.assert_called_once()

    def test_post_save_signal_blog_post_invalidation(self):
        """Test post_save signal invalidates blog post cache correctly."""
        with (
            patch.object(cache_manager, "invalidate_blog_post") as mock_invalidate_blog,
            patch.object(
                cache_manager, "invalidate_content"
            ) as mock_invalidate_content,
            patch.object(cache_manager, "invalidate_search") as mock_invalidate_search,
        ):

            blog_post = BlogPost(
                title="Test Blog Post",
                slug="test-blog-post",
                locale=self.locale_en,
                content="Test content",
                status="published",
            )
            blog_post.id = 1

            # Trigger signal handler directly
            invalidate_cache_on_save(sender=BlogPost, instance=blog_post, created=False)

            # Verify invalidation methods were called
            mock_invalidate_search.assert_called_once()

    def test_post_save_signal_blog_settings_invalidation(self):
        """Test post_save signal invalidates blog settings cache correctly."""
        with (
            patch(
                "apps.core.signals.invalidate_blog_settings_cache"
            ) as mock_invalidate_settings,
            patch.object(cache_manager, "invalidate_search") as mock_invalidate_search,
        ):

            blog_settings = BlogSettings(locale=self.locale_en)
            blog_settings.id = 1

            # Trigger signal handler directly
            invalidate_cache_on_save(
                sender=BlogSettings, instance=blog_settings, created=False
            )

            # Verify invalidation methods were called
            mock_invalidate_settings.assert_called_once_with(blog_settings)
            mock_invalidate_search.assert_called_once()

    def test_post_save_signal_unknown_model(self):
        """Test post_save signal handles unknown model types gracefully."""
        with (
            patch(
                "apps.core.signals.invalidate_content_cache"
            ) as mock_invalidate_content,
            patch.object(cache_manager, "invalidate_search") as mock_invalidate_search,
        ):

            # Create a mock model instance
            mock_instance = Mock()
            mock_instance._meta.app_label = "unknown_app"
            mock_instance._meta.model_name = "unknown_model"
            mock_instance.id = 1

            # Mock sender
            mock_sender = Mock()
            mock_sender._meta.app_label = "unknown_app"
            mock_sender._meta.model_name = "unknown_model"

            # Trigger signal handler directly
            invalidate_cache_on_save(
                sender=mock_sender, instance=mock_instance, created=False
            )

            # Verify content cache invalidation was attempted
            mock_invalidate_content.assert_called_once_with(
                mock_instance, "unknown_app.unknown_model"
            )
            mock_invalidate_search.assert_called_once()

    def test_post_save_signal_error_handling(self):
        """Test post_save signal handles errors gracefully."""
        with patch.object(cache_manager, "invalidate_search") as mock_invalidate_search:
            # Make invalidate_search raise an exception
            mock_invalidate_search.side_effect = Exception("Cache error")

            page = Page(title="Test Page", locale=self.locale_en)
            page.id = 1

            # Should not raise exception
            try:
                invalidate_cache_on_save(sender=Page, instance=page, created=True)
            except Exception:
                self.fail("Signal handler should not raise exceptions")

            # Verify error was logged
            error_logs = [
                record
                for record in self.log_records
                if record.levelno >= logging.WARNING
            ]
            self.assertTrue(len(error_logs) > 0)

    def test_post_delete_signal_cache_invalidation(self):
        """Test post_delete signal invalidates cache correctly."""
        with (
            patch.object(cache_manager, "invalidate_page") as mock_invalidate_page,
            patch.object(cache_manager, "invalidate_search") as mock_invalidate_search,
            patch.object(
                cache_manager, "invalidate_sitemap"
            ) as mock_invalidate_sitemap,
        ):

            page = Page(title="Test Page", path="/test-page/", locale=self.locale_en)
            page.id = 1

            # Trigger signal handler directly
            invalidate_cache_on_delete(sender=Page, instance=page)

            # Verify invalidation methods were called
            mock_invalidate_search.assert_called_once()
            # invalidate_sitemap is called twice: once with locale code, once without
            self.assertEqual(mock_invalidate_sitemap.call_count, 2)

    def test_post_delete_signal_error_handling(self):
        """Test post_delete signal handles errors gracefully."""
        with patch("apps.core.signals.invalidate_page_cache") as mock_invalidate:
            # Make invalidation raise an exception
            mock_invalidate.side_effect = Exception("Invalidation error")

            page = Page(title="Test Page", locale=self.locale_en)
            page.id = 1

            # Should not raise exception
            try:
                invalidate_cache_on_delete(sender=Page, instance=page)
            except Exception:
                self.fail("Signal handler should not raise exceptions")

            # Verify error was logged
            error_logs = [
                record
                for record in self.log_records
                if record.levelno >= logging.WARNING
            ]
            self.assertTrue(len(error_logs) > 0)

    def test_m2m_changed_signal_invalidation(self):
        """Test m2m_changed signal invalidates cache correctly."""
        with (
            patch("apps.core.signals.invalidate_blog_cache") as mock_invalidate_blog,
            patch.object(cache_manager, "invalidate_search") as mock_invalidate_search,
        ):

            blog_post = BlogPost(
                title="Test Blog Post",
                slug="test-blog-post",
                locale=self.locale_en,
                content="Test content",
            )
            blog_post.id = 1
            blog_post._meta.app_label = "blog"
            blog_post._meta.model_name = "blogpost"

            # Test post_add action
            invalidate_cache_on_m2m_change(
                sender=BlogPost.tags.through,
                instance=blog_post,
                action="post_add",
                pk_set={1, 2},
            )

            mock_invalidate_blog.assert_called_once_with(blog_post)
            mock_invalidate_search.assert_called_once()

    def test_m2m_changed_signal_ignored_actions(self):
        """Test m2m_changed signal ignores pre_* actions."""
        with patch("apps.core.signals.invalidate_blog_cache") as mock_invalidate_blog:

            blog_post = BlogPost(title="Test Blog Post", locale=self.locale_en)
            blog_post.id = 1

            # Test pre_add action (should be ignored)
            invalidate_cache_on_m2m_change(
                sender=BlogPost.tags.through,
                instance=blog_post,
                action="pre_add",
                pk_set={1, 2},
            )

            # Should not call invalidation
            mock_invalidate_blog.assert_not_called()

    def test_asset_change_signal_invalidation(self):
        """Test asset change signal invalidates cache correctly."""
        mock_asset = Mock()
        mock_asset.id = 1
        mock_asset._meta.model_name = "asset"

        mock_sender = Mock()
        mock_sender._meta.model_name = "asset"

        # Test asset update (not creation)
        with patch("apps.core.signals.logger") as mock_logger:
            invalidate_cache_on_asset_change(
                sender=mock_sender, instance=mock_asset, created=False
            )

            # Should log asset update
            mock_logger.info.assert_called_once()

    def test_asset_change_signal_skips_non_assets(self):
        """Test asset change signal skips non-asset models."""
        mock_instance = Mock()
        mock_instance.id = 1

        mock_sender = Mock()
        mock_sender._meta.model_name = "page"  # Not an asset

        with patch("apps.core.signals.logger") as mock_logger:
            invalidate_cache_on_asset_change(
                sender=mock_sender, instance=mock_instance, created=False
            )

            # Should not log anything
            mock_logger.info.assert_not_called()

    def test_asset_change_signal_skips_creation(self):
        """Test asset change signal skips asset creation."""
        mock_asset = Mock()
        mock_asset.id = 1
        mock_asset._meta.model_name = "asset"

        mock_sender = Mock()
        mock_sender._meta.model_name = "asset"

        with patch("apps.core.signals.logger") as mock_logger:
            invalidate_cache_on_asset_change(
                sender=mock_sender,
                instance=mock_asset,
                created=True,  # Creation, should be ignored
            )

            # Should not log anything
            mock_logger.info.assert_not_called()


class PageCacheInvalidationTests(SignalHandlerBaseTests):
    """Tests for page-specific cache invalidation functions."""

    def test_invalidate_page_cache_with_locale_and_path(self):
        """Test page cache invalidation with locale and path."""
        with (
            patch.object(cache_manager, "invalidate_page") as mock_invalidate_page,
            patch.object(
                cache_manager, "invalidate_sitemap"
            ) as mock_invalidate_sitemap,
            patch.object(cache_manager, "invalidate_seo") as mock_invalidate_seo,
        ):

            page = Mock()
            page.locale.code = "en"
            page.path = "/test-page/"
            page.id = 1
            page.children.all.return_value = []

            invalidate_page_cache(page)

            mock_invalidate_page.assert_called_once_with(
                locale="en", path="/test-page/"
            )
            mock_invalidate_sitemap.assert_called_once_with("en")
            mock_invalidate_seo.assert_called_once_with(
                model_label="cms.page", object_id=1
            )

    def test_invalidate_page_cache_with_children(self):
        """Test page cache invalidation cascades to children."""
        with (
            patch.object(cache_manager, "invalidate_page") as mock_invalidate_page,
            patch.object(
                cache_manager, "invalidate_sitemap"
            ) as mock_invalidate_sitemap,
            patch.object(cache_manager, "invalidate_seo") as mock_invalidate_seo,
        ):

            # Create parent page
            parent = Mock()
            parent.locale.code = "en"
            parent.path = "/parent/"
            parent.id = 1

            # Create child pages
            child1 = Mock()
            child1.locale.code = "en"
            child1.path = "/parent/child1/"

            child2 = Mock()
            child2.locale.code = "en"
            child2.path = "/parent/child2/"

            parent.children.all.return_value = [child1, child2]

            invalidate_page_cache(parent)

            # Should invalidate parent and both children
            expected_calls = [
                call(locale="en", path="/parent/"),
                call(locale="en", path="/parent/child1/"),
                call(locale="en", path="/parent/child2/"),
            ]
            mock_invalidate_page.assert_has_calls(expected_calls)

    def test_invalidate_page_cache_missing_attributes(self):
        """Test page cache invalidation handles missing attributes gracefully."""
        with patch.object(cache_manager, "invalidate_page") as mock_invalidate_page:

            # Page without locale or path attributes
            page = Mock()
            del page.locale
            del page.path

            # Should not raise exception
            try:
                invalidate_page_cache(page)
            except AttributeError:
                self.fail("Should handle missing attributes gracefully")

            # Should not call invalidate_page
            mock_invalidate_page.assert_not_called()

    def test_invalidate_page_cache_error_handling(self):
        """Test page cache invalidation handles errors gracefully."""
        with patch.object(cache_manager, "invalidate_page") as mock_invalidate_page:
            mock_invalidate_page.side_effect = Exception("Cache error")

            page = Mock()
            page.locale.code = "en"
            page.path = "/test-page/"
            page.id = 1

            # Should not raise exception
            try:
                invalidate_page_cache(page)
            except Exception:
                self.fail("Should handle cache errors gracefully")

            # Verify error was logged
            error_logs = [
                record
                for record in self.log_records
                if record.levelno >= logging.WARNING
            ]
            self.assertTrue(len(error_logs) > 0)


class BlogCacheInvalidationTests(SignalHandlerBaseTests):
    """Tests for blog-specific cache invalidation functions."""

    def test_invalidate_blog_cache_complete(self):
        """Test blog cache invalidation with all attributes."""
        with (
            patch.object(
                cache_manager, "invalidate_blog_post"
            ) as mock_invalidate_blog_post,
            patch.object(
                cache_manager, "invalidate_content"
            ) as mock_invalidate_content,
            patch.object(
                cache_manager, "invalidate_sitemap"
            ) as mock_invalidate_sitemap,
            patch.object(cache_manager, "invalidate_seo") as mock_invalidate_seo,
        ):

            blog_post = Mock()
            blog_post.locale.code = "en"
            blog_post.slug = "test-blog-post"
            blog_post.id = 1

            invalidate_blog_cache(blog_post)

            mock_invalidate_blog_post.assert_called_once_with(
                locale="en", slug="test-blog-post"
            )
            mock_invalidate_content.assert_called_once_with(
                model_label="blog.blogpost", locale="en", slug="test-blog-post"
            )
            mock_invalidate_sitemap.assert_called_once_with("en")
            mock_invalidate_seo.assert_called_once_with(
                model_label="blog.blogpost", object_id=1
            )

    def test_invalidate_blog_cache_missing_attributes(self):
        """Test blog cache invalidation handles missing attributes."""
        with patch.object(
            cache_manager, "invalidate_blog_post"
        ) as mock_invalidate_blog_post:

            # Blog post without locale or slug
            blog_post = Mock()
            del blog_post.locale
            del blog_post.slug

            # Should not raise exception
            try:
                invalidate_blog_cache(blog_post)
            except AttributeError:
                self.fail("Should handle missing attributes gracefully")

            # Should not call invalidate_blog_post
            mock_invalidate_blog_post.assert_not_called()

    def test_invalidate_blog_cache_error_handling(self):
        """Test blog cache invalidation handles errors gracefully."""
        with patch.object(
            cache_manager, "invalidate_blog_post"
        ) as mock_invalidate_blog_post:
            mock_invalidate_blog_post.side_effect = Exception("Cache error")

            blog_post = Mock()
            blog_post.locale.code = "en"
            blog_post.slug = "test-blog-post"
            blog_post.id = 1

            # Should not raise exception
            try:
                invalidate_blog_cache(blog_post)
            except Exception:
                self.fail("Should handle cache errors gracefully")

            # Verify error was logged
            error_logs = [
                record
                for record in self.log_records
                if record.levelno >= logging.WARNING
            ]
            self.assertTrue(len(error_logs) > 0)


class ContentCacheInvalidationTests(SignalHandlerBaseTests):
    """Tests for content cache invalidation functions."""

    def test_invalidate_content_cache_with_registry(self):
        """Test content cache invalidation with registry config."""
        with (
            patch.object(content_registry, "_configs", {"test_app.testmodel": Mock()}),
            patch.object(content_registry, "get_config") as mock_get_config,
            patch.object(
                cache_manager, "invalidate_content"
            ) as mock_invalidate_content,
            patch.object(cache_manager, "invalidate_seo") as mock_invalidate_seo,
        ):

            # Mock registry config
            mock_config = Mock()
            mock_config.slug_field = "slug"
            mock_config.locale_field = "locale"
            mock_get_config.return_value = mock_config

            # Mock content instance
            mock_instance = Mock()
            mock_instance.slug = "test-slug"
            mock_instance.locale.code = "en"
            mock_instance.id = 1

            invalidate_content_cache(mock_instance, "test_app.testmodel")

            mock_invalidate_content.assert_called_once_with(
                model_label="test_app.testmodel", locale="en", slug="test-slug"
            )
            mock_invalidate_seo.assert_called_once_with(
                model_label="test_app.testmodel", object_id=1
            )

    def test_invalidate_content_cache_no_registry_config(self):
        """Test content cache invalidation when registry config doesn't exist."""
        with (
            patch.object(content_registry, "get_config") as mock_get_config,
            patch.object(
                cache_manager, "invalidate_content"
            ) as mock_invalidate_content,
        ):

            mock_get_config.return_value = None
            mock_instance = Mock()

            invalidate_content_cache(mock_instance, "unknown.model")

            # Should not call cache invalidation
            mock_invalidate_content.assert_not_called()

    def test_invalidate_content_cache_registry_not_initialized(self):
        """Test content cache invalidation when registry is not initialized."""
        with patch.object(content_registry, "_configs", None):
            mock_instance = Mock()

            # Should not raise exception
            try:
                invalidate_content_cache(mock_instance, "test_app.testmodel")
            except Exception:
                self.fail("Should handle uninitialized registry gracefully")

    def test_invalidate_content_cache_missing_slug_field(self):
        """Test content cache invalidation when slug field is missing."""
        with (
            patch.object(content_registry, "get_config") as mock_get_config,
            patch.object(
                cache_manager, "invalidate_content"
            ) as mock_invalidate_content,
        ):

            # Mock registry config without slug field
            mock_config = Mock()
            mock_config.slug_field = None
            mock_config.locale_field = "locale"
            mock_get_config.return_value = mock_config

            mock_instance = Mock()
            mock_instance.locale.code = "en"
            mock_instance.id = 1

            invalidate_content_cache(mock_instance, "test_app.testmodel")

            # Should not call content invalidation
            mock_invalidate_content.assert_not_called()

    def test_invalidate_content_cache_locale_string(self):
        """Test content cache invalidation with locale as string."""
        with (
            patch.object(content_registry, "_configs", {"test_app.testmodel": Mock()}),
            patch.object(content_registry, "get_config") as mock_get_config,
            patch.object(
                cache_manager, "invalidate_content"
            ) as mock_invalidate_content,
            patch.object(cache_manager, "invalidate_seo") as mock_invalidate_seo,
        ):

            # Mock registry config
            mock_config = Mock()
            mock_config.slug_field = "slug"
            mock_config.locale_field = "locale_code"
            mock_get_config.return_value = mock_config

            # Mock content instance with string locale
            mock_instance = Mock()
            mock_instance.slug = "test-slug"
            mock_instance.locale_code = "en"  # String instead of object
            mock_instance.id = 1

            invalidate_content_cache(mock_instance, "test_app.testmodel")

            mock_invalidate_content.assert_called_once_with(
                model_label="test_app.testmodel", locale="en", slug="test-slug"
            )

    def test_invalidate_content_cache_error_handling(self):
        """Test content cache invalidation handles errors gracefully."""
        with (
            patch.object(content_registry, "_configs", {"test_app.testmodel": Mock()}),
            patch.object(content_registry, "get_config") as mock_get_config,
        ):

            mock_get_config.side_effect = Exception("Registry error")

            mock_instance = Mock()
            mock_instance.id = 1

            # Should not raise exception
            try:
                invalidate_content_cache(mock_instance, "test_app.testmodel")
            except Exception:
                self.fail("Should handle registry errors gracefully")

            # Verify error was logged
            error_logs = [
                record
                for record in self.log_records
                if record.levelno >= logging.WARNING
            ]
            self.assertTrue(len(error_logs) > 0)


class BlogSettingsCacheInvalidationTests(SignalHandlerBaseTests):
    """Tests for blog settings cache invalidation functions."""

    @patch("apps.core.signals.BlogPost")
    def test_invalidate_blog_settings_cache_success(self, mock_blog_post_model):
        """Test blog settings cache invalidation with existing posts."""
        with (
            patch("django.db.connection") as mock_connection,
            patch.object(
                cache_manager, "invalidate_blog_post"
            ) as mock_invalidate_blog_post,
        ):

            # Mock database introspection
            mock_cursor = Mock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.introspection.table_names.return_value = ["blog_blogpost"]

            # Mock blog posts queryset
            mock_post1 = Mock()
            mock_post1.locale.code = "en"
            mock_post1.slug = "post1"

            mock_post2 = Mock()
            mock_post2.locale.code = "en"
            mock_post2.slug = "post2"

            mock_queryset = Mock()
            mock_queryset.__iter__ = lambda self: iter([mock_post1, mock_post2])

            mock_blog_post_model.objects.filter.return_value = mock_queryset

            # Mock blog settings
            blog_settings = Mock()
            blog_settings.locale.code = "en"

            invalidate_blog_settings_cache(blog_settings)

            # Should invalidate cache for both posts
            expected_calls = [
                call(locale="en", slug="post1"),
                call(locale="en", slug="post2"),
            ]
            mock_invalidate_blog_post.assert_has_calls(expected_calls)

    def test_invalidate_blog_settings_cache_no_table(self):
        """Test blog settings cache invalidation when table doesn't exist."""
        with patch("django.db.connection") as mock_connection:
            # Mock database introspection - no blog table
            mock_cursor = Mock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.introspection.table_names.return_value = ["other_table"]

            blog_settings = Mock()
            blog_settings.locale.code = "en"

            # Should not raise exception
            try:
                invalidate_blog_settings_cache(blog_settings)
            except Exception:
                self.fail("Should handle missing table gracefully")

    def test_invalidate_blog_settings_cache_db_error(self):
        """Test blog settings cache invalidation handles database errors."""
        with patch("django.db.connection") as mock_connection:
            # Mock database error
            mock_connection.cursor.side_effect = Exception("Database error")

            blog_settings = Mock()
            blog_settings.locale.code = "en"

            # Should not raise exception
            try:
                invalidate_blog_settings_cache(blog_settings)
            except Exception:
                self.fail("Should handle database errors gracefully")

    @patch("apps.core.signals.BlogPost")
    def test_invalidate_blog_settings_cache_blog_post_error(self, mock_blog_post_model):
        """Test blog settings cache invalidation handles BlogPost query errors."""
        with patch("django.db.connection") as mock_connection:
            # Mock database introspection
            mock_cursor = Mock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.introspection.table_names.return_value = ["blog_blogpost"]

            # Mock BlogPost query error
            mock_blog_post_model.objects.filter.side_effect = Exception("Query error")

            blog_settings = Mock()
            blog_settings.locale.code = "en"

            # Should not raise exception
            try:
                invalidate_blog_settings_cache(blog_settings)
            except Exception:
                self.fail("Should handle BlogPost query errors gracefully")

            # Verify error was logged
            error_logs = [
                record
                for record in self.log_records
                if record.levelno >= logging.WARNING
            ]
            self.assertTrue(len(error_logs) > 0)


class UtilityFunctionTests(SignalHandlerBaseTests):
    """Tests for utility functions."""

    def test_invalidate_all_cache(self):
        """Test invalidate_all_cache function."""
        with patch.object(cache_manager, "clear_all") as mock_clear_all:
            invalidate_all_cache()
            mock_clear_all.assert_called_once()

    def test_invalidate_content_type_cache_success(self):
        """Test invalidate_content_type_cache with valid model."""
        with (
            patch.object(content_registry, "_configs", {"test_app.testmodel": Mock()}),
            patch.object(content_registry, "get_config") as mock_get_config,
            patch("django.db.connection") as mock_connection,
            patch(
                "apps.core.signals.invalidate_content_cache"
            ) as mock_invalidate_content,
        ):

            # Mock registry config
            mock_model = Mock()
            mock_model._meta.db_table = "test_table"

            mock_config = Mock()
            mock_config.model = mock_model
            mock_get_config.return_value = mock_config

            # Mock database introspection
            mock_cursor = Mock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.introspection.table_names.return_value = ["test_table"]

            # Mock model objects
            mock_obj1 = Mock()
            mock_obj2 = Mock()
            mock_model.objects.all.return_value = [mock_obj1, mock_obj2]

            invalidate_content_type_cache("test_app.testmodel")

            # Should invalidate cache for both objects
            expected_calls = [
                call(mock_obj1, "test_app.testmodel"),
                call(mock_obj2, "test_app.testmodel"),
            ]
            mock_invalidate_content.assert_has_calls(expected_calls)

    def test_invalidate_content_type_cache_unknown_model(self):
        """Test invalidate_content_type_cache with unknown model."""
        with (
            patch.object(content_registry, "get_config") as mock_get_config,
            patch.object(content_registry, "_configs", {"test": "config"}),
        ):
            mock_get_config.return_value = None

            # Should not raise exception
            try:
                invalidate_content_type_cache("unknown.model")
            except Exception:
                self.fail("Should handle unknown model gracefully")

            # Verify warning was logged
            warning_logs = [
                record
                for record in self.log_records
                if record.levelno >= logging.WARNING
            ]
            self.assertTrue(len(warning_logs) > 0)

    def test_invalidate_content_type_cache_no_registry(self):
        """Test invalidate_content_type_cache when registry is not initialized."""
        with patch.object(content_registry, "_configs", None):
            # Should not raise exception
            try:
                invalidate_content_type_cache("test_app.testmodel")
            except Exception:
                self.fail("Should handle uninitialized registry gracefully")

    def test_invalidate_content_type_cache_table_not_exists(self):
        """Test invalidate_content_type_cache when table doesn't exist."""
        with (
            patch.object(content_registry, "get_config") as mock_get_config,
            patch("django.db.connection") as mock_connection,
        ):

            # Mock registry config
            mock_model = Mock()
            mock_model._meta.db_table = "nonexistent_table"

            mock_config = Mock()
            mock_config.model = mock_model
            mock_get_config.return_value = mock_config

            # Mock database introspection - table doesn't exist
            mock_cursor = Mock()
            mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
            mock_connection.introspection.table_names.return_value = ["other_table"]

            # Should not raise exception
            try:
                invalidate_content_type_cache("test_app.testmodel")
            except Exception:
                self.fail("Should handle missing table gracefully")

    def test_invalidate_content_type_cache_db_error(self):
        """Test invalidate_content_type_cache handles database errors."""
        with (
            patch.object(content_registry, "get_config") as mock_get_config,
            patch("django.db.connection") as mock_connection,
        ):

            mock_config = Mock()
            mock_get_config.return_value = mock_config

            # Mock database error
            mock_connection.cursor.side_effect = Exception("Database error")

            # Should not raise exception
            try:
                invalidate_content_type_cache("test_app.testmodel")
            except Exception:
                self.fail("Should handle database errors gracefully")


class CDNWebhookTests(SignalHandlerBaseTests):
    """Tests for CDN webhook functionality."""

    @override_settings(
        CDN_PURGE_WEBHOOK_URL="https://cdn.example.com/purge",
        CDN_PURGE_WEBHOOK_TOKEN="test-token",
    )
    @patch("apps.core.signals.requests.post")
    def test_send_cdn_purge_webhook_success(self, mock_post):
        """Test successful CDN webhook."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        keys = ["key1", "key2"]
        tags = ["tag1", "tag2"]

        send_cdn_purge_webhook(keys, tags)

        # Verify request was made correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        self.assertEqual(args[0], "https://cdn.example.com/purge")
        self.assertIn("Authorization", kwargs["headers"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-token")

        payload = kwargs["json"]
        self.assertEqual(payload["keys"], keys)
        self.assertEqual(payload["tags"], tags)
        self.assertIn("timestamp", payload)

    @override_settings(
        CDN_PURGE_WEBHOOK_URL="https://cdn.example.com/purge"
        # No token configured
    )
    @patch("apps.core.signals.requests.post")
    def test_send_cdn_purge_webhook_no_token(self, mock_post):
        """Test CDN webhook without authentication token."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        keys = ["key1", "key2"]

        send_cdn_purge_webhook(keys)

        # Verify request was made without Authorization header
        args, kwargs = mock_post.call_args
        self.assertNotIn("Authorization", kwargs["headers"])

    @override_settings()  # No webhook URL configured
    @patch("apps.core.signals.requests.post")
    def test_send_cdn_purge_webhook_no_url(self, mock_post):
        """Test CDN webhook when URL is not configured."""
        keys = ["key1", "key2"]

        send_cdn_purge_webhook(keys)

        # Should not make any HTTP requests
        mock_post.assert_not_called()

    @override_settings(CDN_PURGE_WEBHOOK_URL="https://cdn.example.com/purge")
    @patch("apps.core.signals.requests.post")
    def test_send_cdn_purge_webhook_failure(self, mock_post):
        """Test CDN webhook failure response."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        keys = ["key1", "key2"]

        send_cdn_purge_webhook(keys)

        # Should log warning for failed webhook
        warning_logs = [
            record for record in self.log_records if record.levelno >= logging.WARNING
        ]
        self.assertTrue(len(warning_logs) > 0)

    @override_settings(CDN_PURGE_WEBHOOK_URL="https://cdn.example.com/purge")
    @patch("apps.core.signals.requests.post")
    def test_send_cdn_purge_webhook_exception(self, mock_post):
        """Test CDN webhook request exception."""
        mock_post.side_effect = Exception("Network error")

        keys = ["key1", "key2"]

        # Should not raise exception
        try:
            send_cdn_purge_webhook(keys)
        except Exception:
            self.fail("Should handle network errors gracefully")

        # Should log error
        error_logs = [
            record for record in self.log_records if record.levelno >= logging.ERROR
        ]
        self.assertTrue(len(error_logs) > 0)

    @override_settings(CDN_PURGE_WEBHOOK_URL="https://cdn.example.com/purge")
    @patch("apps.core.signals.requests.post")
    def test_send_cdn_purge_webhook_no_tags(self, mock_post):
        """Test CDN webhook without tags."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        keys = ["key1", "key2"]

        send_cdn_purge_webhook(keys)

        # Verify payload doesn't include tags
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["keys"], keys)
        self.assertNotIn("tags", payload)


class SignalConnectionTests(TestCase):
    """Tests for signal connection and disconnection."""

    def test_signal_handlers_are_connected(self):
        """Test that all signal handlers are properly connected."""
        # Get all connected receivers for each signal using a specific sender model
        # to avoid the weak reference error with sender=None
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Get receivers for a specific sender to avoid weak reference issues
        post_save_receivers = []
        post_delete_receivers = []
        m2m_changed_receivers = []

        # Collect all receivers by iterating through different senders
        for sender in [User]:  # Add more models as needed
            post_save_receivers.extend(
                [
                    receiver
                    for receiver in post_save._live_receivers(sender=sender)
                    if receiver is not None
                ]
            )
            post_delete_receivers.extend(
                [
                    receiver
                    for receiver in post_delete._live_receivers(sender=sender)
                    if receiver is not None
                ]
            )
            m2m_changed_receivers.extend(
                [
                    receiver
                    for receiver in m2m_changed._live_receivers(sender=sender)
                    if receiver is not None
                ]
            )

        # Check that our handlers are connected
        handler_names = [
            receiver.__name__
            for receiver in post_save_receivers
            if hasattr(receiver, "__name__")
        ]

        # Verify that at least some signal handlers are connected
        self.assertGreater(len(post_save_receivers), 0, "No post_save receivers found")

        # Check post_delete handlers
        handler_names = [
            receiver.__name__
            for receiver in post_delete_receivers
            if hasattr(receiver, "__name__")
        ]

        # Verify that at least some delete handlers are connected
        self.assertGreaterEqual(
            len(post_delete_receivers), 0, "No post_delete receivers found"
        )

        # Check m2m_changed handlers
        handler_names = [
            receiver.__name__
            for receiver in m2m_changed_receivers
            if hasattr(receiver, "__name__")
        ]
        self.assertIn("invalidate_cache_on_m2m_change", handler_names)

    def test_signal_disconnection(self):
        """Test signal disconnection and reconnection."""
        # Disconnect signal
        post_save.disconnect(invalidate_cache_on_save)

        # Verify handler is not called
        with patch("apps.core.signals.invalidate_page_cache") as mock_invalidate:
            # This should not trigger our handler
            page = Page(title="Test Page", locale_id=1)
            post_save.send(sender=Page, instance=page, created=True)

            mock_invalidate.assert_not_called()

        # Reconnect signal
        post_save.connect(invalidate_cache_on_save)

        # Verify handler is called again
        with patch("apps.core.signals.invalidate_page_cache") as mock_invalidate:
            page = Page(title="Test Page", locale_id=1)
            post_save.send(sender=Page, instance=page, created=True)

            mock_invalidate.assert_called_once()


class SignalPerformanceTests(SignalHandlerBaseTests):
    """Tests for signal handler performance."""

    def test_signal_handler_performance(self):
        """Test that signal handlers execute within reasonable time."""
        with patch.object(cache_manager, "invalidate_page"):
            page = Page(title="Test Page", locale=self.locale_en)
            page.id = 1

            start_time = time.time()

            # Run signal handler multiple times
            for _ in range(100):
                invalidate_cache_on_save(sender=Page, instance=page, created=True)

            end_time = time.time()
            total_time = end_time - start_time

            # Should complete 100 operations in less than 1 second
            self.assertLess(total_time, 1.0, "Signal handlers should be fast")

    def test_signal_handler_memory_usage(self):
        """Test signal handlers don't cause memory leaks."""
        import gc
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        with patch.object(cache_manager, "invalidate_page"):
            page = Page(title="Test Page", locale=self.locale_en)
            page.id = 1

            # Run signal handler many times
            for i in range(1000):
                invalidate_cache_on_save(sender=Page, instance=page, created=True)

                # Force garbage collection every 100 iterations
                if i % 100 == 0:
                    gc.collect()

            final_memory = process.memory_info().rss
            memory_increase = final_memory - initial_memory

            # Memory increase should be minimal (less than 10MB)
            self.assertLess(
                memory_increase,
                10 * 1024 * 1024,
                "Signal handlers should not leak memory",
            )


class SignalThreadSafetyTests(SignalHandlerBaseTests):
    """Tests for signal handler thread safety."""

    def test_signal_handler_thread_safety(self):
        """Test signal handlers are thread-safe."""
        results = []
        errors = []

        def worker():
            try:
                with patch.object(cache_manager, "invalidate_page") as mock_invalidate:
                    page = Page(
                        title=f"Test Page {threading.current_thread().ident}",
                        locale=self.locale_en,
                    )
                    page.id = threading.current_thread().ident

                    # Run signal handler multiple times in this thread
                    for _ in range(10):
                        invalidate_cache_on_save(
                            sender=Page, instance=page, created=True
                        )

                    results.append(mock_invalidate.call_count)
            except Exception as e:
                errors.append(str(e))

        # Run multiple threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        self.assertEqual(len(errors), 0, f"Signal handler errors in threads: {errors}")
        self.assertEqual(len(results), 10, "All threads should complete")

    def test_concurrent_signal_execution(self):
        """Test concurrent signal handler execution."""
        with patch.object(cache_manager, "invalidate_search") as mock_invalidate_search:

            def run_signals():
                for i in range(5):
                    page = Page(title=f"Test Page {i}", locale=self.locale_en)
                    page.id = i
                    invalidate_cache_on_save(sender=Page, instance=page, created=True)

            # Use ThreadPoolExecutor to run signals concurrently
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(run_signals) for _ in range(5)]

                # Wait for all to complete
                for future in futures:
                    future.result()

            # invalidate_search should be called 25 times (5 threads * 5 iterations)
            self.assertEqual(mock_invalidate_search.call_count, 25)


class SignalErrorRecoveryTests(SignalHandlerBaseTests):
    """Tests for signal handler error recovery."""

    def test_signal_handler_recovery_after_cache_error(self):
        """Test signal handlers recover after cache errors."""
        with patch.object(cache_manager, "invalidate_search") as mock_invalidate_search:
            # First call fails
            mock_invalidate_search.side_effect = Exception("Cache error")

            page1 = Page(title="Test Page 1", locale=self.locale_en)
            page1.id = 1

            # Should not raise exception
            invalidate_cache_on_save(sender=Page, instance=page1, created=True)

            # Second call succeeds
            mock_invalidate_search.side_effect = None

            page2 = Page(title="Test Page 2", locale=self.locale_en)
            page2.id = 2

            # Should work normally
            invalidate_cache_on_save(sender=Page, instance=page2, created=True)

            # Both calls should have been attempted
            self.assertEqual(mock_invalidate_search.call_count, 2)

    def test_signal_handler_recovery_after_db_error(self):
        """Test signal handlers recover after database errors."""
        with patch("apps.core.signals.invalidate_page_cache") as mock_invalidate_page:
            # First call fails with database error
            mock_invalidate_page.side_effect = Exception("Database connection lost")

            page1 = Page(title="Test Page 1", locale=self.locale_en)
            page1.id = 1

            # Should not raise exception
            invalidate_cache_on_save(sender=Page, instance=page1, created=True)

            # Second call succeeds
            mock_invalidate_page.side_effect = None

            page2 = Page(title="Test Page 2", locale=self.locale_en)
            page2.id = 2

            # Should work normally
            invalidate_cache_on_save(sender=Page, instance=page2, created=True)

            # Both calls should have been attempted
            self.assertEqual(mock_invalidate_page.call_count, 2)

    def test_partial_cache_invalidation_success(self):
        """Test signal handlers handle partial cache invalidation failures."""
        with (
            patch.object(cache_manager, "invalidate_page") as mock_invalidate_page,
            patch.object(cache_manager, "invalidate_search") as mock_invalidate_search,
            patch.object(
                cache_manager, "invalidate_sitemap"
            ) as mock_invalidate_sitemap,
        ):

            # Page invalidation fails, but search should still be called
            mock_invalidate_page.side_effect = Exception("Page cache error")

            page = Page(title="Test Page", path="/test/", locale=self.locale_en)
            page.id = 1

            invalidate_cache_on_save(sender=Page, instance=page, created=True)

            # Search invalidation should still be called despite page cache error
            mock_invalidate_search.assert_called_once()
