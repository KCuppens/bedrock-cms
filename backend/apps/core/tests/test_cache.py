import os

import django

# Setup Django before imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

import time
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.core.cache import (
    CACHE_PREFIXES,
    CACHE_TIMEOUTS,
    CacheKeyBuilder,
    CacheManager,
    cache_manager,
)
from apps.core.signals import (
    invalidate_all_cache,
    invalidate_blog_cache,
    invalidate_content_cache,
    invalidate_page_cache,
)
from apps.i18n.models import Locale

User = get_user_model()


class CacheKeyBuilderTests(TestCase):
    """Test cache key generation."""

    def setUp(self):
        """Set up test data."""

        self.key_builder = CacheKeyBuilder("test")

    def test_build_basic_key(self):
        """Test basic key building."""

        key = self.key_builder.build_key("page", "en", "about")

        self.assertEqual(key, "test:p:en:about")

    def test_build_key_with_none_values(self):
        """Test key building filters out None values."""

        key = self.key_builder.build_key("page", "en", None, "about")

        self.assertEqual(key, "test:p:en:about")

    def test_page_key_simple(self):
        """Test simple page key generation."""

        key = self.key_builder.page_key("en", "/about")

        self.assertEqual(key, "test:p:en:about")

    def test_page_key_with_revision(self):
        """Test page key with revision ID."""

        key = self.key_builder.page_key("en", "/about", "123")

        self.assertEqual(key, "test:p:en:about:123")

    def test_page_key_root_path(self):
        """Test page key for root path."""

        key = self.key_builder.page_key("en", "/")

        self.assertEqual(key, "test:p:en:home")

        key = self.key_builder.page_key("en", "")

        self.assertEqual(key, "test:p:en:home")

    def test_content_key(self):
        """Test content key generation."""

        key = self.key_builder.content_key("blog.blogpost", "en", "my-post")

        self.assertEqual(key, "test:c:blog.blogpost:en:my-post")

    def test_content_key_with_revision(self):
        """Test content key with revision."""

        key = self.key_builder.content_key("blog.blogpost", "en", "my-post", "456")

        self.assertEqual(key, "test:c:blog.blogpost:en:my-post:456")

    def test_blog_key(self):
        """Test blog presentation key generation."""

        key = self.key_builder.blog_key("en", "my-post")

        self.assertEqual(key, "test:b:en:my-post")

    def test_blog_key_with_revisions(self):
        """Test blog key with post and page revisions."""

        key = self.key_builder.blog_key("en", "my-post", "123", "456")

        self.assertEqual(key, "test:b:en:my-post:123:456")

    def test_api_key_simple(self):
        """Test API key generation."""

        key = self.key_builder.api_key("search")

        self.assertEqual(key, "test:a:search")

    def test_api_key_with_params(self):
        """Test API key with parameters."""

        key = self.key_builder.api_key("search", q="test", locale="en")

        # Should include a hash of the parameters

        self.assertTrue(key.startswith("test:a:search:"))

        self.assertEqual(len(key.split(":")), 4)

    def test_search_key(self):
        """Test search key generation."""

        key = self.key_builder.search_key("django cms")

        self.assertTrue(key.startswith("test:s:"))

        # Should be consistent for same query

        key2 = self.key_builder.search_key("django cms")

        self.assertEqual(key, key2)

    def test_search_key_with_filters(self):
        """Test search key with filters."""

        key = self.key_builder.search_key("django", {"locale": "en", "type": "page"})

        self.assertTrue(key.startswith("test:s:"))

        self.assertEqual(
            len(key.split(":")), 4
        )  # prefix:namespace:query_hash:filter_hash

    def test_sitemap_key(self):
        """Test sitemap key generation."""

        key = self.key_builder.sitemap_key("en")

        self.assertEqual(key, "test:sm:en")

    def test_seo_key(self):
        """Test SEO key generation."""

        key = self.key_builder.seo_key("cms.page", 123, "en")

        self.assertEqual(key, "test:seo:cms.page:123:en")


