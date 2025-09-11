"""
Public-facing serializers optimized for frontend consumption.
Includes resolved SEO data and minimal field exposure.
"""

from rest_framework import serializers
from apps.cms.models import Page
from apps.cms.seo_utils import resolve_seo, generate_seo_links
from apps.cms.models import BlockType
from apps.i18n.models import Locale


class PublicPageSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for public page consumption.
    Includes resolved SEO and minimal necessary fields for performance.
    """

    resolved_seo = serializers.SerializerMethodField()
    seo_links = serializers.SerializerMethodField()
    locale_code = serializers.CharField(source="locale.code", read_only=True)
    locale_name = serializers.CharField(source="locale.name", read_only=True)
    url = serializers.CharField(source="path", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "title",
            "slug",
            "path",
            "url",  # Alias for path
            "status",
            "blocks",
            "locale_code",
            "locale_name",
            "published_at",
            "updated_at",
            "resolved_seo",
            "seo_links",
            # Navigation flags for menu building
            "in_main_menu",
            "in_footer",
            "is_homepage",
        ]
        read_only_fields = fields

    def get_resolved_seo(self, obj):
        """Get resolved SEO data (global + page overrides)."""
        try:
            resolved = resolve_seo(obj)

            # Add computed fields for frontend convenience
            base_url = getattr(
                self.context.get("request"), "build_absolute_uri", lambda x: x
            )("/")
            canonical_url = f"{base_url.rstrip('/')}{obj.path}"

            return {
                **resolved,
                "canonical_url": canonical_url,
                "page_url": canonical_url,
                "locale_code": obj.locale.code,
            }
        except Exception as e:
            # Fallback to basic SEO if resolution fails
            return {
                "title": obj.title,
                "description": getattr(obj, "excerpt", ""),
                "robots": (
                    "noindex,nofollow" if obj.status == "draft" else "index,follow"
                ),
                "canonical_url": (
                    self.context.get("request").build_absolute_uri(obj.path)
                    if self.context.get("request")
                    else obj.path
                ),
                "locale_code": obj.locale.code,
            }

    def get_seo_links(self, obj):
        """Get canonical and hreflang data."""
        try:
            request = self.context.get("request")
            if request:
                base_url = request.build_absolute_uri("/")
                return generate_seo_links(obj, base_url)
            return {}
        except Exception:
            return {}


class PublicPageListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for page listings (navigation, search results).
    Excludes heavy fields like blocks and resolved SEO.
    """

    locale_code = serializers.CharField(source="locale.code", read_only=True)
    url = serializers.CharField(source="path", read_only=True)
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id",
            "title",
            "slug",
            "path",
            "url",
            "status",
            "locale_code",
            "published_at",
            "updated_at",
            "excerpt",
            "in_main_menu",
            "in_footer",
            "is_homepage",
        ]
        read_only_fields = fields

    def get_excerpt(self, obj):
        """Generate excerpt from page SEO description or blocks."""
        # Try SEO description first
        if obj.seo and obj.seo.get("description"):
            return obj.seo["description"]

        # Fallback: extract from first text block
        if obj.blocks:
            for block in obj.blocks:
                if block.get("type") in ["richtext", "paragraph", "text"]:
                    content = block.get("props", {}).get("content", "")
                    if content:
                        # Strip HTML and truncate
                        import re

                        clean_text = re.sub(r"<[^>]+>", "", str(content))
                        return (
                            clean_text[:200] + "..."
                            if len(clean_text) > 200
                            else clean_text
                        )

        return ""


class BlockMetadataSerializer(serializers.Serializer):
    """
    Serializer for block type metadata needed by the frontend.
    """

    type = serializers.CharField()
    component = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    category = serializers.CharField()
    icon = serializers.CharField()
    preload = serializers.BooleanField()
    editing_mode = serializers.CharField()
    schema = serializers.JSONField()
    default_props = serializers.JSONField()
