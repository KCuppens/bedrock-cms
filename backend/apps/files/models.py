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

from apps.core.enums import FileType
from apps.core.mixins import TimestampMixin, UserTrackingMixin

User = get_user_model()


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

    def __str__(self):
        return self.original_filename

    @property
    def file_size_human(self):
        """Human readable file size"""
        from apps.core.utils import format_file_size

        return format_file_size(self.file_size)

    @property
    def is_expired(self):
        """Check if file has expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone

        return timezone.now() > self.expires_at

    @property
    def is_image(self):
        """Check if file is an image"""
        return self.file_type == FileType.IMAGE

    @property
    def is_document(self):
        """Check if file is a document"""
        return self.file_type == FileType.DOCUMENT

    def can_access(self, user=None):
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

    def increment_download_count(self):
        """Increment download counter atomically using F expression"""
        FileUpload.objects.filter(pk=self.pk).update(
            download_count=F("download_count") + 1
        )

    def get_download_url(self, expires_in=3600):
        """Get signed download URL"""
        from .services import FileService

        return FileService.get_download_url(self, expires_in)

    def get_upload_url(self, expires_in=3600):
        """Get signed upload URL"""
        from .services import FileService

        return FileService.get_upload_url(self.storage_path, expires_in)
