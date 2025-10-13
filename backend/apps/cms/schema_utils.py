"""
Schema.org structured data generation utilities.

This module provides utilities for generating JSON-LD structured data
that complies with Schema.org vocabulary for SEO enhancement.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from django.conf import settings
from django.urls import reverse


class SchemaGenerator:
    """Generate Schema.org structured data for various content types."""

    @staticmethod
    def generate_article_schema(
        page_or_post: Any, request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate Article schema from a Page or BlogPost.

        Args:
            page_or_post: Page or BlogPost model instance
            request: HTTP request object for building absolute URLs

        Returns:
            Dict containing Article schema
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": page_or_post.title,
        }

        # Add description if available
        if hasattr(page_or_post, "seo") and isinstance(page_or_post.seo, dict):
            if page_or_post.seo.get("description"):
                schema["description"] = page_or_post.seo["description"]

        # Add excerpt for blog posts
        if hasattr(page_or_post, "excerpt") and page_or_post.excerpt:
            schema["description"] = page_or_post.excerpt

        # Add URL
        if request:
            schema["url"] = request.build_absolute_uri(
                getattr(page_or_post, "path", f"/{page_or_post.slug}/")
            )
        else:
            schema["url"] = getattr(page_or_post, "path", f"/{page_or_post.slug}/")

        # Add published date
        if hasattr(page_or_post, "published_at") and page_or_post.published_at:
            schema["datePublished"] = page_or_post.published_at.isoformat()

        # Add modified date
        if hasattr(page_or_post, "updated_at") and page_or_post.updated_at:
            schema["dateModified"] = page_or_post.updated_at.isoformat()

        # Add author for blog posts
        if hasattr(page_or_post, "author"):
            schema["author"] = {
                "@type": "Person",
                "name": page_or_post.author.get_full_name()
                or page_or_post.author.email,
            }

        # Extract first image from blocks or SEO settings
        image_url = SchemaGenerator._extract_image(page_or_post, request)
        if image_url:
            schema["image"] = image_url

        # Add publisher (organization)
        publisher = SchemaGenerator._get_organization_schema(request)
        if publisher:
            schema["publisher"] = publisher

        return schema

    @staticmethod
    def generate_blog_posting_schema(
        blog_post: Any, request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate BlogPosting schema from a BlogPost.

        Args:
            blog_post: BlogPost model instance
            request: HTTP request object for building absolute URLs

        Returns:
            Dict containing BlogPosting schema
        """
        # Start with Article schema
        schema = SchemaGenerator.generate_article_schema(blog_post, request)

        # Change type to BlogPosting
        schema["@type"] = "BlogPosting"

        # Add blog-specific fields
        if hasattr(blog_post, "category") and blog_post.category:
            schema["articleSection"] = blog_post.category.name

        # Add word count if available
        if hasattr(blog_post, "content") and blog_post.content:
            word_count = len(blog_post.content.split())
            schema["wordCount"] = word_count

        return schema

    @staticmethod
    def generate_webpage_schema(
        page: Any, request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate WebPage schema from a Page.

        Args:
            page: Page model instance
            request: HTTP request object for building absolute URLs

        Returns:
            Dict containing WebPage schema
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": page.title,
        }

        # Add description
        if hasattr(page, "seo") and isinstance(page.seo, dict):
            if page.seo.get("description"):
                schema["description"] = page.seo["description"]

        # Add URL
        if request:
            schema["url"] = request.build_absolute_uri(page.path)
        else:
            schema["url"] = page.path

        # Add published date
        if hasattr(page, "published_at") and page.published_at:
            schema["datePublished"] = page.published_at.isoformat()

        # Add modified date
        if hasattr(page, "updated_at") and page.updated_at:
            schema["dateModified"] = page.updated_at.isoformat()

        # Extract image
        image_url = SchemaGenerator._extract_image(page, request)
        if image_url:
            schema["image"] = image_url

        # Add breadcrumb
        breadcrumb = SchemaGenerator.generate_breadcrumb_schema(page, request)
        if breadcrumb:
            schema["breadcrumb"] = breadcrumb

        return schema

    @staticmethod
    def generate_breadcrumb_schema(
        page: Any, request: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Generate BreadcrumbList schema from page hierarchy.

        Args:
            page: Page model instance
            request: HTTP request object for building absolute URLs

        Returns:
            Dict containing BreadcrumbList schema or None
        """
        if not hasattr(page, "parent"):
            return None

        items = []
        position = 1

        # Build breadcrumb trail
        ancestors = []
        current = page
        visited = set()

        # Get ancestors
        while current:
            if current.id in visited:
                break
            visited.add(current.id)
            ancestors.append(current)
            current = getattr(current, "parent", None)

        # Reverse to start from root
        ancestors.reverse()

        # Build breadcrumb items
        for ancestor in ancestors:
            item = {
                "@type": "ListItem",
                "position": position,
                "name": ancestor.title,
            }

            if request:
                item["item"] = request.build_absolute_uri(ancestor.path)
            else:
                item["item"] = ancestor.path

            items.append(item)
            position += 1

        if not items:
            return None

        return {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": items,
        }

    @staticmethod
    def generate_organization_schema(
        locale: Optional[Any] = None, request: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Generate Organization schema from SEO settings.

        Args:
            locale: Locale model instance
            request: HTTP request object for building absolute URLs

        Returns:
            Dict containing Organization schema
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "Organization",
        }

        # Try to get from SEO settings
        if locale:
            try:
                from apps.cms.seo import SeoSettings

                seo_settings = SeoSettings.objects.filter(locale=locale).first()

                if seo_settings and seo_settings.organization_jsonld:
                    # Merge saved organization schema
                    schema.update(seo_settings.organization_jsonld)
                    return schema
            except Exception:
                pass

        # Default organization schema
        schema["name"] = getattr(settings, "SITE_NAME", "Website")

        if request:
            schema["url"] = request.build_absolute_uri("/")
        else:
            schema["url"] = "/"

        return schema

    @staticmethod
    def generate_faq_schema(faqs: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generate FAQPage schema from FAQ items.

        Args:
            faqs: List of dicts with 'question' and 'answer' keys

        Returns:
            Dict containing FAQPage schema
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [],
        }

        for faq in faqs:
            if "question" in faq and "answer" in faq:
                schema["mainEntity"].append(
                    {
                        "@type": "Question",
                        "name": faq["question"],
                        "acceptedAnswer": {"@type": "Answer", "text": faq["answer"]},
                    }
                )

        return schema

    @staticmethod
    def generate_how_to_schema(
        title: str,
        description: str,
        steps: List[Dict[str, str]],
        image_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate HowTo schema for tutorial/guide pages.

        Args:
            title: Title of the how-to guide
            description: Description of what the guide teaches
            steps: List of dicts with 'name' and 'text' keys
            image_url: Optional URL to an image

        Returns:
            Dict containing HowTo schema
        """
        schema = {
            "@context": "https://schema.org",
            "@type": "HowTo",
            "name": title,
            "description": description,
            "step": [],
        }

        if image_url:
            schema["image"] = image_url

        for i, step in enumerate(steps, 1):
            schema["step"].append(
                {
                    "@type": "HowToStep",
                    "position": i,
                    "name": step.get("name", f"Step {i}"),
                    "text": step.get("text", ""),
                }
            )

        return schema

    @staticmethod
    def _extract_image(
        page_or_post: Any, request: Optional[Any] = None
    ) -> Optional[str]:
        """
        Extract image URL from page/post.

        Priority:
        1. SEO og_image
        2. social_image (for blog posts)
        3. First image block
        4. Default OG image from SEO settings

        Args:
            page_or_post: Page or BlogPost instance
            request: HTTP request object

        Returns:
            Image URL string or None
        """
        # Check SEO og_image
        if hasattr(page_or_post, "seo") and isinstance(page_or_post.seo, dict):
            og_image = page_or_post.seo.get("og_image")
            if og_image:
                if request and not og_image.startswith("http"):
                    return request.build_absolute_uri(og_image)
                return og_image

        # Check social_image for blog posts
        if hasattr(page_or_post, "social_image") and page_or_post.social_image:
            if hasattr(page_or_post.social_image, "url"):
                url = page_or_post.social_image.url
                if request and not url.startswith("http"):
                    return request.build_absolute_uri(url)
                return url

        # Check blocks for image
        if hasattr(page_or_post, "blocks") and page_or_post.blocks:
            for block in page_or_post.blocks[:5]:  # Check first 5 blocks
                if isinstance(block, dict):
                    # Check for image block
                    if block.get("type") == "image":
                        content = block.get("content", {}) or block.get("props", {})
                        image_url = (
                            content.get("image")
                            or content.get("url")
                            or content.get("src")
                        )
                        if image_url:
                            if request and not image_url.startswith("http"):
                                return request.build_absolute_uri(image_url)
                            return image_url

        return None

    @staticmethod
    def _get_organization_schema(
        request: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get simplified organization schema for publisher.

        Args:
            request: HTTP request object

        Returns:
            Organization schema dict or None
        """
        schema = {
            "@type": "Organization",
            "name": getattr(settings, "SITE_NAME", "Website"),
        }

        if request:
            schema["url"] = request.build_absolute_uri("/")

        return schema

    @staticmethod
    def merge_schemas(*schemas: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Merge multiple schema objects into a single JSON-LD array.

        Args:
            *schemas: Variable number of schema dictionaries

        Returns:
            List of schema dictionaries ready for JSON-LD output
        """
        merged = []
        for schema in schemas:
            if schema and isinstance(schema, dict):
                # Remove @context if it's not the first schema
                if merged and "@context" in schema:
                    schema = dict(schema)  # Make a copy
                    del schema["@context"]
                merged.append(schema)

        return merged

    @staticmethod
    def validate_schema(schema: Union[Dict, List, str]) -> tuple[bool, Optional[str]]:
        """
        Basic validation of schema structure.

        Args:
            schema: Schema dict, list, or JSON string

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Parse if string
            if isinstance(schema, str):
                schema = json.loads(schema)

            # Handle list of schemas
            if isinstance(schema, list):
                for item in schema:
                    is_valid, error = SchemaGenerator.validate_schema(item)
                    if not is_valid:
                        return False, error
                return True, None

            # Must be a dict
            if not isinstance(schema, dict):
                return False, "Schema must be a JSON object or array"

            # Check for @type
            if "@type" not in schema:
                return False, "Schema must have @type property"

            # Check for @context (optional but recommended)
            if "@context" not in schema:
                # This is just a warning, not an error
                pass

            return True, None

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"


def generate_page_schema(page, request=None) -> List[Dict[str, Any]]:
    """
    Auto-generate appropriate schema for a page.

    Args:
        page: Page model instance
        request: HTTP request object

    Returns:
        List of schema dictionaries
    """
    schemas = []

    # Determine if this is a blog post or regular page
    if hasattr(page, "author"):
        # It's a blog post
        schema = SchemaGenerator.generate_blog_posting_schema(page, request)
    else:
        # It's a regular page
        schema = SchemaGenerator.generate_webpage_schema(page, request)

    schemas.append(schema)

    # Add breadcrumb schema
    breadcrumb = SchemaGenerator.generate_breadcrumb_schema(page, request)
    if breadcrumb:
        schemas.append(breadcrumb)

    return schemas
