import logging

from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.blog.models import BlogPost
from apps.cms.models import Page
from apps.core.cache import cache_manager
from apps.core.tasks import bulk_warm_cache, warm_cache_async
from apps.i18n.models import Locale

Cache warming and invalidation strategies.

logger = logging.getLogger(__name__)

class CacheWarmer:

    Manages cache warming strategies for optimal performance.

    @staticmethod
    def warm_homepage_cache():
        """Warm cache for homepage and main navigation."""

        configs = []

        for locale in Locale.objects.filter(is_active=True):
            # Homepage
            homepage = Page.objects.filter(
                locale=locale, is_homepage=True, status="published"
            ).first()

            if homepage:
                configs.append(
                    {
                        "key": cache_manager.key_builder.page_key(locale.code, "/"),
                        "callable": "apps.cms.utils.get_page_data",
                        "args": [homepage.id],
                        "timeout": 3600,  # 1 hour
                    }
                )

            # Main menu pages
            menu_pages = Page.objects.filter(
                locale=locale, in_main_menu=True, status="published"
            ).order_by("position")[:10]

            for page in menu_pages:
                configs.append(
                    {
                        "key": cache_manager.key_builder.page_key(
                            locale.code, page.path
                        ),
                        "callable": "apps.cms.utils.get_page_data",
                        "args": [page.id],
                        "timeout": 1800,  # 30 minutes
                    }
                )

        # Dispatch warming tasks
        if configs:
            bulk_warm_cache.delay(configs)
            logger.info(f"Warming {len(configs)} homepage and menu caches")

    @staticmethod
    def warm_popular_content():
        """Warm cache for popular/featured content."""

        configs = []

        # Featured blog posts
        featured_posts = (
            BlogPost.objects.filter(status="published", featured=True)
            .select_related("locale")
            .order_by("-published_at")[:20]
        )

        for post in featured_posts:
            configs.append(
                {
                    "key": cache_manager.key_builder.blog_key(
                        post.locale.code, post.slug
                    ),
                    "callable": "apps.blog.utils.get_post_data",
                    "args": [post.id],
                    "timeout": 1800,  # 30 minutes
                }
            )

        # Recent posts
        recent_posts = (
            BlogPost.objects.filter(status="published")
            .select_related("locale")
            .order_by("-published_at")[:30]
        )

        for post in recent_posts:
            configs.append(
                {
                    "key": cache_manager.key_builder.blog_key(
                        post.locale.code, post.slug
                    ),
                    "callable": "apps.blog.utils.get_post_data",
                    "args": [post.id],
                    "timeout": 900,  # 15 minutes
                }
            )

        if configs:
            bulk_warm_cache.delay(configs)
            logger.info(f"Warming {len(configs)} popular content caches")

    @staticmethod
    def warm_api_endpoints():
        """Warm cache for frequently accessed API endpoints."""

        configs = []

        # Common API endpoints to warm
        endpoints = [
            ("pages", {"status": "published", "page_size": 20}),
            ("blog", {"status": "published", "featured": True}),
            ("categories", {}),
            ("tags", {"limit": 50}),
        ]

        for endpoint, params in endpoints:
            cache_key = cache_manager.key_builder.api_key(endpoint, **params)
            configs.append(
                {
                    "key": cache_key,
                    "callable": f"apps.api.utils.get_{endpoint}_data",
                    "kwargs": params,
                    "timeout": 600,  # 10 minutes
                }
            )

        if configs:
            bulk_warm_cache.delay(configs)
            logger.info(f"Warming {len(configs)} API endpoint caches")

    @staticmethod
    def warm_after_deployment():
        """Comprehensive cache warming after deployment."""
        logger.info("Starting post-deployment cache warming")

        # Warm in order of priority
        CacheWarmer.warm_homepage_cache()
        CacheWarmer.warm_popular_content()
        CacheWarmer.warm_api_endpoints()

        # Warm sitemaps
        CacheWarmer.warm_sitemaps()

        logger.info("Post-deployment cache warming completed")

    @staticmethod
    def warm_sitemaps():
        """Warm sitemap caches."""

        configs = []

        for locale in Locale.objects.filter(is_active=True):
            cache_key = cache_manager.key_builder.sitemap_key(locale.code)
            configs.append(
                {
                    "key": cache_key,
                    "callable": "apps.cms.utils.generate_sitemap",
                    "args": [locale.code],
                    "timeout": 21600,  # 6 hours
                }
            )

        if configs:
            bulk_warm_cache.delay(configs)
            logger.info(f"Warming {len(configs)} sitemap caches")

