from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Page


@receiver(post_save, sender=Page)
def update_descendant_paths(sender, instance, created, **kwargs):
    """Update paths for all descendants when a page's path changes."""
    if not created:
        # Check if path computation is needed for descendants
        old_path = getattr(instance, "_old_path", None)
        if old_path and old_path != instance.path:
            # Update descendant paths
            descendants = Page.objects.filter(
                path__startswith=f"{old_path}/", locale=instance.locale
            )
            for descendant in descendants:
                descendant.path = descendant.compute_path()
                descendant.save(update_fields=["path"])


@receiver(pre_save, sender=Page)
def store_old_path(sender, instance, **kwargs):
    """Store old path to compare after save."""
    if instance.pk:
        try:
            old_instance = Page.objects.get(pk=instance.pk)
            instance._old_path = old_instance.path
        except Page.DoesNotExist:
            instance._old_path = None


@receiver(post_save, sender=Page)
def update_asset_usage(sender, instance, created, **kwargs):
    """Update asset usage tracking when page is saved."""
    try:
        from apps.media.usage import update_usage_for_instance

        update_usage_for_instance(instance)
    except ImportError:
        # Media app not available
        pass


@receiver(post_delete, sender=Page)
def cleanup_asset_usage(sender, instance, **kwargs):
    """Clean up asset usage records when page is deleted."""
    try:
        from apps.media.usage import cleanup_usage_for_instance

        cleanup_usage_for_instance(instance)
    except ImportError:
        # Media app not available
        pass


@receiver(post_save, sender=Page)
def create_page_revision(sender, instance, created, **kwargs):
    """Create revision snapshots when pages are saved."""
    try:
        from django.conf import settings

        from .versioning import AuditEntry, PageRevision

        # Skip if this is being called during revision restoration
        if getattr(instance, "_skip_revision_creation", False):
            return

        # Get user from thread-local storage or request context
        user = getattr(instance, "_current_user", None)

        # Determine revision type
        is_published = bool(
            instance.status == "published"
            and instance.published_at
            and instance.published_at <= timezone.now()
        )

        # Always create revision for published snapshots
        # For drafts, check if we should create an autosave
        should_create = (
            is_published
            or created
            or (user and PageRevision.should_create_autosave(instance, user))
        )

        if should_create:
            revision = PageRevision.create_snapshot(
                page=instance,
                user=user,
                is_published=is_published,
                is_autosave=bool(not created and not is_published),
                comment=getattr(instance, "_revision_comment", ""),
            )

            # Store revision ID for API responses
            instance._revision_id = str(revision.id)

        # Create audit entry
        if user:
            action = "create" if created else "update"
            if is_published and hasattr(instance, "_was_published_now"):
                action = "publish"
            elif hasattr(instance, "_was_unpublished_now"):
                action = "unpublish"

            meta = {
                "revision_id": getattr(instance, "_revision_id", None),
                "status": instance.status,
                "locale": instance.locale.code if instance.locale else None,
                "path": instance.path,
            }

            AuditEntry.log(
                actor=user,
                action=action,
                obj=instance,
                meta=meta,
                request=getattr(instance, "_current_request", None),
            )

    except ImportError:
        # Versioning models not available
        pass


@receiver(pre_save, sender=Page)
def detect_publish_status_change(sender, instance, **kwargs):
    """Detect if page is being published or unpublished."""
    if instance.pk:
        try:
            old_instance = Page.objects.get(pk=instance.pk)

            # Check if status changed to/from published
            was_published = (
                old_instance.status == "published"
                and old_instance.published_at
                and old_instance.published_at <= timezone.now()
            )

            is_published = (
                instance.status == "published"
                and instance.published_at
                and instance.published_at <= timezone.now()
            )

            if not was_published and is_published:
                instance._was_published_now = True
            elif was_published and not is_published:
                instance._was_unpublished_now = True

        except Page.DoesNotExist:
            pass
