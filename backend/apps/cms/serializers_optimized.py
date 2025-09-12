from rest_framework import serializers

from .models import Page, Redirect
from .seo_utils import resolve_seo

Optimized serializers for CMS with reduced field loading.

class PageListSerializer(serializers.ModelSerializer):
    """Minimal serializer for page lists."""

    locale_code = serializers.CharField(source="locale.code", read_only=True)
    children_count = serializers.IntegerField(source="_children_count", read_only=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "title",
            "slug",
            "path",
            "status",
            "locale_code",
            "position",
            "children_count",
            "in_main_menu",
            "in_footer",
            "is_homepage",
            "updated_at",
        ]

class PageDetailSerializer(serializers.ModelSerializer):
    """Full serializer for page detail views."""

    locale = serializers.SerializerMethodField()
    children_count = serializers.IntegerField(source="_children_count", read_only=True)
    blocks = serializers.SerializerMethodField()
    resolved_seo = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = "__all__"

    def get_locale(self, obj):
        return {"id": obj.locale.id, "code": obj.locale.code, "name": obj.locale.name}

    def get_blocks(self, obj):
        """Process blocks with component mapping."""
        blocks = obj.blocks or []
        processed_blocks = []

        for block in blocks:
            processed_block = dict(block)
            if "component" not in processed_block and "type" in processed_block:
                processed_block["component"] = processed_block["type"]
            processed_blocks.append(processed_block)

        return processed_blocks

    def get_resolved_seo(self, obj):
        """Return resolved SEO if requested."""
        request = self.context.get("request")
        if request and request.query_params.get("with_seo") == "1":
            try:

                return resolve_seo(obj)
            except ImportError:
                return None
        return None

class PageMinimalSerializer(serializers.ModelSerializer):
    """Ultra-minimal serializer for references."""

    class Meta:
        model = Page
        fields = ["id", "title", "slug", "path"]

class PageTreeSerializer(serializers.ModelSerializer):
    """Optimized serializer for tree structures."""

    children = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["id", "title", "slug", "path", "position", "children"]

    def get_children(self, obj):
        # Only serialize if children are prefetched
        if (
            hasattr(obj, "_prefetched_objects_cache")
            and "children" in obj._prefetched_objects_cache
        ):
            return PageTreeSerializer(obj.children.all(), many=True).data
        return []

class RedirectListSerializer(serializers.ModelSerializer):
    """Optimized serializer for redirect lists."""

    class Meta:
        model = Redirect
        fields = ["id", "from_path", "to_path", "status", "is_active", "hits"]

class RedirectDetailSerializer(serializers.ModelSerializer):
    """Full serializer for redirect details."""

    class Meta:
        model = Redirect
        fields = "__all__"
