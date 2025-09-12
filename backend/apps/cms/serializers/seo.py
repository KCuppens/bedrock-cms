import uuid


from rest_framework import serializers


from apps.cms.seo import SeoSettings

from apps.files.models import FileUpload

from apps.i18n.models import Locale


class SeoSettingsSerializer(serializers.ModelSerializer):
    """Serializer for SEO settings."""

    locale_code = serializers.CharField(source="locale.code", read_only=True)

    locale_name = serializers.CharField(source="locale.name", read_only=True)

    locale_id = serializers.PrimaryKeyRelatedField(
        source="locale", queryset=Locale.objects.all(), write_only=True, required=False
    )

    # Override these fields to handle UUID strings

    default_og_asset_id = serializers.CharField(
        source="default_og_asset",
        required=False,
        allow_null=True,
        allow_blank=True,
        write_only=True,
    )

    default_twitter_asset_id = serializers.CharField(
        source="default_twitter_asset",
        required=False,
        allow_null=True,
        allow_blank=True,
        write_only=True,
    )

    # Read-only fields for output

    default_og_asset = serializers.SerializerMethodField(read_only=True)

    default_twitter_asset = serializers.SerializerMethodField(read_only=True)

    default_og_image_url = serializers.SerializerMethodField()

    default_twitter_image_url = serializers.SerializerMethodField()

    class Meta:

        model = SeoSettings

        fields = [
            "id",
            "locale",
            "locale_code",
            "locale_name",
            "locale_id",
            # Basic SEO
            "title_suffix",
            "default_title",
            "default_description",
            "default_keywords",
            # Open Graph
            "default_og_asset",
            "default_og_asset_id",  # Write-only field for UUID string
            "default_og_image_url",
            "default_og_title",
            "default_og_description",
            "default_og_type",
            "default_og_site_name",
            # Twitter Card
            "default_twitter_card",
            "default_twitter_site",
            "default_twitter_creator",
            "default_twitter_asset",
            "default_twitter_asset_id",  # Write-only field for UUID string
            "default_twitter_image_url",
            # Technical SEO
            "robots_default",
            "canonical_domain",
            "google_site_verification",
            "bing_site_verification",
            # Schema.org / JSON-LD
            "jsonld_default",
            "organization_jsonld",
            # Additional Meta Tags
            "meta_author",
            "meta_generator",
            "meta_viewport",
            # Social Media
            """"facebook_app_id","""
            # Timestamps
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "locale_code",
            "locale_name",
            "created_at",
            "updated_at",
        ]

    def get_default_og_asset(self, obj):
        """Get the UUID for the default OG asset."""

        return str(obj.default_og_asset.id) if obj.default_og_asset else None

    def get_default_twitter_asset(self, obj):
        """Get the UUID for the default Twitter asset."""

        return str(obj.default_twitter_asset.id) if obj.default_twitter_asset else None

    def get_default_og_image_url(self, obj):
        """Get the URL for the default OG image asset."""

        if obj.default_og_asset:

            request = self.context.get("request")

            # FileUpload model has get_download_url method

            if hasattr(obj.default_og_asset, "get_download_url"):

                return obj.default_og_asset.get_download_url()

            # Fallback to building URL manually

            if request:

                return request.build_absolute_uri(
                    f"/api/v1/files/{obj.default_og_asset.id}/download/"
                )

        return None

    def get_default_twitter_image_url(self, obj):
        """Get the URL for the default Twitter image asset."""

        if obj.default_twitter_asset:

            request = self.context.get("request")

            # FileUpload model has get_download_url method

            if hasattr(obj.default_twitter_asset, "get_download_url"):

                return obj.default_twitter_asset.get_download_url()

            # Fallback to building URL manually

            if request:

                return request.build_absolute_uri(
                    f"/api/v1/files/{obj.default_twitter_asset.id}/download/"
                )

        return None

    def validate_default_og_asset_id(self, value):
        """Validate and convert UUID string to FileUpload instance."""

        if not value or value == "null" or value == "":

            return None

        try:

            # Validate UUID format first

            uuid.UUID(str(value))

            # Try to get the FileUpload by UUID

            file_obj = FileUpload.objects.get(pk=value)

            # Validate it's an image

            if file_obj.file_type != "image":

                raise serializers.ValidationError(
                    f"File must be an image. Selected file is type: {file_obj.file_type}"
                )

            return file_obj

        except FileUpload.DoesNotExist:

            raise serializers.ValidationError(
                f"Image with ID {value} does not exist. Please select a valid image."
            )

        except ValueError:

            raise serializers.ValidationError(
                f"Invalid image ID format: {value}. Expected a valid UUID."
            )

    def validate_default_twitter_asset_id(self, value):
        """Validate and convert UUID string to FileUpload instance."""

        if not value or value == "null" or value == "":

            return None

        try:

            # Validate UUID format first

            uuid.UUID(str(value))

            # Try to get the FileUpload by UUID

            file_obj = FileUpload.objects.get(pk=value)

            # Validate it's an image

            if file_obj.file_type != "image":

                raise serializers.ValidationError(
                    f"File must be an image. Selected file is type: {file_obj.file_type}"
                )

            return file_obj

        except FileUpload.DoesNotExist:

            raise serializers.ValidationError(
                f"Image with ID {value} does not exist. Please select a valid image."
            )

        except ValueError:

            raise serializers.ValidationError(
                f"Invalid image ID format: {value}. Expected a valid UUID."
            )

    def validate_robots_default(self, value):
        """Validate robots directive."""

        valid_directives = [
            "index",
            "noindex",
            "follow",
            "nofollow",
            "none",
            "noarchive",
            "nosnippet",
        ]

        if value:

            parts = [p.strip() for p in value.lower().split(",")]

            for part in parts:

                if part not in valid_directives:

                    raise serializers.ValidationError(
                        f"Invalid robots directive: {part}"
                    )

        return value

    def validate_jsonld_default(self, value):
        """Validate JSON-LD structure."""

        if value and not isinstance(value, list):

            raise serializers.ValidationError("JSON-LD must be a list of objects")

        return value

    def create(self, validated_data):
        """Create a new SEO settings instance."""

        # The validators have already converted UUID strings to FileUpload instances

        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update an existing SEO settings instance."""

        # The validators have already converted UUID strings to FileUpload instances

        return super().update(instance, validated_data)
