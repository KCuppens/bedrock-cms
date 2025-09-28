import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    F,
    PositiveIntegerField,
    TextField,
    UUIDField,
)
from django.utils import timezone

from apps.core.enums import FileType
from apps.core.mixins import TimestampMixin, UserTrackingMixin
from apps.core.utils import format_file_size

User = get_user_model()


class MediaCategory(models.Model):
    """Category for organizing media files."""

    name = models.CharField(max_length=100, help_text="Category name")
    slug = models.SlugField(max_length=120, unique=True, help_text="URL slug")
    description = models.TextField(blank=True, help_text="Category description")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Media Category"
        verbose_name_plural = "Media Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class FileUpload(TimestampMixin, UserTrackingMixin):
    """File upload model with S3/MinIO storage"""

    # File identification

    id: UUIDField = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )

    original_filename: CharField = models.CharField("Original filename", max_length=255)

    filename: CharField = models.CharField(
        "Stored filename", max_length=255, unique=True
    )

    # File metadata

    file_type: CharField = models.CharField(
        "File type", max_length=20, choices=FileType.choices, default=FileType.OTHER
    )

    mime_type: CharField = models.CharField("MIME type", max_length=100)

    file_size: PositiveIntegerField = models.PositiveIntegerField("File size (bytes)")

    checksum: CharField = models.CharField(
        "File checksum", max_length=64, blank=True, db_index=True
    )

    # Storage info

    storage_path: TextField = models.TextField("Storage path")

    is_public: BooleanField = models.BooleanField("Public access", default=False)

    # File details

    description: TextField = models.TextField("Description", blank=True)

    tags: CharField = models.CharField("Tags", max_length=500, blank=True)

    # Image-specific fields for thumbnail generation

    width: PositiveIntegerField = models.PositiveIntegerField(
        "Image width", null=True, blank=True, help_text="Image width in pixels"
    )

    height: PositiveIntegerField = models.PositiveIntegerField(
        "Image height", null=True, blank=True, help_text="Image height in pixels"
    )

    blurhash: CharField = models.CharField(
        "BlurHash",
        max_length=100,
        blank=True,
        help_text="BlurHash for ultra-fast image placeholders",
    )

    dominant_color: CharField = models.CharField(
        "Dominant color",
        max_length=7,
        blank=True,
        help_text="Dominant color as hex value (e.g., #FF5733)",
    )

    thumbnails: models.JSONField = models.JSONField(
        "Thumbnails",
        default=dict,
        help_text="Generated thumbnail configurations and URLs",
    )

    # Access control

    expires_at: DateTimeField = models.DateTimeField(
        "Expires at", null=True, blank=True
    )

    download_count: PositiveIntegerField = models.PositiveIntegerField(
        "Download count", default=0
    )

    class Meta:

        verbose_name = "File Upload"

        verbose_name_plural = "File Uploads"

        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=["created_by", "-created_at"]),
            models.Index(fields=["file_type", "-created_at"]),
            models.Index(fields=["is_public", "expires_at"]),
            models.Index(fields=["checksum"]),
            models.Index(fields=["tags"]),
        ]

    def __str__(self):  # noqa: C901

        return self.original_filename

    @property
    def file_size_human(self):  # noqa: C901
        """Human readable file size"""

        return format_file_size(self.file_size)

    @property
    def is_expired(self):  # noqa: C901
        """Check if file has expired"""

        if not self.expires_at:

            return False

        return timezone.now() > self.expires_at

    @property
    def is_image(self):  # noqa: C901
        """Check if file is an image"""

        return self.file_type == FileType.IMAGE

    @property
    def is_document(self):  # noqa: C901
        """Check if file is a document"""

        return self.file_type == FileType.DOCUMENT

    def can_access(self, user=None):  # noqa: C901
        """Check if user can access this file"""

        # Public files are accessible to all

        if self.is_public and not self.is_expired:

            return True

        # Anonymous users can only access public files

        if not user or not user.is_authenticated:

            return False

        # Owners can always access their files

        if self.created_by == user:

            return True

        # Admins can access all files

        if user.is_admin():

            return True

        return False

    def increment_download_count(self):  # noqa: C901
        """Increment download counter atomically using F expression"""

        FileUpload.objects.filter(pk=self.pk).update(
            download_count=F("download_count") + 1
        )

    def get_download_url(self, expires_in=3600):  # noqa: C901
        """Get signed download URL"""
        from apps.files.services import FileService

        return FileService.get_download_url(self, expires_in)

    def get_upload_url(self, expires_in=3600):  # noqa: C901
        """Get signed upload URL"""
        from apps.files.services import FileService

        return FileService.get_upload_url(self.storage_path, expires_in)

    @property
    def aspect_ratio(self):  # noqa: C901
        """Calculate image aspect ratio"""
        if self.width and self.height:
            return self.width / self.height
        return None

    def get_thumbnails_for_config(self, config_hash):  # noqa: C901
        """Get thumbnail URLs for a specific configuration hash"""
        return self.thumbnails.get("config_hashes", {}).get(config_hash, {})

    def add_thumbnails_for_config(self, config_hash, thumbnail_urls):  # noqa: C901
        """Add thumbnail URLs for a specific configuration"""
        if "config_hashes" not in self.thumbnails:
            self.thumbnails["config_hashes"] = {}

        self.thumbnails["config_hashes"][config_hash] = thumbnail_urls
        self.save(update_fields=["thumbnails"])

    def has_thumbnails_for_config(self, config_hash):  # noqa: C901
        """Check if thumbnails exist for a configuration"""
        return config_hash in self.thumbnails.get("config_hashes", {})

    def get_all_thumbnail_urls(self):  # noqa: C901
        """Get all thumbnail URLs across all configurations"""
        all_urls = []
        for config_thumbnails in self.thumbnails.get("config_hashes", {}).values():
            all_urls.extend(config_thumbnails.values())
        return all_urls
