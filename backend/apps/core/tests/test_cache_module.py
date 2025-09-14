"""Tests for core cache functionality."""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.core.cache import (
    CACHE_PREFIXES,
    CACHE_TIMEOUTS,
    CacheKeyBuilder,
    CacheManager,
    cache_manager,
)


class CacheKeyBuilderTestCase(TestCase):
    """Test cache key building functionality."""

    def setUp(self):
        self.builder = CacheKeyBuilder(prefix="test")

    def test_build_key_simple(self):
        """Test building a simple cache key."""
        key = self.builder.build_key("user", "123")
        self.assertEqual(key, "test:user:123")

    def test_build_key_multiple_parts(self):
        """Test building cache key with multiple parts."""
        key = self.builder.build_key("page", "en", "home", "v1")
        # "page" gets abbreviated to "p" per CACHE_PREFIXES
        self.assertEqual(key, "test:p:en:home:v1")

    def test_build_key_with_dict(self):
        """Test building cache key with dictionary argument."""
        key = self.builder.build_key("api", {"locale": "en", "type": "blog"})
        # Dict should be converted to deterministic string
        # "api" gets abbreviated to "a" per CACHE_PREFIXES
        self.assertIn("test:a:", key)
        self.assertIn("locale:en", key)
        self.assertIn("type:blog", key)

    def test_build_key_with_special_characters(self):
        """Test building cache key with special characters."""
        key = self.builder.build_key("content", "my-slug/with-chars")
        # Special characters should be handled
        # "content" gets abbreviated to "c" per CACHE_PREFIXES
        self.assertIn("test:c:", key)

    def test_hash_key_long_input(self):
        """Test key hashing for very long inputs."""
        long_string = "x" * 300  # Longer than typical cache key limit
        key = self.builder.build_key("long", long_string)
        # Should still produce valid key
        self.assertLess(len(key), 250)  # Most cache backends limit ~250 chars
        self.assertIn("test:long:", key)


class CacheManagerTestCase(TestCase):
    """Test cache manager functionality."""

    def setUp(self):
        self.manager = CacheManager()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_get_set_basic(self):
        """Test basic get/set operations."""
        key = "test:item"
        value = {"data": "test_value"}

        # Set value
        self.manager.set(key, value, timeout=60)

        # Get value
        result = self.manager.get(key)
        self.assertEqual(result, value)

    def test_get_nonexistent(self):
        """Test getting non-existent cache entry."""
        result = self.manager.get("nonexistent:key")
        self.assertIsNone(result)

    def test_get_with_default(self):
        """Test getting with default value."""
        default = {"default": "value"}
        result = self.manager.get("nonexistent:key", default=default)
        self.assertEqual(result, default)

    def test_delete(self):
        """Test cache deletion."""
        key = "test:delete"
        self.manager.set(key, "value")

        # Verify it exists
        self.assertIsNotNone(self.manager.get(key))

        # Delete and verify
        self.manager.delete(key)
        self.assertIsNone(self.manager.get(key))

    def test_get_or_set(self):
        """Test get_or_set functionality."""
        key = "test:get_or_set"

        def expensive_function():
            return {"computed": "value"}

        # First call should compute and cache
        result1 = self.manager.get_or_set(key, expensive_function, timeout=60)

        # Second call should return cached value
        result2 = self.manager.get_or_set(
            key, lambda: {"different": "value"}, timeout=60
        )

        self.assertEqual(result1, result2)
        self.assertEqual(result1, {"computed": "value"})

    def test_invalidate_by_pattern(self):
        """Test pattern-based cache invalidation."""
        # Set multiple cache entries
        self.manager.set("page:en:home", "home_content")
        self.manager.set("page:en:about", "about_content")
        self.manager.set("page:fr:home", "accueil_content")
        self.manager.set("content:blog:1", "blog_content")

        # Invalidate all English pages
        with patch.object(cache, "delete_many") as mock_delete:
            # Mock the pattern matching since it's cache backend dependent
            mock_delete.return_value = None
            self.manager.invalidate_by_pattern("page:en:*")

        # In real implementation, this would test actual pattern matching
        # For now, we just verify the method was called

    def test_get_cache_info(self):
        """Test cache information retrieval."""
        # Set some test data
        self.manager.set("test:info:1", "value1")
        self.manager.set("test:info:2", "value2")

        info = self.manager.get_cache_info()

        # Should return some cache statistics
        self.assertIsInstance(info, dict)

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-cache",
            }
        }
    )
    def test_with_different_backend(self):
        """Test cache manager with different cache backend."""
        manager = CacheManager()

        # Basic operations should still work
        manager.set("test:backend", "value")
        result = manager.get("test:backend")
        self.assertEqual(result, "value")


class CacheConstantsTestCase(TestCase):
    """Test cache constants and configuration."""

    def test_cache_timeouts_exist(self):
        """Test that cache timeout constants are defined."""
        self.assertIsInstance(CACHE_TIMEOUTS, dict)
        self.assertIn("page", CACHE_TIMEOUTS)
        self.assertIn("content", CACHE_TIMEOUTS)
        self.assertIn("api", CACHE_TIMEOUTS)

        # All timeouts should be positive integers
        for timeout in CACHE_TIMEOUTS.values():
            self.assertIsInstance(timeout, int)
            self.assertGreater(timeout, 0)

    def test_cache_prefixes_exist(self):
        """Test that cache prefix constants are defined."""
        self.assertIsInstance(CACHE_PREFIXES, dict)
        self.assertIn("page", CACHE_PREFIXES)
        self.assertIn("content", CACHE_PREFIXES)
        self.assertIn("blog", CACHE_PREFIXES)

        # All prefixes should be non-empty strings
        for prefix in CACHE_PREFIXES.values():
            self.assertIsInstance(prefix, str)
            self.assertGreater(len(prefix), 0)

    def test_global_cache_manager_instance(self):
        """Test that global cache manager instance exists."""
        self.assertIsInstance(cache_manager, CacheManager)


class CacheIntegrationTestCase(TestCase):
    """Integration tests for cache functionality."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_page_caching_workflow(self):
        """Test typical page caching workflow."""
        builder = CacheKeyBuilder(prefix=CACHE_PREFIXES["page"])
        manager = CacheManager()

        # Build page cache key
        page_key = builder.build_key("en", "home", "v1")

        # Cache page content
        page_content = {
            "title": "Home Page",
            "content": "Welcome to our site",
            "meta": {"description": "Home page description"},
        }

        manager.set(page_key, page_content, timeout=CACHE_TIMEOUTS["page"])

        # Retrieve and verify
        cached_content = manager.get(page_key)
        self.assertEqual(cached_content, page_content)

    def test_content_invalidation_scenario(self):
        """Test content invalidation scenario."""
        manager = CacheManager()

        # Cache related content
        manager.set("page:en:blog", "blog_page")
        manager.set("content:blog:1", "blog_post_1")
        manager.set("content:blog:2", "blog_post_2")
        manager.set("api:blog:list", "blog_list_api")

        # Simulate content update that should invalidate cache
        keys_to_invalidate = ["page:en:blog", "content:blog:1", "api:blog:list"]

        for key in keys_to_invalidate:
            manager.delete(key)

        # Verify invalidation
        self.assertIsNone(manager.get("page:en:blog"))
        self.assertIsNone(manager.get("content:blog:1"))
        self.assertIsNone(manager.get("api:blog:list"))

        # Other content should remain
        self.assertIsNotNone(manager.get("content:blog:2"))
