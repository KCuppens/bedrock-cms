"""
Presentation page resolver for content_detail blocks.

Handles the resolution of which presentation page to use for rendering
registered content models, with support for precedence and caching.
"""

# mypy: ignore-errors

from typing import Optional, Dict, Any
from django.shortcuts import get_object_or_404
from django.apps import apps
from django.core.exceptions import ValidationError
from django.http import Http404

from apps.core.cache import cache_manager
from apps.registry.registry import get_all_configs


class PresentationPageResolver:
    """Resolves presentation pages for content detail rendering."""

    def __init__(self):
        self.registry_configs = get_all_configs()

    def resolve_from_route(self, path: str, locale_code: str) -> Dict[str, Any]:
        """
        Resolve content and presentation page from a URL path.

        Args:
            path: URL path like '/blog/my-post-slug'
            locale_code: Locale code like 'en'

        Returns:
            Dict containing 'content', 'presentation_page', 'display_options'

        Raises:
            Http404: If content or presentation page not found
        """
        # Parse path to determine content type and slug
        path_parts = path.strip("/").split("/")

        # Handle blog posts: /blog/{slug} or /{locale}/blog/{slug}
        if len(path_parts) >= 2:
            # Check if first part is locale
            if path_parts[0] == locale_code and len(path_parts) >= 3:
                base_path = path_parts[1]
                slug = path_parts[2]
            else:
                base_path = path_parts[0]
                slug = path_parts[1]

            if base_path == "blog":
                return self._resolve_blog_post(slug, locale_code)

        # Could extend this for other registered content types
        # by checking registry configurations and their route patterns

        raise Http404(f"No content found for path: {path}")

    def resolve_by_id(
        self, content_label: str, content_id: int, locale_code: str
    ) -> Dict[str, Any]:
        """
        Resolve content and presentation page by explicit ID.

        Args:
            content_label: Content type label like 'blog.blogpost'
            content_id: ID of the content instance
            locale_code: Locale code

        Returns:
            Dict containing 'content', 'presentation_page', 'display_options'
        """
        if content_label == "blog.blogpost":
            from apps.blog.models import BlogPost

            try:
                post = BlogPost.objects.select_related("category", "locale").get(
                    id=content_id, locale__code=locale_code
                )

                return self._resolve_blog_post_from_instance(post)
            except BlogPost.DoesNotExist:
                raise Http404(
                    f"BlogPost {content_id} not found for locale {locale_code}"
                )

        # Could extend for other registered content types
        raise Http404(f"Content type {content_label} not supported")

    def _resolve_blog_post(self, slug: str, locale_code: str) -> Dict[str, Any]:
        """Resolve blog post by slug."""
        from apps.blog.models import BlogPost

        try:
            post = BlogPost.objects.select_related("category", "locale").get(
                slug=slug, locale__code=locale_code, status="published"
            )

            return self._resolve_blog_post_from_instance(post)
        except BlogPost.DoesNotExist:
            raise Http404(
                f"Published blog post '{slug}' not found for locale {locale_code}"
            )

    def _resolve_blog_post_from_instance(self, post) -> Dict[str, Any]:
        """Resolve presentation page and options for a blog post instance."""
        from apps.blog.models import BlogSettings

        # Get blog settings for this locale
        try:
            blog_settings = BlogSettings.objects.select_related(
                "default_presentation_page"
            ).get(locale=post.locale)
        except BlogSettings.DoesNotExist:
            # No settings configured, return basic structure
            return {
                "content": post,
                "presentation_page": None,
                "display_options": {
                    "show_toc": True,
                    "show_author": True,
                    "show_dates": True,
                    "show_share": True,
                    "show_reading_time": True,
                },
            }

        # Resolve presentation page with precedence
        presentation_page = blog_settings.get_presentation_page(
            category=post.category, post=post
        )

        # Get display options with precedence
        display_options = blog_settings.get_display_options(
            category=post.category, post=post
        )

        return {
            "content": post,
            "presentation_page": presentation_page,
            "display_options": display_options,
        }

    def build_cache_key(self, content, presentation_page=None) -> str:
        """
        Build composite cache key for presentation page rendering.

        Format: post:{locale}:{slug}:{post_rev}:{page_rev}
        """
        # Get post revision ID (could be extended for other content types)
        post_rev = getattr(content, "updated_at", None)
        if post_rev:
            post_rev = post_rev.timestamp()

        # Get presentation page revision ID
        page_rev = None
        if presentation_page:
            page_rev = getattr(presentation_page, "updated_at", None)
            if page_rev:
                page_rev = page_rev.timestamp()

        return cache_manager.key_builder.blog_key(
            content.locale.code, content.slug, post_rev, page_rev
        )

    def validate_content_detail_block(
        self, blocks: list, allowed_labels: Optional[list] = None
    ) -> None:
        """
        Validate that a page has exactly one content_detail block for presentation pages.

        Args:
            blocks: List of block data
            allowed_labels: Optional list of allowed content labels
        """
        content_detail_blocks = [
            block
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "content_detail"
        ]

        if len(content_detail_blocks) == 0:
            raise ValidationError(
                "Presentation pages must include exactly one content_detail block"
            )

        if len(content_detail_blocks) > 1:
            raise ValidationError(
                "Presentation pages can only have one content_detail block"
            )

        # Validate the content_detail block configuration
        block = content_detail_blocks[0]
        props = block.get("props", {})
        label = props.get("label", "")

        if not label:
            raise ValidationError("content_detail block must specify a content label")

        if allowed_labels and label not in allowed_labels:
            raise ValidationError(
                f"content_detail block label '{label}' not in allowed list: {allowed_labels}"
            )


# Global resolver instance
presentation_resolver = PresentationPageResolver()


def resolve_presentation_page(
    path: str = None,
    content_label: str = None,
    content_id: int = None,
    locale_code: str = "en",
) -> Dict[str, Any]:
    """
    Convenience function to resolve presentation pages.

    Args:
        path: URL path for route-based resolution
        content_label: Content type label for ID-based resolution
        content_id: Content ID for ID-based resolution
        locale_code: Locale code

    Returns:
        Dict with content, presentation_page, and display_options
    """
    if path:
        return presentation_resolver.resolve_from_route(path, locale_code)
    elif content_label and content_id:
        return presentation_resolver.resolve_by_id(
            content_label, content_id, locale_code
        )
    else:
        raise ValueError("Must provide either path or (content_label, content_id)")
