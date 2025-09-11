# Compatibility layer for old migrations
# This app exists only to satisfy migration dependencies
# All file/media functionality is in apps.files

from apps.files.models import FileUpload


class Asset(FileUpload):
    """Proxy model for backward compatibility with old migrations."""

    class Meta:
        proxy = True
