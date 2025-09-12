from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.blog.models import BlogPost

from ..models import Page
from ..scheduling import ScheduledTask

"""
Scheduling service for CMS content.

This module provides services for scheduling content publishing and unpublishing.
"""


class SchedulingService:
    """Service for managing content scheduling."""

    @staticmethod
    def schedule_publish(
        content_object, publish_at, unpublish_at=None, user=None
    ) -> tuple[ScheduledTask, ScheduledTask | None]:
        """
        Schedule content for publishing.



        Args:

            content_object: The Page or BlogPost to schedule

            publish_at: DateTime when to publish

            unpublish_at: Optional DateTime when to unpublish

            user: The user creating the schedule



        Returns:

            Tuple of (publish_task, unpublish_task or None)



        Raises:

            ValidationError: If scheduling parameters are invalid
        """
        # Validate

        if publish_at <= timezone.now():

            raise ValidationError("Publish time must be in the future")

        if unpublish_at and unpublish_at <= publish_at:

            raise ValidationError("Unpublish time must be after publish time")

        with transaction.atomic():

            # Cancel any existing pending scheduling tasks

            SchedulingService.cancel_scheduling(content_object, skip_status_update=True)

            # Update content status and scheduling fields

            content_object.status = "scheduled"

            content_object.scheduled_publish_at = publish_at

            content_object.scheduled_unpublish_at = unpublish_at

            content_object.save()

            # Get content type

            content_type = ContentType.objects.get_for_model(content_object)

            # Create scheduled task for publishing

            publish_task = ScheduledTask.objects.create(
                content_type=content_type,
                object_id=content_object.id,
                task_type="publish",
                scheduled_for=publish_at,
                created_by=user,
            )

            # Create scheduled task for unpublishing if needed

            unpublish_task = None

            if unpublish_at:

                unpublish_task = ScheduledTask.objects.create(
                    content_type=content_type,
                    object_id=content_object.id,
                    task_type="unpublish",
                    scheduled_for=unpublish_at,
                    created_by=user,
                )

            return publish_task, unpublish_task

    @staticmethod
    def schedule_unpublish(content_object, unpublish_at, user=None) -> ScheduledTask:
        """
        Schedule content for unpublishing (content must be already published).



        Args:

            content_object: The Page or BlogPost to schedule unpublishing

            unpublish_at: DateTime when to unpublish

            user: The user creating the schedule



        Returns:

            The created ScheduledTask



        Raises:

            ValidationError: If content is not published or time is invalid
        """
        if content_object.status != "published":

            raise ValidationError(
                "Can only schedule unpublishing for published content"
            )

        if unpublish_at <= timezone.now():

            raise ValidationError("Unpublish time must be in the future")

        with transaction.atomic():

            # Cancel any existing unpublish tasks

            content_type = ContentType.objects.get_for_model(content_object)

            ScheduledTask.objects.filter(
                content_type=content_type,
                object_id=content_object.id,
                task_type="unpublish",
                status="pending",
            ).update(status="cancelled")

            # Update content

            content_object.scheduled_unpublish_at = unpublish_at

            content_object.save()

            # Create scheduled task

            unpublish_task = ScheduledTask.objects.create(
                content_type=content_type,
                object_id=content_object.id,
                task_type="unpublish",
                scheduled_for=unpublish_at,
                created_by=user,
            )

            return unpublish_task

    @staticmethod
    def cancel_scheduling(content_object, skip_status_update=False):
        """
        Cancel all scheduled tasks for content.



        Args:

            content_object: The Page or BlogPost

            skip_status_update: If True, don't update content status
        """
        content_type = ContentType.objects.get_for_model(content_object)

        with transaction.atomic():

            # Cancel pending tasks

            ScheduledTask.objects.filter(
                content_type=content_type, object_id=content_object.id, status="pending"
            ).update(status="cancelled")

            # Clear scheduling fields

            content_object.scheduled_publish_at = None

            content_object.scheduled_unpublish_at = None

            # Update status if scheduled (unless skipped)

            if not skip_status_update and content_object.status == "scheduled":

                content_object.status = "draft"

            content_object.save()

    @staticmethod
    def get_scheduled_tasks(
        content_type=None, status="pending", from_date=None, to_date=None
    ):
        """
        Get scheduled tasks with filters.



        Args:

            content_type: Filter by content type (Page or BlogPost)

            status: Filter by task status

            from_date: Filter tasks scheduled after this date

            to_date: Filter tasks scheduled before this date



        Returns:

            QuerySet of ScheduledTask objects
        """
        queryset = ScheduledTask.objects.all()

        if content_type:

            if isinstance(content_type, str):

                # Convert string to ContentType

                if content_type.lower() == "page":

                    content_type = ContentType.objects.get_for_model(Page)

                elif content_type.lower() in ["blogpost", "blog"]:

                    content_type = ContentType.objects.get_for_model(BlogPost)

            queryset = queryset.filter(content_type=content_type)

        if status:

            queryset = queryset.filter(status=status)

        if from_date:

            queryset = queryset.filter(scheduled_for__gte=from_date)

        if to_date:

            queryset = queryset.filter(scheduled_for__lte=to_date)

        return queryset.select_related("content_type", "created_by")

    @staticmethod
    def reschedule_task(task, new_scheduled_for, user=None):
        """
        Reschedule an existing task to a new time.



        Args:

            task: The ScheduledTask to reschedule

            new_scheduled_for: New DateTime for the task

            user: The user making the change



        Raises:

            ValidationError: If task cannot be rescheduled or time is invalid
        """
        if task.status != "pending":

            raise ValidationError("Can only reschedule pending tasks")

        if new_scheduled_for <= timezone.now():

            raise ValidationError("New scheduled time must be in the future")

        with transaction.atomic():

            # Update task

            task.scheduled_for = new_scheduled_for

            task.save()

            # Update content object

            content = task.content_object

            if content:

                if task.task_type == "publish":

                    content.scheduled_publish_at = new_scheduled_for

                elif task.task_type == "unpublish":

                    content.scheduled_unpublish_at = new_scheduled_for

                content.save()
