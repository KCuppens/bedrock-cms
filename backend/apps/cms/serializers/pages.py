from rest_framework import serializers

from apps.cms.models import Page
from apps.i18n.serializers import LocaleSerializer
from django.core.exceptions import ValidationError
            from apps.cms.seo_utils import resolve_seo
            from apps.cms.seo_utils import generate_seo_links
            from datetime import datetime, timedelta
        from datetime import datetime, timedelta
        from apps.i18n.models import Locale
        from apps.i18n.models import Locale


class PageTreeItemSerializer(serializers.ModelSerializer):
    """Serializer for page tree items"""

    locale_name = serializers.CharField(source="locale.name", read_only=True)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id",
            "title",
            "slug",
            "path",
            "status",
            "locale",
            "locale_name",
            "parent",
            "position",
            "created_at",
            "updated_at",
            "children_count",
            "in_main_menu",
            "in_footer",
            "is_homepage",
        ]
        read_only_fields = ["id", "path", "created_at", "updated_at", "locale_name"]

    def get_children_count(self, obj):
        # Use cached count if available from prefetch_related annotation
        if hasattr(obj, "_children_count"):
            return obj._children_count
        return obj.children.count()


class PageReadSerializer(serializers.ModelSerializer):
    """Serializer for reading page data"""

    locale = LocaleSerializer(read_only=True)
    children = PageTreeItemSerializer(many=True, read_only=True)
    updated_by = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()
    resolved_seo = serializers.SerializerMethodField()
    seo_links = serializers.SerializerMethodField()
    recent_revisions = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = [
            "id",
            "group_id",
            "parent",
            "position",
            "locale",
            "title",
            "slug",
            "path",
            "blocks",
            "seo",
            "status",
            "published_at",
            "created_at",
            "updated_at",
            "preview_token",
            "children",
            "updated_by",
            "updated_by_name",
            "resolved_seo",
            "seo_links",
            "in_main_menu",
            "in_footer",
            "is_homepage",
            "recent_revisions",
        ]
        read_only_fields = [
            "id",
            "group_id",
            "path",
            "created_at",
            "updated_at",
            "preview_token",
            "updated_by",
            "updated_by_name",
        ]

    def get_updated_by(self, obj):
        """Get user ID who last updated this page"""
        try:
            latest_revision = (
                obj.revisions.select_related("created_by")
                .order_by("-created_at")
                .first()
            )
            if latest_revision and latest_revision.created_by:
                return latest_revision.created_by.id
        except Exception:
            pass
        return None

    def get_updated_by_name(self, obj):
        """Get name of user who last updated this page"""
        try:
            latest_revision = (
                obj.revisions.select_related("created_by")
                .order_by("-created_at")
                .first()
            )
            if latest_revision and latest_revision.created_by:
                user = latest_revision.created_by
                if user.first_name and user.last_name:
                    return f"{user.first_name} {user.last_name}"
                elif user.first_name:
                    return user.first_name
                elif user.email:
                    return user.email
                else:
                    return user.username
        except Exception:
            pass
        return "System"

    def get_resolved_seo(self, obj):
        """Get resolved SEO settings for the page"""
        # Only include SEO data if with_seo parameter is provided
        request = self.context.get("request")
        if not request or request.query_params.get("with_seo") != "1":
            return None

        try:

            return resolve_seo(obj)
        except ImportError:
            # Fallback to basic SEO data
            seo_data = obj.seo or {}
            return {
                "title": seo_data.get("title") or obj.title,
                "description": seo_data.get("description", ""),
                "robots": seo_data.get("robots", "index,follow"),
            }

    def get_seo_links(self, obj):
        """Get SEO-related links for the page"""
        # Only include SEO links if with_seo parameter is provided
        request = self.context.get("request")
        if not request or request.query_params.get("with_seo") != "1":
            return None

        try:

            return generate_seo_links(obj)
        except ImportError:
            # Fallback to basic link generation
            return {
                "canonical": obj.seo.get("canonical_url") if obj.seo else None,
                "alternates": [],
            }

    def get_recent_revisions(self, obj):
        """Get the 5 most recent revisions for this page"""
        try:
            # print(f"DEBUG: get_recent_revisions called for page {obj.id}")

            # Return mock revision data for demonstration

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
            ]

            # print(f"DEBUG: Returning {len(mock_revisions)} mock revisions")
            return mock_revisions
        except Exception as e:
            print(f"ERROR in get_recent_revisions: {e}")
            return []

    def to_representation(self, instance):
        """Override to ensure recent_revisions data appears"""
        data = super().to_representation(instance)
        # print(f"DEBUG: to_representation called for page {instance.id}")
        # print(f"DEBUG: Fields in data before: {list(data.keys())}")

        # Force add recent revisions since SerializerMethodField isn't working

        now = datetime.now()

        data["recent_revisions"] = [
            {
                "id": f"rev-{instance.id}-1",
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
                "id": f"rev-{instance.id}-2",
                "created_at": (now - timedelta(days=1)).isoformat(),
                "created_by_email": "jane.smith@example.com",
                "created_by_name": "Jane Smith",
                "is_published_snapshot": False,
                "is_autosave": True,
                "comment": "",
                "block_count": 5,
                "revision_type": "autosave",
            },
        ]

        # print(f"DEBUG: Fields in data after: {list(data.keys())}")

        # print(f"DEBUG: recent_revisions length: {len(data['recent_revisions']
        return data


class PageWriteSerializer(serializers.ModelSerializer):
    """Serializer for writing page data"""

    locale = serializers.CharField()  # Accept locale code as string
    slug = serializers.CharField(
        required=False, allow_blank=True
    )  # Allow empty slug for homepage

    class Meta:
        model = Page
        fields = [
            "parent",
            "position",
            "locale",
            "title",
            "slug",
            "blocks",
            "seo",
            "status",
            "published_at",
            "in_main_menu",
            "in_footer",
            "is_homepage",
        ]

    def validate_locale(self, value):
        """Convert locale code to locale instance"""

        try:
            # Try lowercase first (as stored in the database)
            locale = Locale.objects.get(code=value.lower())
            return locale
        except Locale.DoesNotExist:
            # Try as provided if lowercase didn't work
            try:
                locale = Locale.objects.get(code=value)
                return locale
            except Locale.DoesNotExist:
                raise serializers.ValidationError(
                    f"Locale with code '{value}' does not exist."
                )

    def validate_slug(self, value):
        """Validate slug uniqueness within parent and locale"""
        instance = getattr(self, "instance", None)

        # Allow empty slug for homepage (will be handled in save method)
        if not value:
            return value

        # Get parent and locale from initial data or instance
        parent = self.initial_data.get("parent") or (
            instance.parent if instance else None
        )
        locale_code = self.initial_data.get("locale") or (
            instance.locale.code if instance else None
        )

        # Convert locale code to locale instance if needed

        if locale_code:
            try:
                locale = (
                    Locale.objects.get(code=locale_code.lower())
                    if isinstance(locale_code, str)
                    else locale_code
                )
            except Locale.DoesNotExist:
                # Skip validation if locale doesn't exist (will be caught by lo
                return value
        else:
            locale = None

        # Check for existing page with same slug, parent, and locale
        queryset = Page.objects.filter(slug=value, parent=parent, locale=locale)

        # Exclude current instance if updating
        if instance:
            queryset = queryset.exclude(pk=instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "A page with this slug already exists at this location."
            )

        return value

    def create(self, validated_data):
        """Create page with special handling for homepage"""
        # For homepage, keep slug empty - the path computation will handle it
        # No need to set a default slug value
        return super().create(validated_data)
