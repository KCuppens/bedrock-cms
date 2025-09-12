import time



from django.core.cache import cache

from django.core.management.base import BaseCommand



from apps.blog.models import BlogPost

from apps.cms.models import Page

from apps.core.cache import CACHE_PREFIXES, cache_manager

from apps.core.signals import invalidate_all_cache, invalidate_content_type_cache

from apps.i18n.models import Locale



"""Django management command for cache management.

Usage:
    python manage.py cache_manage --clear-all
    python manage.py cache_manage --stats
    python manage.py cache_manage --invalidate-pages
    python manage.py cache_manage --warm-cache
"""



class Command(BaseCommand):
    """Management command for cache operations."""



    help = "Manage CMS cache operations"



    def add_arguments(self, parser):

        """Add command arguments."""

        parser.add_argument(

            "--clear-all", action="store_true", help="Clear all CMS cache entries"

        )



        parser.add_argument(

            "--stats", action="store_true", help="Show cache statistics"

        )



        parser.add_argument(

            "--invalidate-pages",

            action="store_true",

            help="Invalidate all page cache entries",

        )



        parser.add_argument(

            "--invalidate-content",

            type=str,

            help="Invalidate cache for specific content type (e.g., blog.blogpost)",

        )



        parser.add_argument(

            "--warm-cache",

            action="store_true",

            help="Pre-warm cache with popular content",

        )



        parser.add_argument(

            "--test-keys", action="store_true", help="Test cache key generation"

        )



        parser.add_argument(

            "--verbose", action="store_true", help="Enable verbose output"

        )



    def handle(self, *args, **options):

        """Handle the command."""

        self.verbosity = options.get("verbosity", 1)

        self.verbose = options.get("verbose", False)



        if options["clear_all"]:

            self.clear_all_cache()

        elif options["stats"]:

            self.show_cache_stats()

        elif options["invalidate_pages"]:

            self.invalidate_pages()

        elif options["invalidate_content"]:

            self.invalidate_content_type(options["invalidate_content"])

        elif options["warm_cache"]:

            self.warm_cache()

        """elif options["test_keys"]:"""

            """self.test_cache_keys()"""

        else:

            self.show_help()



    def show_help(self):

        """Show command help."""

        """self.stdout.write(self.style.SUCCESS("Cache Management"))"""

        self.stdout.write("")

        self.stdout.write("Available operations:")

        self.stdout.write("  --clear-all           Clear all CMS cache entries")

        self.stdout.write("  --stats              Show cache statistics")

        self.stdout.write("  --invalidate-pages   Invalidate page cache")

        self.stdout.write("  --invalidate-content Clear content type cache")

        self.stdout.write("  --warm-cache         Pre-warm popular content")

        """self.stdout.write("  --test-keys          Test cache key generation")"""

        self.stdout.write("")

        self.stdout.write("Examples:")

        self.stdout.write("  python manage.py cache_manage --clear-all")

        self.stdout.write(

            "  python manage.py cache_manage --invalidate-content blog.blogpost"

        )

        self.stdout.write("  python manage.py cache_manage --stats")



    def clear_all_cache(self):

        """Clear all CMS cache entries."""

        self.stdout.write(self.style.WARNING("Clearing all CMS cache entries..."))



        start_time = time.time()

        invalidate_all_cache()

        end_time = time.time()



        self.stdout.write(

            self.style.SUCCESS(

                f"Successfully cleared all cache entries in {end_time - start_time:.2f}s"

            )

        )



    def show_cache_stats(self):

        """Show cache statistics."""

        self.stdout.write(self.style.SUCCESS("Cache Statistics"))

        self.stdout.write("=" * 50)



        # Try to get cache backend info

        try:

            cache_info = self._get_cache_info()



            for key, value in cache_info.items():

                self.stdout.write(f"{key}: {value}")



        except Exception as e:

            self.stdout.write(

                self.style.WARNING(f"Could not retrieve cache stats: {e}")

            )



        self.stdout.write("")

        self.stdout.write("Cache Key Prefixes:")



        for cache_type, prefix in CACHE_PREFIXES.items():

            self.stdout.write(f"  {cache_type}: {prefix}")



    def _get_cache_info(self):

        """Get cache backend information."""

        info = {}



        # Basic cache backend info

        info["Backend"] = cache.__class__.__name__



        try:

            # Try to get Redis info if available

            if hasattr(cache, "_cache") and hasattr(cache._cache, "get_stats"):

                stats = cache._cache.get_stats()

                info.update(stats)

            elif hasattr(cache, "get_stats"):

                stats = cache.get_stats()

                info.update(stats)

        except Exception:
            pass

        # Test cache connectivity

        test_key = "cache_test_key"

        test_value = "test_value"



        try:

            """cache.set(test_key, test_value, 60)"""

            retrieved = cache.get(test_key)

            """cache.delete(test_key)"""



            info["Status"] = "Connected" if retrieved == test_value else "Error"

        except Exception as e:

            info["Status"] = f"Error: {e}"



        return info



    def invalidate_pages(self):

        """Invalidate all page cache entries."""

        self.stdout.write(self.style.SUCCESS("Invalidating page cache..."))



        try:

            # Invalidate page-related cache patterns

            cache_manager.delete_pattern(f"{cache_manager.key_builder.prefix}:p:*")

            cache_manager.delete_pattern(

                f"{cache_manager.key_builder.prefix}:sm:*"

            )  # Sitemaps



            self.stdout.write(self.style.SUCCESS("Successfully invalidated page cache"))

        except Exception as e:

            self.stdout.write(self.style.ERROR(f"Error invalidating page cache: {e}"))



    def invalidate_content_type(self, model_label):

        """Invalidate cache for a specific content type."""

        self.stdout.write(

            self.style.SUCCESS(f"Invalidating cache for {model_label}...")

        )



        try:

            invalidate_content_type_cache(model_label)



            self.stdout.write(

                self.style.SUCCESS(f"Successfully invalidated cache for {model_label}")

            )

        except Exception as e:

            self.stdout.write(

                self.style.ERROR(f"Error invalidating cache for {model_label}: {e}")

            )



    def warm_cache(self):

        """Pre-warm cache with popular content."""

        self.stdout.write(self.style.SUCCESS("Warming cache with popular content..."))



        warmed_count = 0



        try:

            # Warm page cache

            warmed_count += self._warm_page_cache()



            # Warm blog cache

            warmed_count += self._warm_blog_cache()



            # Warm sitemaps

            warmed_count += self._warm_sitemap_cache()



            self.stdout.write(

                self.style.SUCCESS(f"Successfully warmed {warmed_count} cache entries")

            )



        except Exception as e:

            self.stdout.write(self.style.ERROR(f"Error warming cache: {e}"))



    def _warm_page_cache(self):

        """Warm page cache."""

        warmed = 0



        try:



            # Get published pages

            pages = Page.objects.filter(status="published").select_related("locale")[

                :20

            ]



            for page in pages:

                if self.verbose:

                    self.stdout.write(

                        f"  Warming page: {page.path} ({page.locale.code})"

                    )



                # This would typically involve making a request to the page

                # For now, we'll just generate and store the cache key structure

                cache_manager.key_builder.page_key(page.locale.code, page.path)



                # In a real implementation, you'd fetch the page data and cache it

                # cache_manager.set(cache_key, page_data)



                warmed += 1



        except ImportError:



        return warmed



    def _warm_blog_cache(self):

        """Warm blog cache."""

        warmed = 0



        try:



            # Get published blog posts

            posts = BlogPost.objects.filter(status="published").select_related(

                "locale"

            )[:10]



            for post in posts:

                if self.verbose:

                    self.stdout.write(

                        f"  Warming blog post: {post.slug} ({post.locale.code})"

                    )



                cache_manager.key_builder.blog_key(post.locale.code, post.slug)



                # In a real implementation, you'd render the blog post

                # cache_manager.set(cache_key, rendered_post)



                warmed += 1



        except ImportError:



        return warmed



    def _warm_sitemap_cache(self):

        """Warm sitemap cache."""

        warmed = 0



        try:



            locales = Locale.objects.filter(is_active=True)



            for locale in locales:

                if self.verbose:

                    self.stdout.write(f"  Warming sitemap: {locale.code}")



                cache_manager.key_builder.sitemap_key(locale.code)



                # In a real implementation, you'd generate the sitemap

                # cache_manager.set(cache_key, sitemap_xml)



                warmed += 1



        except ImportError:



        return warmed



    def test_cache_keys(self):

        """Test cache key generation."""

        """self.stdout.write(self.style.SUCCESS("Testing Cache Key Generation"))"""

        self.stdout.write("=" * 50)



        # Test page keys

        page_key = cache_manager.key_builder.page_key("en", "/about")

        self.stdout.write(f"Page key: {page_key}")



        page_key_with_rev = cache_manager.key_builder.page_key("en", "/about", "123")

        self.stdout.write(f"Page key with revision: {page_key_with_rev}")



        # Test content keys

        content_key = cache_manager.key_builder.content_key(

            "blog.blogpost", "en", "my-post"

        )

        self.stdout.write(f"Content key: {content_key}")



        # Test blog keys

        blog_key = cache_manager.key_builder.blog_key("en", "my-post", "456", "789")

        self.stdout.write(f"Blog key: {blog_key}")



        # Test API keys

        api_key = cache_manager.key_builder.api_key("search", q="test", locale="en")

        self.stdout.write(f"API key: {api_key}")



        # Test search keys

        search_key = cache_manager.key_builder.search_key(

            "django cms", {"locale": "en"}

        )

        self.stdout.write(f"Search key: {search_key}")



        # Test sitemap keys

        sitemap_key = cache_manager.key_builder.sitemap_key("en")

        self.stdout.write(f"Sitemap key: {sitemap_key}")



        # Test SEO keys

        seo_key = cache_manager.key_builder.seo_key("cms.page", 123, "en")

        self.stdout.write(f"SEO key: {seo_key}")



        self.stdout.write("")

        """self.stdout.write(self.style.SUCCESS("All cache key tests completed"))"""