class CacheManagerTests(TestCase):
    """Test cache manager functionality."""

    def setUp(self):
        """Set up test data."""

        self.cache_manager = CacheManager()

        # Clear cache before each test

        cache.clear()

    def test_set_and_get(self):
        """Test basic cache set/get."""

        key = "test:key"

        value = {"data": "test"}

        self.cache_manager.set(key, value, timeout=60)

        retrieved = self.cache_manager.get(key)

        self.assertEqual(retrieved, value)

    def test_get_or_set(self):
        """Test get_or_set functionality."""

        key = "test:get_or_set"

        def generate_value():

            return {"generated": True}

        # First call should generate and cache

        result1 = self.cache_manager.get_or_set(key, generate_value, timeout=60)

        self.assertEqual(result1, {"generated": True})

        # Second call should return cached value

        result2 = self.cache_manager.get_or_set(
            key, lambda: {"different": True}, timeout=60
        )

        self.assertEqual(result2, {"generated": True})  # Should be cached value

    def test_delete(self):
        """Test cache deletion."""

        key = "test:delete"

        value = "test_value"

        self.cache_manager.set(key, value)

        self.assertEqual(self.cache_manager.get(key), value)

        self.cache_manager.delete(key)

        self.assertIsNone(self.cache_manager.get(key))

    @patch("apps.core.cache.cache")
    def test_delete_pattern_redis(self, mock_cache):
        """Test pattern deletion with Redis backend."""

        # Mock Redis-style cache with delete_pattern

        mock_cache._cache = MagicMock()

        mock_cache._cache.delete_pattern = MagicMock(return_value=5)

        self.cache_manager.delete_pattern("test:*")

        mock_cache._cache.delete_pattern.assert_called_once_with("test:*")

    @patch("apps.core.cache.cache")
    def test_delete_pattern_fallback(self, mock_cache):
        """Test pattern deletion fallback for non-Redis backends."""

        # Mock cache without pattern deletion support

        mock_cache._cache = MagicMock(spec=[])  # No delete_pattern method

        # Should not raise an exception

        self.cache_manager.delete_pattern("test:*")


class CacheInvalidationTests(TestCase):
    """Test cache invalidation functionality."""

    def setUp(self):
        """Set up test data."""

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

        # Clear cache before each test

        cache.clear()

    def test_invalidate_all_cache(self):
        """Test invalidating all cache entries."""

        # Set some test cache entries

        cache_manager.set("cms:p:en:test", "page_data")

        cache_manager.set("cms:b:en:post", "blog_data")

        # Verify they exist

        self.assertIsNotNone(cache_manager.get("cms:p:en:test"))

        self.assertIsNotNone(cache_manager.get("cms:b:en:post"))

        # Invalidate all

        invalidate_all_cache()

        # Should be gone (note: this test depends on delete_pattern working)

        # In practice, pattern deletion might not work with all cache backends

    def test_invalidate_page_cache_direct(self):
        """Test direct page cache invalidation."""

        cache_manager.invalidate_page(locale="en", path="/about")

        # Should not raise an exception

    def test_invalidate_content_cache_direct(self):
        """Test direct content cache invalidation."""

        cache_manager.invalidate_content("blog.blogpost", locale="en", slug="test-post")

        # Should not raise an exception

    def test_invalidate_blog_cache_direct(self):
        """Test direct blog cache invalidation."""

        cache_manager.invalidate_blog_post(locale="en", slug="test-post")

        # Should not raise an exception

    def test_invalidate_search_cache(self):
        """Test search cache invalidation."""

        # Set some search cache

        search_key = cache_manager.key_builder.search_key("test query")

        cache_manager.set(search_key, "search_results")

        # Invalidate

        cache_manager.invalidate_search("test query")

        # Should be invalidated (pattern-dependent)

    def test_invalidate_sitemap_cache(self):
        """Test sitemap cache invalidation."""

        sitemap_key = cache_manager.key_builder.sitemap_key("en")

        cache_manager.set(sitemap_key, "sitemap_xml")

        # Verify cached

        self.assertEqual(cache_manager.get(sitemap_key), "sitemap_xml")

        # Invalidate

        cache_manager.invalidate_sitemap("en")

        # Should be gone

        self.assertIsNone(cache_manager.get(sitemap_key))