# Signal handlers for cache invalidation
@receiver(post_save, sender="cms.Page")
def invalidate_page_cache(sender, instance, created, **kwargs):
    """Invalidate page cache on save."""

    if instance.locale and instance.path:
        # Invalidate specific page
        cache_manager.invalidate_page(locale=instance.locale.code, path=instance.path)

        # Invalidate parent if exists
        if instance.parent:
            cache_manager.invalidate_page(page_id=instance.parent.id)

        # Invalidate sitemap
        cache_manager.invalidate_sitemap(instance.locale.code)

        # Re-warm if published
        if instance.status == "published":
            warm_cache_async.delay(
                cache_key=cache_manager.key_builder.page_key(
                    instance.locale.code, instance.path
                ),
                callable_path="apps.cms.utils.get_page_data",
                args=[instance.id],
                timeout=1800,
            )

@receiver(post_delete, sender="cms.Page")
def invalidate_page_cache_on_delete(sender, instance, **kwargs):
    """Invalidate page cache on delete."""

    if instance.locale and instance.path:
        cache_manager.invalidate_page(locale=instance.locale.code, path=instance.path)
        cache_manager.invalidate_sitemap(instance.locale.code)

@receiver(post_save, sender="blog.BlogPost")
def invalidate_blog_cache(sender, instance, created, **kwargs):
    """Invalidate blog post cache on save."""

    if instance.locale and instance.slug:
        # Invalidate specific post
        cache_manager.invalidate_blog_post(
            locale=instance.locale.code, slug=instance.slug
        )

        # Invalidate category pages if exists
        if instance.category:
            pattern = f"api:blog:category:{instance.category.id}:*"
            cache_manager.delete_pattern(pattern)

        # Re-warm if published
        if instance.status == "published":
            warm_cache_async.delay(
                cache_key=cache_manager.key_builder.blog_key(
                    instance.locale.code, instance.slug
                ),
                callable_path="apps.blog.utils.get_post_data",
                args=[instance.id],
                timeout=1800,
            )

@receiver(post_delete, sender="blog.BlogPost")
def invalidate_blog_cache_on_delete(sender, instance, **kwargs):
    """Invalidate blog post cache on delete."""

    if instance.locale and instance.slug:
        cache_manager.invalidate_blog_post(
            locale=instance.locale.code, slug=instance.slug
        )

# Management command for cache warming

class Command(BaseCommand):
    """Management command for cache operations."""

    help = "Manage cache warming and invalidation"

    def add_arguments(self, parser):
        parser.add_argument(
            "action", choices=["warm", "clear", "stats"], help="Action to perform"
        )
        parser.add_argument(
            "--target",
            choices=["all", "homepage", "popular", "api", "sitemaps"],
            default="all",
            help="Target for cache operation",
        )

    def handle(self, *args, **options):
        action = options["action"]
        target = options["target"]

        if action == "warm":
            self.warm_cache(target)
        elif action == "clear":
            self.clear_cache(target)
        elif action == "stats":
            self.show_stats()

    def warm_cache(self, target):
        """Warm cache based on target."""
        self.stdout.write("Starting cache warming...")

        if target == "all":
            CacheWarmer.warm_after_deployment()
        elif target == "homepage":
            CacheWarmer.warm_homepage_cache()
        elif target == "popular":
            CacheWarmer.warm_popular_content()
        elif target == "api":
            CacheWarmer.warm_api_endpoints()
        elif target == "sitemaps":
            CacheWarmer.warm_sitemaps()

        self.stdout.write(self.style.SUCCESS(f"Cache warming for {target} initiated"))

    def clear_cache(self, target):
        """Clear cache based on target."""

        self.stdout.write("Clearing cache...")

        if target == "all":
            cache_manager.clear_all()
        else:
            pattern = f"{target}:*"
            cache_manager.delete_pattern(pattern)

        self.stdout.write(self.style.SUCCESS(f"Cache cleared for {target}"))

    def show_stats(self):
        """Show cache statistics."""
        stats = cache.get("cache:stats:global", {})

        self.stdout.write("Cache Statistics:")
        self.stdout.write(f"  Hits: {stats.get('hits', 0)}")
        self.stdout.write(f"  Misses: {stats.get('misses', 0)}")
        self.stdout.write(f"  Hit Rate: {stats.get('hit_rate', 0):.2%}")

        # Show slow endpoints

        self.stdout.write("\nSlow Endpoints:")
        # This is a simplified example - in production you'd query Redis directly
        for key in ["perf:slow:/api/v1/cms/pages/", "perf:slow:/api/v1/blog/posts/"]:
            data = cache.get(key)
            if data:
                self.stdout.write(
                    f"  {key}: {data['avg_time']:.3f}s (n={data['count']})"
                )
