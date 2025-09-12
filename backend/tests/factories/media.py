"""
Media and file factories for testing uploads and media management.
"""

import factory
import factory.django
from django.core.files.base import ContentFile
from faker import Faker

from apps.media.models import MediaItem

from .base import BaseFactory, UserFactory

fake = Faker()


class MediaItemFactory(BaseFactory):
    """Factory for creating media items."""

    class Meta:
        model = MediaItem

    title = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("sentence", nb_words=10)
    file_type = factory.Iterator(["image", "video", "document", "audio"])
    mime_type = factory.LazyAttribute(
        lambda obj: {
            "image": "image/jpeg",
            "video": "video/mp4",
            "document": "application/pdf",
            "audio": "audio/mp3",
        }.get(obj.file_type, "application/octet-stream")
    )

    file_size = factory.LazyAttribute(
        lambda obj: fake.random_int(min=1024, max=10485760)
    )  # 1KB to 10MB

    # Generate realistic filename
    original_filename = factory.LazyAttribute(
        lambda obj: f"{fake.slug()}.{obj.mime_type.split('/')[-1]}"
    )

    uploaded_by = factory.SubFactory(UserFactory)

    # Generate file content (simplified for testing)
    file = factory.LazyAttribute(
        lambda obj: ContentFile(b"test file content", name=obj.original_filename)
    )

    # Metadata based on file type
    metadata = factory.LazyAttribute(
        lambda obj: {
            "image": {
                "width": fake.random_int(min=100, max=4000),
                "height": fake.random_int(min=100, max=4000),
                "format": "JPEG",
            },
            "video": {
                "duration": fake.random_int(min=10, max=3600),
                "resolution": f"{fake.random_int(min=480, max=1920)}x{fake.random_int(min=360, max=1080)}",
            },
            "document": {"pages": fake.random_int(min=1, max=100)},
            "audio": {
                "duration": fake.random_int(min=30, max=600),
                "bitrate": "320kbps",
            },
        }.get(obj.file_type, {})
    )


class ImageFactory(MediaItemFactory):
    """Factory specifically for images."""

    file_type = "image"
    mime_type = "image/jpeg"


class DocumentFactory(MediaItemFactory):
    """Factory specifically for documents."""

    file_type = "document"
    mime_type = "application/pdf"


__all__ = ["MediaItemFactory", "ImageFactory", "DocumentFactory"]
