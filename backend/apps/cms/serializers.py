from rest_framework import serializers

from .models import Page
from .seo import SeoSettings


class PageReadSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    resolved_seo = serializers.SerializerMethodField()
    seo_links = serializers.SerializerMethodField()
    recent_revisions = serializers.SerializerMethodField()
    blocks = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id",
            "group_id",
            "locale",
            "parent",
            "position",
            "path",
            "title",
            "slug",
            "status",
            "published_at",
            "scheduled_publish_at",
            "scheduled_unpublish_at",
            "updated_at",
            "blocks",
            "seo",
            "children_count",
            "resolved_seo",
            "seo_links",
            "recent_revisions",
        ]

    def get_blocks(self, obj):
        """Add component field to each block for frontend compatibility."""
        blocks = obj.blocks or []
        processed_blocks = []

        for block in blocks:
            # Create a copy to avoid modifying the original
            processed_block = dict(block)

            # Add component field if not present
            if "component" not in processed_block and "type" in processed_block:
                # Map type to component name (e.g.,
                    'faq' -> 'faq',
                    'hero' -> 'hero')
                # The component field tells frontend exactly which component to load
                processed_block["component"] = processed_block["type"]

            processed_blocks.append(processed_block)

        return processed_blocks

    def get_children_count(self, obj):
        # Use cached count if available from prefetch_related annotation
        if hasattr(obj, "_children_count"):
            return obj._children_count
        return obj.children.count()

    def get_resolved_seo(self, obj):
        """Return resolved SEO if with_seo=1 parameter is provided."""
        request = self.context.get("request")
        if request and request.query_params.get("with_seo") == "1":
            try:
                from .seo_utils import resolve_seo

                return resolve_seo(obj)
            except ImportError as e:
                print(f"SEO import error: {e}")
                return {"error": str(e)}
        return None

    def get_seo_links(self, obj):
        """Return SEO links (canonical + alternates) if with_seo=1 parameter is provided."""
        request = self.context.get("request")
        if request and request.query_params.get("with_seo") == "1":
            try:
                from .seo_utils import generate_seo_links

                return generate_seo_links(obj)
            except ImportError as e:
                print(f"SEO links import error: {e}")
                return {"error": str(e)}
        return None

    def get_recent_revisions(self, obj):
        """Return the 5 most recent revisions for this page."""
        # print(f"DEBUG: get_recent_revisions called for page {obj.id} in serializers.py")

        # Return mock revision data since database versioning isn't configured yet
        from datetime import datetime, timedelta

        now = datetime.now()

        mock_revisions = [
            {
                "id": f"rev-{obj.id}-1",
                "created_at": (now - timedelta(hours=2)).isoformat(),
                "created_by_email": "john.doe@example.com",
                "created_by_name": "John Doe",
                "is_published_snapshot": True,
                "is_autosave": False,
                "comment": "Published latest changes",
                "block_count": 5,
                "revision_type": "published",
            },
            {
                "id": f"rev-{obj.id}-2",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "created_by_email": "jane.smith@example.com",
                "created_by_name": "Jane Smith",
                "is_published_snapshot": False,
                "is_autosave": True,
                "comment": "",
                "block_count": 5,
                "revision_type": "autosave",
            },
            {
                "id": f"rev-{obj.id}-3",
                "created_at": (now - timedelta(days=3)).isoformat(),
                "created_by_email": "admin@example.com",
                "created_by_name": "Admin",
                "is_published_snapshot": False,
                "is_autosave": False,
                "comment": "Initial version",
                "block_count": 3,
                "revision_type": "manual",
            },
        ]

        # print(
        #     f"DEBUG: Returning {len(mock_revisions)} mock revisions from serializers.py"
        # )
        return mock_revisions


class PageTreeItemSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["id",
            "title",
            "slug",
            "path",
            "position",
            "status",
            "children_count"]

    def get_children_count(self, obj):
        # Use cached count if available from prefetch_related annotation
        if hasattr(obj, "_children_count"):
            return obj._children_count
        return obj.children.count()


class PageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = [
            "parent",
            "locale",
            "title",
            "slug",
            "status",
            "scheduled_publish_at",
            "scheduled_unpublish_at",
        ]

    def validate_scheduled_publish_at(self, value):
        """Validate scheduled publish date."""
        if value:
            from django.utils import timezone

            if value <= timezone.now():
                raise serializers.ValidationError(
                    "Scheduled publish time must be in the future"
                )
        return value

    def validate_scheduled_unpublish_at(self, value):
        """Validate scheduled unpublish date."""
        if value:
            from django.utils import timezone

            if value <= timezone.now():
                raise serializers.ValidationError(
                    "Scheduled unpublish time must be in the future"
                )
        return value

    def validate(self, attrs):
        """Cross-field validation."""
        status = attrs.get("status")
        scheduled_publish_at = attrs.get("scheduled_publish_at")
        scheduled_unpublish_at = attrs.get("scheduled_unpublish_at")

        # If status is scheduled, scheduled_publish_at is required
        if status == "scheduled" and not scheduled_publish_at:
            raise serializers.ValidationError(
                {"scheduled_publish_at": "Required when status is scheduled"}
            )

        # If both are set, unpublish must be after publish
        if scheduled_publish_at and scheduled_unpublish_at:
            if scheduled_unpublish_at <= scheduled_publish_at:
                raise serializers.ValidationError(
                    {"scheduled_unpublish_at": "Must be after scheduled publish time"}
                )

        return attrs


class SeoSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoSettings
        fields = [
            "id",
            "locale",
            "title_suffix",
            "default_description",
            "robots_default",
            "jsonld_default",
            "created_at",
            "updated_at",
            # 'default_og_asset' will be added in Phase 3
        ]


# SeoDefaultsSerializer removed - section-based defaults no longer needed
