
"""
Cache invalidation signals for CMS.

Automatically invalidates relevant cache entries when content changes.
"""



import logging



from django.conf import settings

from django.db.models.signals import m2m_changed, post_delete, post_save

from django.dispatch import receiver

from django.utils import timezone



import requests



from apps.blog.models import BlogPost

from apps.registry.registry import content_registry



from .cache import cache_manager



logger = logging.getLogger(__name__)



@receiver(post_save)

def invalidate_cache_on_save(sender, instance, created, **kwargs):
    """
    Invalidate cache when models are saved.

    Handles Page, BlogPost, and any registered content types.
    """



    try:

        model_label = f"{sender._meta.app_label}.{sender._meta.model_name}"



        # Handle Page model

        if model_label == "cms.page":

            invalidate_page_cache(instance)



        # Handle BlogPost model

        elif model_label == "blog.blogpost":

            invalidate_blog_cache(instance)



        # Handle BlogSettings changes - invalidate all blog post caches for that locale

        elif model_label == "blog.blogsettings":

            invalidate_blog_settings_cache(instance)



        # Handle other registered content types

        else:

            invalidate_content_cache(instance, model_label)



        # Always invalidate search cache when content changes

        cache_manager.invalidate_search()



        logger.debug("Cache invalidated for %s {instance.id}", model_label)



    except Exception:

        logger.warning("Error invalidating cache for %s: {e}", instance)



@receiver(post_delete)

def invalidate_cache_on_delete(sender, instance, **kwargs):
    """
    Invalidate cache when models are deleted.
    """



    try:

        model_label = f"{sender._meta.app_label}.{sender._meta.model_name}"



        # Handle Page model

        if model_label == "cms.page":

            invalidate_page_cache(instance)



        # Handle BlogPost model

        elif model_label == "blog.blogpost":

            invalidate_blog_cache(instance)



        # Handle other registered content types

        else:

            invalidate_content_cache(instance, model_label)



        # Invalidate search and sitemap cache

        cache_manager.invalidate_search()

        cache_manager.invalidate_sitemap()



        logger.debug("Cache invalidated for deleted %s {instance.id}", model_label)



    except Exception:

        logger.warning("Error invalidating cache for deleted %s: {e}", instance)



def invalidate_page_cache(page):
    """
    Invalidate cache for a specific page and related entries.

    Args:
        page: Page instance
    """



    try:

        # Invalidate the specific page

        if hasattr(page, "locale") and hasattr(page, "path"):

            cache_manager.invalidate_page(locale=page.locale.code, path=page.path)



        # Invalidate sitemap for this locale

        if hasattr(page, "locale"):

            cache_manager.invalidate_sitemap(page.locale.code)



        # If this page has children, we might need to invalidate them too

        # (path changes cascade to descendants)

        if hasattr(page, "children"):

            for child in page.children.all():

                cache_manager.invalidate_page(locale=child.locale.code, path=child.path)



        # Invalidate SEO cache

        cache_manager.invalidate_seo(model_label="cms.page", object_id=page.id)



    except Exception:

        logger.warning("Error invalidating page cache for %s: {e}", page)



def invalidate_blog_cache(blog_post):
    """
    Invalidate cache for a specific blog post.

    Args:
        blog_post: BlogPost instance
    """



    try:

        # Invalidate blog post presentation cache

        if hasattr(blog_post, "locale") and hasattr(blog_post, "slug"):

            cache_manager.invalidate_blog_post(

                locale=blog_post.locale.code, slug=blog_post.slug

            )



        # Invalidate content cache (for registry API)

        if hasattr(blog_post, "locale") and hasattr(blog_post, "slug"):

            cache_manager.invalidate_content(

                model_label="blog.blogpost",

                locale=blog_post.locale.code,

                slug=blog_post.slug,

            )



        # Invalidate sitemap

        if hasattr(blog_post, "locale"):

            cache_manager.invalidate_sitemap(blog_post.locale.code)



        # Invalidate SEO cache

        cache_manager.invalidate_seo(

            model_label="blog.blogpost", object_id=blog_post.id

        )



        # If this affects feeds, invalidate those too

        # (RSS/Atom feeds would be handled by view-level caching)



    except Exception:

        logger.warning("Error invalidating blog cache for %s: {e}", blog_post)



def invalidate_content_cache(instance, model_label):
    """
    Invalidate cache for registered content types.

    Args:
        instance: Model instance
        model_label: Model label (app.model)
    """



    try:



        config = content_registry.get_config(model_label)

        if not config:
            return

        # Get slug and locale from the instance

        slug_value = None

        locale_code = None



        if config.slug_field:

            slug_value = getattr(instance, config.slug_field, None)



        if config.locale_field:

            locale_obj = getattr(instance, config.locale_field, None)

            if locale_obj:

                locale_code = (

                    locale_obj.code if hasattr(locale_obj, "code") else str(locale_obj)

                )



        # Invalidate content cache

        if slug_value:

            cache_manager.invalidate_content(

                model_label=model_label, locale=locale_code, slug=slug_value

            )



        # Invalidate SEO cache

        cache_manager.invalidate_seo(model_label=model_label, object_id=instance.id)



    except Exception:

        logger.warning("Error invalidating content cache for %s: {e}", instance)



