from datetime import datetime, timedelta


from django.utils import timezone


from rest_framework import serializers


from .models import Page

from .seo import SeoSettings

from .seo_utils import generate_seo_links, resolve_seo


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

    def get_blocks(self, obj):  # noqa: C901
        """Add component field to each block for frontend compatibility."""

        blocks = obj.blocks or []

        processed_blocks = []

        for block in blocks:

            # Create a copy to avoid modifying the original

            processed_block = dict(block)

            # Add component field if not present

            if "component" not in processed_block and "type" in processed_block:

                processed_block["component"] = processed_block["type"]

            processed_blocks.append(processed_block)

        return processed_blocks

    def get_children_count(self, obj):  # noqa: C901

        # Use cached count if available from prefetch_related annotation

        if hasattr(obj, "_children_count"):

            return obj._children_count

        return obj.children.count()

    def get_resolved_seo(self, obj):  # noqa: C901
        """Return resolved SEO if with_seo=1 parameter is provided."""

        request = self.context.get("request")

        if request and request.query_params.get("with_seo") == "1":

            try:

                return resolve_seo(obj)

            except ImportError as e:
                return {"error": str(e)}

        return None

    def get_seo_links(self, obj):  # noqa: C901
        """Return SEO links (canonical + alternates)

        if with_seo=1 parameter is provided."""

        request = self.context.get("request")

        if request and request.query_params.get("with_seo") == "1":

            try:

                return generate_seo_links(obj)

            except ImportError as e:
                return {"error": str(e)}

        return None

    def get_recent_revisions(self, obj):  # noqa: C901
        """Return the 5 most recent revisions for this page."""

        # Return mock revision data since database

        # versioning isn't configured yet

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

        return mock_revisions


class PageTreeItemSerializer(serializers.ModelSerializer):

    children_count = serializers.SerializerMethodField()

    class Meta:

        model = Page

        fields = ["id", "title", "slug", "path", "position", "status", "children_count"]

    def get_children_count(self, obj):  # noqa: C901

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

    def validate_scheduled_publish_at(self, value):  # noqa: C901
        """Validate scheduled publish date."""

        if value:

            if value <= timezone.now():

                raise serializers.ValidationError(
                    "Scheduled publish time must be in the future"
                )

        return value

    def validate_scheduled_unpublish_at(self, value):  # noqa: C901
        """Validate scheduled unpublish date."""

        if value:

            if value <= timezone.now():

                raise serializers.ValidationError(
                    "Scheduled unpublish time must be in the future"
                )

        return value

    def validate(self, attrs):  # noqa: C901
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