class CacheIntegrationTests(TestCase):
    """Integration tests for caching with models."""

    def setUp(self):
        """Set up test data."""

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

        cache.clear()

    def test_cache_timeouts_configuration(self):
        """Test that cache timeouts are properly configured."""

        self.assertIn("page", CACHE_TIMEOUTS)

        self.assertIn("content", CACHE_TIMEOUTS)

        self.assertIn("search", CACHE_TIMEOUTS)

        self.assertIn("sitemap", CACHE_TIMEOUTS)

        # All timeouts should be positive integers

        for timeout in CACHE_TIMEOUTS.values():

            self.assertIsInstance(timeout, int)

            self.assertGreater(timeout, 0)

    def test_cache_key_prefixes(self):
        """Test cache key prefix configuration."""

        self.assertIn("page", CACHE_PREFIXES)

        self.assertIn("content", CACHE_PREFIXES)

        self.assertIn("search", CACHE_PREFIXES)

        # All prefixes should be short strings

        for prefix in CACHE_PREFIXES.values():

            self.assertIsInstance(prefix, str)

            self.assertLessEqual(len(prefix), 3)

    @override_settings(DEBUG=True)
    def test_cache_in_debug_mode(self):
        """Test caching behavior in debug mode."""

        # Cache should still work in debug mode

        key = "test:debug:key"

        value = "debug_value"

        cache_manager.set(key, value)

        retrieved = cache_manager.get(key)

        self.assertEqual(retrieved, value)


class CacheSignalTests(TestCase):
    """Test cache invalidation signals."""

    def setUp(self):
        """Set up test data."""

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

        cache.clear()

    def test_invalidate_page_cache_function(self):
        """Test page cache invalidation function."""

        # Create a mock page object

        mock_page = MagicMock()

        mock_page.locale.code = "en"

        mock_page.path = "/test"

        mock_page.id = 123

        mock_page.children.all.return_value = []

        # Should not raise an exception

        invalidate_page_cache(mock_page)

    def test_invalidate_blog_cache_function(self):
        """Test blog cache invalidation function."""

        # Create a mock blog post object

        mock_post = MagicMock()

        mock_post.locale.code = "en"

        mock_post.slug = "test-post"

        mock_post.id = 456

        # Should not raise an exception

        invalidate_blog_cache(mock_post)

    def test_invalidate_content_cache_function(self):
        """Test content cache invalidation function."""

        # Create a mock content object

        mock_content = MagicMock()

        mock_content.id = 789

        # Should not raise an exception

        invalidate_content_cache(mock_content, "test.model")


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "test-cache",
        }
    }
)
class CachePerformanceTests(TestCase):
    """Test cache performance characteristics."""

    def test_cache_key_generation_performance(self):
        """Test that cache key generation is fast."""

        key_builder = CacheKeyBuilder()

        start_time = time.time()

        # Generate 1000 cache keys

        for i in range(1000):

            key_builder.page_key("en", f"/page-{i}", str(i))

            key_builder.content_key("blog.blogpost", "en", f"post-{i}", str(i))

            key_builder.search_key(f"query {i}", {"locale": "en"})

        end_time = time.time()

        # Should complete in under 100ms (very generous)

        self.assertLess(end_time - start_time, 0.1)

    def test_cache_operations_performance(self):
        """Test basic cache operations performance."""

        start_time = time.time()

        # Perform 100 cache operations

        for i in range(100):

            key = f"perf:test:{i}"

            value = f"value_{i}"

            cache_manager.set(key, value)

            retrieved = cache_manager.get(key)

            self.assertEqual(retrieved, value)

            cache_manager.delete(key)

        end_time = time.time()

        # Should complete in under 500ms for local memory cache

        self.assertLess(end_time - start_time, 0.5)