# Handle many-to-many changes (like blog post tags)

@receiver(m2m_changed)

def invalidate_cache_on_m2m_change(sender, instance, action, pk_set, **kwargs):
    """
    Invalidate cache when many-to-many relationships change.
    """



    if action in ["post_add", "post_remove", "post_clear"]:

        try:

            # Determine the model that changed

            model_label = f"{instance._meta.app_label}.{instance._meta.model_name}"



            # Handle BlogPost tag changes

            if model_label == "blog.blogpost":

                invalidate_blog_cache(instance)



            # Handle other content types

            else:

                invalidate_content_cache(instance, model_label)



            # Invalidate search cache since relationships changed

            cache_manager.invalidate_search()



            logger.debug(

                "Cache invalidated for M2M change on %s {instance.id}", model_label

            )



        except Exception:

            logger.warning(

                "Error invalidating cache for M2M change on %s: {e}", instance

            )



# Handle asset changes (media replacements)

@receiver(post_save)

def invalidate_cache_on_asset_change(sender, instance, created, **kwargs):
    """
    Invalidate cache when assets are updated.

    This is important for media replacements that should update all
    pages/content using those assets.
    """



    if sender._meta.model_name != "asset":
        return

    try:

        # When an asset is replaced, we need to invalidate all content using it

        # This would require scanning usage tracking (from Phase 3)



        # For now, we'll do a broad invalidation on asset changes

        if not created:  # Only on updates, not creation

            # Invalidate all page cache (broad but safe)

            # In production, you'd want more targeted invalidation

            # using asset usage tracking



            logger.info("Asset %s updated, invalidating related cache", instance.id)



            # This is a placeholder - in a real implementation,

            # you'd scan the AssetUsage table to find affected content



    except Exception:

        logger.warning("Error invalidating cache for asset change %s: {e}", instance)



# CDN Webhook Support (optional)

def send_cdn_purge_webhook(keys: list, tags: list = None):
    """
    Send cache purge webhook to CDN.

    Args:
        keys: List of cache keys to purge
        tags: List of cache tags to purge (if CDN supports tag-based purging)
    """



    try:



        # Check if CDN webhook is configured

        webhook_url = getattr(settings, "CDN_PURGE_WEBHOOK_URL", None)

        webhook_token = getattr(settings, "CDN_PURGE_WEBHOOK_TOKEN", None)



        if not webhook_url:
            return

        # Prepare webhook payload

        payload = {

            "keys": keys,

            "timestamp": timezone.now().isoformat(),

        }



        if tags:

            payload["tags"] = tags



        headers = {"Content-Type": "application/json"}

        if webhook_token:

            headers["Authorization"] = f"Bearer {webhook_token}"



        # Send webhook (async in production)

        response = requests.post(webhook_url, json=payload, headers=headers, timeout=10)



        if response.status_code == 200:

            logger.info("CDN purge webhook sent successfully for %s keys", len(keys))

        else:

            logger.warning(

                "CDN purge webhook failed: %s {response.text}", response.status_code

            )



    except Exception as e:

        logger.error("Error sending CDN purge webhook: %s", e)



# Utility functions for manual cache invalidation



def invalidate_all_cache():

    """Manually invalidate all CMS cache entries."""

    cache_manager.clear_all()

    logger.info("All CMS cache entries invalidated")



def invalidate_content_type_cache(model_label: str):
    """
    Invalidate all cache entries for a specific content type.

    Args:
        model_label: Model label (e.g., 'blog.blogpost')
    """



    try:



        config = content_registry.get_config(model_label)

        if not config:
            logger.warning(
                "Unknown model label for cache invalidation: %s", model_label
            )
            return

        # Get all objects of this type and invalidate their cache

        for obj in config.model.objects.all():

            invalidate_content_cache(obj, model_label)



        logger.info("Cache invalidated for all %s objects", model_label)



    except Exception:

        logger.error("Error invalidating cache for %s: {e}", model_label)



def invalidate_blog_settings_cache(blog_settings):
    """
    Invalidate cache when blog settings change.

    This affects all blog posts in that locale since presentation
    page and display options may have changed.

    Args:
        blog_settings: BlogSettings instance
    """



    try:



        # Get all published blog posts for this locale

        posts = BlogPost.objects.filter(locale=blog_settings.locale, status="published")



        # Invalidate cache for each blog post

        for post in posts:

            cache_manager.invalidate_blog_post(locale=post.locale.code, slug=post.slug)



        logger.info(

            "Blog settings cache invalidated for locale %s", blog_settings.locale.code

        )



    except Exception as e:

        logger.warning("Error invalidating blog settings cache: %s", e)

