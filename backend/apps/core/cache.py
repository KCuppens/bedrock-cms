"""
Cache utilities and key management for CMS.

Provides consistent cache key generation and invalidation strategies.
"""

# mypy: ignore-errors

import hashlib
from typing import Optional, List, Union, Dict, Any
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

# Cache TTL settings
CACHE_TIMEOUTS = {
    "page": 60 * 60,  # 1 hour
    "content": 60 * 30,  # 30 minutes
    "api": 60 * 15,  # 15 minutes
    "search": 60 * 60 * 24,  # 24 hours
    "sitemap": 60 * 60 * 6,  # 6 hours
    "seo": 60 * 60 * 2,  # 2 hours
}

# Cache key prefixes
CACHE_PREFIXES = {
    "page": "p",
    "content": "c",
    "blog": "b",
    "search": "s",
    "api": "a",
    "sitemap": "sm",
    "seo": "seo",
}


class CacheKeyBuilder:
    """
    Builds consistent cache keys across the CMS.

    Key format: {prefix}:{namespace}:{key_parts}
    """

    def __init__(self, prefix: str = "cms"):
        self.prefix = prefix

    def build_key(self, namespace: str, *parts: Union[str, int]) -> str:
        """
        Build a cache key from namespace and parts.

        Args:
            namespace: Key namespace (e.g., 'page', 'content')
            *parts: Key components to join

        Returns:
            Formatted cache key
        """
        # Convert all parts to strings and filter out None values
        clean_parts = [str(part) for part in parts if part is not None]
        key_suffix = ":".join(clean_parts)

        # Get prefix for namespace
        ns_prefix = CACHE_PREFIXES.get(namespace, namespace[:2])

        return f"{self.prefix}:{ns_prefix}:{key_suffix}"

    def page_key(
        self, locale: str, path: str, revision_id: Optional[Union[str, int]] = None
    ) -> str:
        """
        Build cache key for a page.

        Format: cms:p:{locale}:{path}:{revision_id}
        """
        # Normalize path (remove leading/trailing slashes for consistency)
        clean_path = path.strip("/")
        if not clean_path:
            clean_path = "home"

        parts = [locale, clean_path]
        if revision_id:
            parts.append(revision_id)

        return self.build_key("page", *parts)

    def content_key(
        self,
        model_label: str,
        locale: str,
        slug: str,
        revision_id: Optional[Union[str, int]] = None,
    ) -> str:
        """
        Build cache key for registry content.

        Format: cms:c:{model_label}:{locale}:{slug}:{revision_id}
        """
        parts = [model_label, locale, slug]
        if revision_id:
            parts.append(revision_id)

        return self.build_key("content", *parts)

    def blog_key(
        self,
        locale: str,
        slug: str,
        post_rev: Optional[Union[str, int]] = None,
        page_rev: Optional[Union[str, int]] = None,
    ) -> str:
        """
        Build cache key for blog post presentation.

        Format: cms:b:{locale}:{slug}:{post_rev}:{page_rev}
        """
        parts = [locale, slug]
        if post_rev:
            parts.append(post_rev)
        if page_rev:
            parts.append(page_rev)

        return self.build_key("blog", *parts)

    def api_key(self, endpoint: str, **params) -> str:
        """
        Build cache key for API responses.

        Format: cms:a:{endpoint}:{param_hash}
        """
        # Create a hash of the parameters for consistent key generation
        if params:
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
            param_hash = hashlib.md5(
                param_str.encode(), usedforsecurity=False
            ).hexdigest()[:8]
            return self.build_key("api", endpoint, param_hash)
        else:
            return self.build_key("api", endpoint)

    def search_key(self, query: str, filters: Dict[str, Any] = None) -> str:
        """
        Build cache key for search results.

        Format: cms:s:{query_hash}:{filter_hash}
        """
        # Hash the query for consistent keys
        query_hash = hashlib.md5(query.encode(), usedforsecurity=False).hexdigest()[:8]

        if filters:
            filter_str = "&".join(
                f"{k}={v}" for k, v in sorted(filters.items()) if v is not None
            )
            filter_hash = hashlib.md5(
                filter_str.encode(), usedforsecurity=False
            ).hexdigest()[:8]
            return self.build_key("search", query_hash, filter_hash)
        else:
            return self.build_key("search", query_hash)

    def sitemap_key(self, locale: str) -> str:
        """
        Build cache key for sitemap.

        Format: cms:sm:{locale}
        """
        return self.build_key("sitemap", locale)

    def seo_key(self, model_label: str, object_id: Union[str, int], locale: str) -> str:
        """
        Build cache key for SEO data.

        Format: cms:seo:{model_label}:{object_id}:{locale}
        """
        return self.build_key("seo", model_label, object_id, locale)


