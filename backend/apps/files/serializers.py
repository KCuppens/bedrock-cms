import os

from rest_framework import serializers

from .models import FileUpload


class FileUploadSerializer(serializers.ModelSerializer):
    """Serializer for FileUpload model"""

    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True
    )

    updated_by_name = serializers.CharField(
        source="updated_by.get_full_name", read_only=True
    )

    file_size_human = serializers.CharField(read_only=True)

    is_expired = serializers.BooleanField(read_only=True)

    download_url = serializers.SerializerMethodField()

    class Meta:

        model = FileUpload

        fields = [
            "id",
            "original_filename",
            "filename",
            "file_type",
            "mime_type",
            "file_size",
            "file_size_human",
            "checksum",
            "is_public",
            "description",
            "tags",
            "expires_at",
            "is_expired",
            "download_count",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "download_url",
            # Image-specific fields
            "width",
            "height",
            "blurhash",
            "dominant_color",
            "thumbnails",
        ]

        read_only_fields = [
            "id",
            "filename",
            "file_type",
            "mime_type",
            "file_size",
            "file_size_human",
            "checksum",
            "storage_path",
            "download_count",
            "created_at",
            "updated_at",
            "created_by",
            "created_by_name",
            "updated_by",
            "updated_by_name",
            "is_expired",
            # Image fields (auto-generated)
            "width",
            "height",
            "blurhash",
            "dominant_color",
            "thumbnails",
        ]

    def get_download_url(self, obj):  # noqa: C901
        """Get download URL if user has access"""

        request = self.context.get("request")

        if request and obj.can_access(request.user):

            return request.build_absolute_uri(f"/api/v1/files/{obj.id}/download/")

        return None


class FileUploadCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating FileUpload"""

    file = serializers.FileField(write_only=True)

    class Meta:

        model = FileUpload

        fields = ["file", "description", "tags", "is_public", "expires_at"]


class SignedUrlSerializer(serializers.Serializer):
    """Serializer for signed upload URL request"""

    filename = serializers.CharField(max_length=255)

    content_type = serializers.CharField(max_length=100, required=False)

    max_size = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=100 * 1024 * 1024,  # 100MB max
        help_text="Maximum file size in bytes",
    )

    def validate_filename(self, value):  # noqa: C901
        """Validate filename"""

        # Check for dangerous characters

        dangerous_chars = ["..", "/", "\\", "<", ">", ":", '"', "|", "?", "*"]

        for char in dangerous_chars:

            if char in value:

                raise serializers.ValidationError(
                    f"Filename contains invalid character: {char}"
                )

        # Check file extension

        file_extension = os.path.splitext(value)[1].lower()

        if not file_extension:

            raise serializers.ValidationError("Filename must have an extension")

        return value


class FileStatsSerializer(serializers.Serializer):
    """Serializer for file statistics"""

    total_files = serializers.IntegerField()

    total_size = serializers.IntegerField()

    total_size_human = serializers.CharField()

    file_types = serializers.DictField()

    recent_uploads = serializers.ListField()


class ThumbnailSizeSerializer(serializers.Serializer):
    """Serializer for individual thumbnail size configuration"""

    width = serializers.IntegerField(min_value=1, max_value=3840)
    height = serializers.IntegerField(min_value=1, max_value=3840, required=False)
    quality = serializers.IntegerField(min_value=1, max_value=100, default=85)


class ThumbnailConfigSerializer(serializers.Serializer):
    """Serializer for thumbnail generation configuration"""

    sizes = serializers.DictField(
        child=ThumbnailSizeSerializer(),
        help_text="Dictionary of size configurations (e.g., {'mobile': {'width': 375, 'quality': 80}})",
    )

    formats = serializers.ListField(
        child=serializers.ChoiceField(choices=["webp", "jpeg", "avif"]),
        default=["webp", "jpeg"],
        help_text="List of formats to generate",
    )

    placeholder = serializers.ChoiceField(
        choices=["blurhash", "dominant-color", "blur"],
        default="blurhash",
        required=False,
        help_text="Type of placeholder to generate",
    )

    priority = serializers.BooleanField(
        default=False, help_text="Whether to process with high priority"
    )

    def validate_sizes(self, value):
        """Validate thumbnail sizes configuration"""
        if not value:
            raise serializers.ValidationError(
                "At least one size configuration is required"
            )

        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 thumbnail sizes allowed")

        for size_name, size_config in value.items():
            if not isinstance(size_name, str) or len(size_name) > 50:
                raise serializers.ValidationError(f"Invalid size name: {size_name}")

        return value


class ThumbnailGenerationResponseSerializer(serializers.Serializer):
    """Serializer for thumbnail generation response"""

    status = serializers.ChoiceField(choices=["processing", "completed", "failed"])
    config_hash = serializers.CharField(max_length=8)
    task_id = serializers.CharField(required=False)
    urls = serializers.DictField(required=False)
    error = serializers.CharField(required=False)


class ThumbnailStatusSerializer(serializers.Serializer):
    """Serializer for thumbnail generation status"""

    file_id = serializers.UUIDField()
    config_hash = serializers.CharField(max_length=8)
    status = serializers.ChoiceField(
        choices=["processing", "completed", "failed", "not_found"]
    )
    urls = serializers.DictField(required=False)
    error = serializers.CharField(required=False)
