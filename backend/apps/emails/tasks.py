import logging

from django.conf import settings

from celery import shared_task

from .models import EmailMessageLog
        from .services import EmailService
        from datetime import timedelta
        from django.utils import timezone
        from django.db import transaction
        from .models import EmailMessageLog, EmailTemplate
        from .services import EmailService
        from datetime import timedelta
        from django.db import transaction
        from django.db.models import F, Q
        from django.utils import timezone
        from apps.core.enums import EmailStatus

logger = logging.getLogger(__name__)


@shared_task(name="apps.emails.tasks.send_email_task", bind=True)
def send_email_task(self, email_log_id: int):  # noqa: C901
    """
    Celery task to send email asynchronously

    Args:
        email_log_id: ID of EmailMessageLog to send

    Returns:
        dict: Task result with success status and details
    """
    try:

        # Get email log
        email_log = EmailMessageLog.objects.get(id=email_log_id)

        # Send email
        success = EmailService._send_email_now(email_log)

        if success:
            logger.info("Email task completed successfully for %s", email_log.to_email)
            return {
                "success": True,
                "email_log_id": email_log_id,
                "to_email": email_log.to_email,
                "subject": email_log.subject,
            }
        else:
            logger.error("Email task failed for %s", email_log.to_email)
            return {
                "success": False,
                "email_log_id": email_log_id,
                "to_email": email_log.to_email,
                "error": email_log.error_message,
            }

    except EmailMessageLog.DoesNotExist:
        error_msg = f"EmailMessageLog with id {email_log_id} not found"
        logger.error(error_msg)
        return {"success": False, "error": error_msg, "email_log_id": email_log_id}

    except Exception as e:
        error_msg = f"Unexpected error in email task: {str(e)}"
        logger.error(error_msg)

        # Try to mark email as failed if we have the log
        try:
            email_log = EmailMessageLog.objects.get(id=email_log_id)
            email_log.mark_as_failed(error_msg)
        except EmailMessageLog.DoesNotExist:
            pass

        # Retry the task up to 3 times with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2**self.request.retries), max_retries=3)


@shared_task(name="apps.emails.tasks.cleanup_old_email_logs")
def cleanup_old_email_logs(days_to_keep: int = 30):  # noqa: C901
    """
    Celery task to clean up old email logs

    Args:
        days_to_keep: Number of days to keep email logs (default: 30)

    Returns:
        dict: Task result with cleanup details
    """
    try:


        cutoff_date = timezone.now() - timedelta(days=days_to_keep)

        # Delete old email logs
        deleted_count, _ = EmailMessageLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        logger.info("Cleaned up %s old email logs", deleted_count)

        return {
            "success": True,
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
            "days_kept": days_to_keep,
        }

    except Exception as e:
        error_msg = f"Failed to cleanup old email logs: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


@shared_task(name="apps.emails.tasks.send_bulk_email_task")
def send_bulk_email_task(
    template_key: str, recipient_emails: list[str], context: dict | None = None
):
    """
    Celery task to send bulk emails with batch processing

    Args:
        template_key: Email template key
        recipient_emails: List of recipient email addresses
        context: Template context data

    Returns:
        dict: Task result with bulk send details
    """
    try:


        # Get template once and cache it
        template = EmailTemplate.get_template(template_key, "en")
        if not template:
            raise ValueError(f"Email template '{template_key}' not found")

        # Pre-render template content once if context is the same for all
        rendered_content = template.render_all(context or {})

        sent_count = 0
        failed_count = 0
        failed_emails = []
        batch_size = 50  # Process in batches

        # Process emails in batches for better performance
        for i in range(0, len(recipient_emails), batch_size):
            batch = recipient_emails[i : i + batch_size]
            email_logs = []

            # Create all log entries in a single transaction
            with transaction.atomic():
                for email in batch:
                    try:
                        email_log = EmailMessageLog(
                            template=template,
                            template_key=template_key,
                            to_email=email,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            subject=rendered_content["subject"],
                            html_content=rendered_content["html_content"],
                            text_content=rendered_content["text_content"],
                            context_data=context or {},
                        )
                        email_logs.append(email_log)
                    except Exception as e:
                        failed_count += 1
                        failed_emails.append({"email": email, "error": str(e)})
                        logger.error(
                            "Failed to prepare bulk email for %s: {str(e)}", email
                        )

                # Bulk create all email logs
                if email_logs:
                    EmailMessageLog.objects.bulk_create(email_logs)

            # Send emails in this batch
            for email_log in email_logs:
                try:
                    EmailService._send_email_now(email_log)
                    sent_count += 1
                except Exception as e:
                    failed_count += 1
                    failed_emails.append({"email": email_log.to_email, "error": str(e)})
                    logger.error(
                        "Failed to send bulk email to %s: {str(e)}", email_log.to_email
                    )

        logger.info(
            f"Bulk email task completed: {sent_count} sent, {failed_count} failed"
        )

        return {
            "success": True,
            "sent_count": sent_count,
            "failed_count": failed_count,
            "failed_emails": failed_emails,
            "template_key": template_key,
            "total_recipients": len(recipient_emails),
        }

    except Exception as e:
        error_msg = f"Bulk email task failed: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg,
            "template_key": template_key,
            "total_recipients": len(recipient_emails) if recipient_emails else 0,
        }


@shared_task(name="apps.emails.tasks.retry_failed_emails")
def retry_failed_emails(max_retries: int = 3):  # noqa: C901
    """
    Celery task to retry failed emails with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        dict: Task result with retry details
    """
    try:



        # Get failed emails from the last 24 hours that haven't exceeded retry limit
        cutoff_time = timezone.now() - timedelta(hours=24)

        # Use select_for_update to prevent concurrent retries
        with transaction.atomic():
            failed_emails = (
                EmailMessageLog.objects.select_for_update()
                .filter(
                    Q(status=EmailStatus.FAILED)
                    & Q(created_at__gte=cutoff_time)
                    & Q(
                        retry_count__lt=max_retries
                    )  # Assuming retry_count field exists
                )
                .select_related("template")[:50]
            )  # Process fewer at a time for better performance

            email_ids = list(failed_emails.values_list("id", flat=True))

            # Bulk update to mark as retrying
            EmailMessageLog.objects.filter(id__in=email_ids).update(
                status=EmailStatus.PENDING,
                error_message="",
                retry_count=F("retry_count") + 1,
            )

        retried_count = 0
        tasks = []

        # Schedule retries with exponential backoff
        for idx, email_id in enumerate(email_ids):
            try:
                # Calculate backoff delay based on retry count
                delay = min(60 * (2**idx), 3600)  # Max 1 hour delay

                # Schedule task with delay
                task = send_email_task.apply_async(
                    args=[email_id],
                    countdown=delay,
                    queue="high_priority",  # Use high priority queue for retries
                )
                tasks.append((email_id, task.id))
                retried_count += 1

            except Exception:
                logger.error(
                    "Failed to schedule retry for email %s: {str(e)}", email_id
                )

        # Bulk update celery task IDs
        if tasks:
            for email_id, task_id in tasks:
                EmailMessageLog.objects.filter(id=email_id).update(
                    celery_task_id=task_id
                )

        logger.info("Scheduled %s failed emails for retry", retried_count)

        return {
            "success": True,
            "retried_count": retried_count,
            "total_failed": len(email_ids),
        }

    except Exception as e:
        error_msg = f"Failed to retry failed emails: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