class CacheManager:
    """
    High-level cache management with invalidation support.
    """

    def __init__(self, key_builder: Optional[CacheKeyBuilder] = None):
        self.key_builder = key_builder or CacheKeyBuilder()

    def get(self, key: str, default=None, version=None):
        """Get value from cache."""
        return cache.get(key, default, version=version)

    def set(self, key: str, value, timeout: Optional[int] = None, version=None):
        """Set value in cache with appropriate timeout."""
        if timeout is None:
            # Try to determine timeout from key pattern
            for cache_type, default_timeout in CACHE_TIMEOUTS.items():
                if f":{CACHE_PREFIXES.get(cache_type, cache_type)}:" in key:
                    timeout = default_timeout
                    break
            else:
                timeout = CACHE_TIMEOUTS["api"]  # Default fallback

        return cache.set(key, value, timeout, version=version)

    def delete(self, key: str, version=None):
        """Delete value from cache."""
        return cache.delete(key, version=version)

    def delete_pattern(self, pattern: str):
        """
        Delete all keys matching a pattern.

        Note: This requires a cache backend that supports pattern deletion,
        like Redis. For other backends, this is a no-op.
        """
        try:
            # Try Redis-style pattern deletion
            if hasattr(cache, "_cache") and hasattr(cache._cache, "delete_pattern"):
                return cache._cache.delete_pattern(pattern)
            elif hasattr(cache, "delete_pattern"):
                return cache.delete_pattern(pattern)
            else:
                # Fallback: iterate through known keys (not efficient)
                # This is mainly for development/testing with local cache
                pass
        except Exception:
            # If pattern deletion fails, ignore silently
            # Individual key invalidation will still work
            pass

    def get_or_set(
        self, key: str, callable_func, timeout: Optional[int] = None, version=None
    ):
        """Get from cache or set using callable if not found."""
        value = self.get(key, version=version)
        if value is None:
            value = callable_func()
            self.set(key, value, timeout=timeout, version=version)
        return value

    def invalidate_page(
        self, locale: str = None, path: str = None, page_id: int = None
    ):
        """
        Invalidate page cache entries.

        Args:
            locale: Page locale
            path: Page path
            page_id: Page ID (will look up path/locale if not provided)
        """
        keys_to_invalidate = []

        if locale and path:
            # Invalidate specific page
            base_key = self.key_builder.page_key(locale, path)
            keys_to_invalidate.append(base_key)

            # Also invalidate with any potential revision IDs
            pattern = f"{base_key}:*"
            self.delete_pattern(pattern)

        elif page_id:
            # Look up page and invalidate
            try:
                from apps.cms.models import Page

                page = Page.objects.get(id=page_id)
                self.invalidate_page(locale=page.locale.code, path=page.path)
            except:
                pass  # Page not found, nothing to invalidate

        # Delete specific keys
        for key in keys_to_invalidate:
            self.delete(key)

    def invalidate_content(
        self,
        model_label: str,
        locale: str = None,
        slug: str = None,
        object_id: int = None,
    ):
        """
        Invalidate content cache entries.
        """
        keys_to_invalidate = []

        if locale and slug:
            # Invalidate specific content
            base_key = self.key_builder.content_key(model_label, locale, slug)
            keys_to_invalidate.append(base_key)

            # Pattern for revision variants
            pattern = f"{base_key}:*"
            self.delete_pattern(pattern)

        elif object_id:
            # Try to look up object and invalidate
            try:
                from apps.registry.registry import content_registry

                config = content_registry.get_config(model_label)
                if config:
                    obj = config.model.objects.get(id=object_id)
                    # Get slug and locale from object
                    slug_value = getattr(obj, config.slug_field or "slug", None)
                    locale_obj = (
                        getattr(obj, config.locale_field, None)
                        if config.locale_field
                        else None
                    )
                    locale_code = locale_obj.code if locale_obj else None

                    if slug_value:
                        self.invalidate_content(model_label, locale_code, slug_value)
            except:
                pass  # Object not found or error

        # Delete specific keys
        for key in keys_to_invalidate:
            self.delete(key)

    def invalidate_blog_post(
        self, locale: str = None, slug: str = None, post_id: int = None
    ):
        """
        Invalidate blog post cache entries.
        """
        if locale and slug:
            # Invalidate all blog cache variations for this post
            pattern = self.key_builder.build_key("blog", locale, slug, "*")
            self.delete_pattern(pattern)

        elif post_id:
            # Look up post and invalidate
            try:
                from apps.blog.models import BlogPost

                post = BlogPost.objects.get(id=post_id)
                self.invalidate_blog_post(locale=post.locale.code, slug=post.slug)
            except:
                pass

    def invalidate_search(self, query: str = None):
        """
        Invalidate search cache entries.
        """
        if query:
            # Invalidate specific query
            pattern = self.key_builder.search_key(query, {}) + "*"
            self.delete_pattern(pattern)
        else:
            # Invalidate all search cache
            pattern = self.key_builder.build_key("search", "*")
            self.delete_pattern(pattern)

    def invalidate_sitemap(self, locale: str = None):
        """
        Invalidate sitemap cache.
        """
        if locale:
            key = self.key_builder.sitemap_key(locale)
            self.delete(key)
        else:
            # Invalidate all sitemaps
            pattern = self.key_builder.build_key("sitemap", "*")
            self.delete_pattern(pattern)

    def invalidate_seo(
        self, model_label: str = None, object_id: int = None, locale: str = None
    ):
        """
        Invalidate SEO cache entries.
        """
        if model_label and object_id and locale:
            key = self.key_builder.seo_key(model_label, object_id, locale)
            self.delete(key)
        elif model_label and object_id:
            # Invalidate for all locales
            pattern = self.key_builder.build_key("seo", model_label, object_id, "*")
            self.delete_pattern(pattern)

    def clear_all(self):
        """
        Clear all CMS cache entries.
        """
        pattern = f"{self.key_builder.prefix}:*"
        self.delete_pattern(pattern)


# Global cache manager instance
cache_manager = CacheManager()
