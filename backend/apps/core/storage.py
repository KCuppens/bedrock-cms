"""
Custom storage backends for different use cases.
"""

from django.conf import settings

try:
    from storages.backends.s3boto3 import S3Boto3Storage

    class S3MediaStorage(S3Boto3Storage):
        """Custom S3 storage for media files."""

        location = "media"
        default_acl = getattr(settings, "AWS_DEFAULT_ACL", "public-read")
        file_overwrite = False

    class S3StaticStorage(S3Boto3Storage):
        """Custom S3 storage for static files."""

        location = "static"
        default_acl = "public-read"
        file_overwrite = True

except ImportError:
    # django-storages not available, create dummy classes
    class S3MediaStorage:  # type: ignore[no-redef]
        """Dummy S3 storage class when django-storages is not available."""

        pass

    class S3StaticStorage:  # type: ignore[no-redef]
        """Dummy S3 storage class when django-storages is not available."""

        pass
