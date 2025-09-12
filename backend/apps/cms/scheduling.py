from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

Scheduling models for the CMS.

This module provides scheduling functionality for pages and blog posts.

class ScheduledTask(models.Model):
    """Track all scheduled publishing tasks"""

    TASK_TYPES = [
        ("publish", _("Publish")),
        ("unpublish", _("Unpublish")),
    ]

    TASK_STATUS = [
        ("pending", _("Pending")),
        ("processing", _("Processing")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
        ("cancelled", _("Cancelled")),
    ]

    id: models.AutoField = models.AutoField(primary_key=True)
    content_type: models.ForeignKey = models.ForeignKey(
        ContentType, on_delete=models.CASCADE
    )
    object_id: models.PositiveIntegerField = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    task_type: models.CharField = models.CharField(
        max_length=10, choices=TASK_TYPES, db_index=True
    )
    scheduled_for: models.DateTimeField = models.DateTimeField(db_index=True)

    status: models.CharField = models.CharField(
        max_length=10, choices=TASK_STATUS, default="pending", db_index=True
    )

    # Execution tracking
    attempts: models.PositiveIntegerField = models.PositiveIntegerField(default=0)
    last_attempt_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    completed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)
    error_message: models.TextField = models.TextField(blank=True)

    # Metadata
    created_by: models.ForeignKey = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="scheduled_tasks",
    )
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
            models.Index(fields=["content_type", "object_id", "task_type"]),
            models.Index(fields=["status", "task_type", "-scheduled_for"]),
        ]
        ordering = ["scheduled_for"]
        verbose_name = _("Scheduled Task")
        verbose_name_plural = _("Scheduled Tasks")

    def __str__(self):
        return f"{self.get_task_type_display()} - {self.content_object} at {self.scheduled_for}"

    def clean(self):
        """Validate the scheduled task"""
        if self.status == "pending" and self.scheduled_for <= timezone.now():
            # Allow tasks in the past only if they're being processed
            if not self.pk:  # New task
                raise ValidationError(
                    {"scheduled_for": _("Scheduled time must be in the future")}
                )

    def can_cancel(self):
        """Check if this task can be cancelled"""
        return self.status in ["pending", "processing"]

    def cancel(self):
        """Cancel this scheduled task"""
        if not self.can_cancel():
            raise ValidationError(
                _("Only pending or processing tasks can be cancelled")
            )

        self.status = "cancelled"
        self.save(update_fields=["status", "updated_at"])

        # Clear scheduling fields on content object
        content = self.content_object
        if content and hasattr(content, "scheduled_publish_at"):
            if self.task_type == "publish":
                content.scheduled_publish_at = None
                if content.status == "scheduled":
                    content.status = "draft"
            elif self.task_type == "unpublish":
                content.scheduled_unpublish_at = None
            content.save()

    def execute(self):
        """Execute the scheduled task"""

        if self.status != "pending":
            raise ValidationError(_("Only pending tasks can be executed"))

        self.status = "processing"
        self.attempts += 1
        self.last_attempt_at = timezone.now()
        self.save()

        try:
            with transaction.atomic():
                content = self.content_object
                if not content:
                    raise ValueError(f"Content object not found for task {self.id}")

                now = timezone.now()

                if self.task_type == "publish":
                    content.status = "published"
                    content.published_at = now
                    content.scheduled_publish_at = None
                    content.save()

                elif self.task_type == "unpublish":
                    content.status = "draft"
                    content.scheduled_unpublish_at = None
                    content.save()

                self.status = "completed"
                self.completed_at = now
                self.save()

                return True

        except Exception as e:
            self.status = "failed" if self.attempts >= 3 else "pending"
            self.error_message = str(e)
            self.save()

            if self.attempts >= 3:
                # Max retries reached, mark as failed
                return False
            else:
                # Will retry
