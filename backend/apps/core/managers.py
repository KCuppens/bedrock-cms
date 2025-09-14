from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    """Manager that provides soft delete functionality"""

    def get_queryset(self):
        """Return queryset excluding soft-deleted items"""
        return super().get_queryset().filter(is_deleted=False)

    def active(self):
        """Return only active (non-deleted) records"""
        return self.get_queryset().filter(is_deleted=False)

    def deleted(self):
        """Return only soft-deleted records"""
        return self.get_queryset(manager=models.Manager()).filter(is_deleted=True)

    def with_deleted(self):
        """Return all records including soft-deleted ones"""
        return super().get_queryset()


class PublishedManager(models.Manager):
    """Manager that filters for published content"""

    def get_queryset(self):
        """Return base queryset"""
        return super().get_queryset()

    def published(self):
        """Return only published records"""
        now = timezone.now()
        return self.get_queryset().filter(is_published=True, published_at__lte=now)

    def draft(self):
        """Return only draft records"""
        return self.get_queryset().filter(is_published=False)

    def scheduled(self):
        """Return records scheduled for future publication"""
        now = timezone.now()
        return self.get_queryset().filter(is_published=True, published_at__gt=now)
