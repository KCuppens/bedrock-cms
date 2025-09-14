import re

from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework import serializers

from apps.files.models import FileUpload
from apps.i18n.models import Locale

from .models import BlogPost, BlogSettings, Category, Tag
from .versioning import BlogPostRevision

"""Blog serializers for API endpoints."""

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model."""

    post_count = serializers.IntegerField(read_only=True)

    class Meta:

        model = Tag

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "post_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "slug", "post_count", "created_at", "updated_at"]


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model."""

    post_count = serializers.IntegerField(read_only=True)

    presentation_page_title = serializers.CharField(
        source="presentation_page.title", read_only=True
    )

    class Meta:

        model = Category

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "color",
            "presentation_page",
            "presentation_page_title",
            "is_active",
            "post_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "slug", "post_count", "created_at", "updated_at"]

    def validate_color(self, value):  # noqa: C901
        """Validate hex color format."""

        if not re.match(r"^#[0-9a-fA-F]{6}$", value):

            raise serializers.ValidationError(
                "Color must be a valid hex color (e.g., #6366f1)"
            )

        return value


class BlogPostListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for blog post listings."""

    author_name = serializers.CharField(source="author.get_full_name", read_only=True)

    category_name = serializers.CharField(source="category.name", read_only=True)

    tag_names = serializers.SerializerMethodField()

    reading_time = serializers.SerializerMethodField()

    locale_code = serializers.CharField(source="locale.code", read_only=True)

    class Meta:

        model = BlogPost

        fields = [
            "id",
            "group_id",
            "locale",
            "locale_code",
            "title",
            "slug",
            "excerpt",
            "author",
            "author_name",
            "category",
            "category_name",
            "tag_names",
            "status",
            "featured",
            "reading_time",
            "published_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "group_id",
            "author_name",
            "category_name",
            "tag_names",
            "reading_time",
            "locale_code",
            "created_at",
            "updated_at",
        ]

    def get_tag_names(self, obj):  # noqa: C901
        """Get list of tag names."""

        return list(obj.tags.values_list("name", flat=True))

    def get_reading_time(self, obj):  # noqa: C901
        """Get estimated reading time."""

        return obj.get_reading_time()


class BlogPostSerializer(serializers.ModelSerializer):
    """Full serializer for blog posts."""

    author_name = serializers.CharField(source="author.get_full_name", read_only=True)

    category_data = CategorySerializer(source="category", read_only=True)

    tag_data = TagSerializer(source="tags", many=True, read_only=True)

    reading_time = serializers.SerializerMethodField()

    locale_code = serializers.CharField(source="locale.code", read_only=True)

    related_posts = serializers.SerializerMethodField()

    revision_count = serializers.SerializerMethodField()

    blocks = serializers.SerializerMethodField()

    social_image = serializers.PrimaryKeyRelatedField(
        required=False, allow_null=True, read_only=True
    )

    class Meta:

        model = BlogPost

        fields = [
            "id",
            "group_id",
            "locale",
            "locale_code",
            "title",
            "slug",
            "excerpt",
            "content",
            "blocks",
            "author",
            "author_name",
            "category",
            "category_data",
            "tags",
            "tag_data",
            "seo",
            "status",
            "featured",
            "allow_comments",
            "published_at",
            "scheduled_publish_at",
            "scheduled_unpublish_at",
            "social_image",
            "reading_time",
            "related_posts",
            "revision_count",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "group_id",
            "author_name",
            "category_data",
            "tag_data",
            "locale_code",
            "reading_time",
            "related_posts",
            "revision_count",
            "created_at",
            "updated_at",
        ]

    def get_reading_time(self, obj):  # noqa: C901
        """Get estimated reading time."""

        return obj.get_reading_time()

    def get_related_posts(self, obj):  # noqa: C901
        """Get related posts with optimized querying."""

        # Use optimized queryset for serialization to prevent N+1 queries
        related = (
            obj.get_related_posts(limit=3)
            .select_related("locale", "author", "category")
            .prefetch_related("tags")
            .only(
                # Only fetch fields needed by BlogPostListSerializer
                "id",
                "group_id",
                "title",
                "slug",
                "excerpt",
                "status",
                "featured",
                "published_at",
                "created_at",
                "updated_at",
                "locale__code",
                "author__first_name",
                "author__last_name",
                "author__email",
                "category__name",
            )
        )

        return BlogPostListSerializer(related, many=True).data

    def get_revision_count(self, obj):  # noqa: C901
        """Get count of revisions for this post."""

        try:

            return BlogPostRevision.objects.filter(blog_post=obj).count()

        except ImportError:

            return 0

    def get_blocks(self, obj):  # noqa: C901
        """Add component field to each block for frontend compatibility."""

        blocks = obj.blocks or []

        processed_blocks = []

        for block in blocks:

            # Create a copy to avoid modifying the original

            processed_block = dict(block)

            # Add component field if not present

            if "component" not in processed_block and "type" in processed_block:

                # Map type to component name (e.g., 'faq' -> 'faq', 'hero' -> 'hero')

                # The component field tells frontend exactly which component to load

                processed_block["component"] = processed_block["type"]

            """processed_blocks.append(processed_block)"""

        return processed_blocks

    def validate_status(self, value):  # noqa: C901
        """Validate status transitions."""

        if (
            self.instance
            and hasattr(self.instance, "status")
            and self.instance.status == "published"
            and value == "draft"
        ):

            # Allow unpublishing but warn about SEO impact
            pass

        return value

    def validate_scheduled_publish_at(self, value):  # noqa: C901
        """Validate scheduled publish date."""

        if value and value <= timezone.now():

            raise serializers.ValidationError(
                "Scheduled publish time must be in the future."
            )

        return value

    def validate_scheduled_unpublish_at(self, value):  # noqa: C901
        """Validate scheduled unpublish date."""

        if value and value <= timezone.now():

            raise serializers.ValidationError(
                "Scheduled unpublish time must be in the future."
            )

        return value

    def validate(self, attrs):  # noqa: C901
        """Cross-field validation."""

        status = attrs.get("status", getattr(self.instance, "status", None))

        scheduled_publish_at = attrs.get(
            "scheduled_publish_at", getattr(self.instance, "scheduled_publish_at", None)
        )

        scheduled_unpublish_at = attrs.get(
            "scheduled_unpublish_at",
            getattr(self.instance, "scheduled_unpublish_at", None),
        )

        if status == "scheduled" and not scheduled_publish_at:

            raise serializers.ValidationError(
                "Scheduled posts must have a scheduled publication date."
            )

        if status != "scheduled" and scheduled_publish_at:

            # Clear scheduled_publish_at if status is not scheduled

            attrs["scheduled_publish_at"] = None

        # If both are set, unpublish must be after publish

        if scheduled_publish_at and scheduled_unpublish_at:

            if scheduled_unpublish_at <= scheduled_publish_at:

                raise serializers.ValidationError(
                    {"scheduled_unpublish_at": "Must be after scheduled publish time"}
                )

        return attrs

    def create(self, validated_data):  # noqa: C901
        """Create a new blog post."""

        # Set author from request user if not provided

        if "author" not in validated_data:

            validated_data["author"] = self.context["request"].user

        # Handle publishing

        if validated_data.get("status") == "published" and not validated_data.get(
            "published_at"
        ):

            validated_data["published_at"] = timezone.now()

        return super().create(validated_data)

    def update(self, instance, validated_data):  # noqa: C901
        """Update a blog post."""

        # Handle publishing

        if validated_data.get("status") == "published" and not instance.published_at:

            validated_data["published_at"] = timezone.now()

        return super().update(instance, validated_data)


class BlogPostWriteSerializer(serializers.ModelSerializer):
    """Write-only serializer for creating/updating blog posts."""

    social_image = serializers.PrimaryKeyRelatedField(
        queryset=FileUpload.objects.all(),
        required=False,
        allow_null=True,
        pk_field=serializers.UUIDField(format="hex_verbose"),
    )

    class Meta:

        model = BlogPost

        fields = [
            "locale",
            "title",
            "slug",
            "excerpt",
            "content",
            "blocks",
            "category",
            "tags",
            "seo",
            "status",
            "featured",
            "allow_comments",
            "scheduled_publish_at",
            "scheduled_unpublish_at",
            "social_image",
        ]

    def validate_slug(self, value):  # noqa: C901
        """Validate slug uniqueness within locale."""

        if self.instance:

            # Update case - exclude current instance

            queryset = (
                BlogPost.objects.filter(
                    slug=value, locale=self.instance.locale
                ).exclude(id=self.instance.id)
                if hasattr(self.instance, "locale") and hasattr(self.instance, "id")
                else BlogPost.objects.none()
            )

        else:

            # Create case - check against all posts in the locale

            locale = self.initial_data.get("locale")

            if locale:

                queryset = BlogPost.objects.filter(slug=value, locale=locale)

            else:

                # Can't validate without locale

                return value

        if queryset.exists():

            raise serializers.ValidationError(
                "A blog post with this slug already exists in this locale."
            )

        return value


class BlogPostRevisionSerializer(serializers.Serializer):
    """Serializer for blog post revisions."""

    id = serializers.UUIDField(read_only=True)

    snapshot = serializers.JSONField(read_only=True)

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    created_at = serializers.DateTimeField(read_only=True)

    is_published_snapshot = serializers.BooleanField(read_only=True)

    is_autosave = serializers.BooleanField(read_only=True)

    comment = serializers.CharField(read_only=True)


class BlogPostAutosaveSerializer(serializers.Serializer):
    """Serializer for autosave functionality."""

    title = serializers.CharField(required=False)

    content = serializers.CharField(required=False, allow_blank=True)

    blocks = serializers.JSONField(required=False)

    excerpt = serializers.CharField(required=False, allow_blank=True)


class BlogPostDuplicateSerializer(serializers.Serializer):
    """Serializer for duplicating blog posts."""

    title = serializers.CharField(help_text="Title for the duplicated post")

    locale = serializers.PrimaryKeyRelatedField(
        queryset=Locale.objects.all(), help_text="Target locale for the duplicate"
    )

    copy_tags = serializers.BooleanField(default=True, help_text="Whether to copy tags")

    copy_category = serializers.BooleanField(
        default=True, help_text="Whether to copy category"
    )

    def __init__(self, *args, **kwargs):  # noqa: C901

        super().__init__(*args, **kwargs)

        # Set the queryset for locale field

        self.fields["locale"].queryset = Locale.objects.filter(is_active=True)


class BlogSettingsSerializer(serializers.ModelSerializer):
    """Serializer for BlogSettings model."""

    locale = serializers.StringRelatedField(read_only=True)

    default_presentation_page_title = serializers.CharField(
        source="default_presentation_page.title", read_only=True
    )

    class Meta:

        model = BlogSettings

        fields = [
            "id",
            "locale",
            "base_path",
            "default_presentation_page",
            "default_presentation_page_title",
            "design_tokens",
            "show_toc",
            "show_author",
            "show_dates",
            "show_share",
            "show_reading_time",
            "feeds_config",
            "seo_defaults",
            "created_at",
            "updated_at",
        ]

        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_design_tokens(self, value):  # noqa: C901
        """Validate design tokens JSON structure."""

        if not isinstance(value, dict):

            raise serializers.ValidationError("Design tokens must be a JSON object")

        # Basic validation of expected keys

        allowed_keys = {
            "content_width",
            "typography_scale",
            "accent_color",
            "font_family",
            "spacing",
            "colors",
        }

        for key in value.keys():

            if key not in allowed_keys:

                raise serializers.ValidationError(
                    f"Unknown design token key: {key}. "
                    f"Allowed keys: {', '.join(sorted(allowed_keys))}"
                )

        return value

    def validate_feeds_config(self, value):  # noqa: C901
        """Validate feeds config JSON structure."""

        if not isinstance(value, dict):

            raise serializers.ValidationError("Feeds config must be a JSON object")

        # Validate items_per_feed if provided

        if "items_per_feed" in value:

            items_per_feed = value["items_per_feed"]

            if (
                not isinstance(items_per_feed, int)
                or items_per_feed < 1
                or items_per_feed > 100
            ):

                raise serializers.ValidationError(
                    "items_per_feed must be an integer between 1 and 100"
                )

        return value

    def validate_seo_defaults(self, value):  # noqa: C901
        """Validate SEO defaults JSON structure."""

        if not isinstance(value, dict):

            raise serializers.ValidationError("SEO defaults must be a JSON object")

        # Validate template strings if provided

        for template_key in ["title_template", "meta_description_template"]:

            if template_key in value:

                template = value[template_key]

                if not isinstance(template, str):

                    raise serializers.ValidationError(
                        f"{template_key} must be a string"
                    )

        return value
