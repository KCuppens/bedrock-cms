"""Celery tasks for analytics data processing and aggregation."""

import logging
from datetime import date, datetime, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from celery import shared_task

from .aggregation import AnalyticsAggregator
from .models import ContentMetrics, PageView, UserActivity

User = get_user_model()

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_analytics_summary(target_date=None):  # noqa: C901
    """Generate daily analytics summary for a specific date.

    Args:
        target_date: Date string in YYYY-MM-DD format, defaults to yesterday
    """

    if target_date is None:

        target_date = (timezone.now() - timedelta(days=1)).date()

    elif isinstance(target_date, str):

        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    try:

        summary = AnalyticsAggregator.generate_daily_summary(target_date)

        return {
            "success": True,
            "date": str(target_date),
            "summary_id": summary.id,
            "total_views": summary.total_views,
        }

    except Exception as e:

        return {"success": False, "error": str(e), "date": str(target_date)}


@shared_task
def generate_weekly_analytics_summary(week_start=None):  # noqa: C901
    """Generate weekly analytics summary.

    Args:
        week_start: Week start date string in YYYY-MM-DD format
    """

    if week_start is None:

        # Default to start of current week (Monday)

        today = timezone.now().date()

        week_start = today - timedelta(days=today.weekday())

    elif isinstance(week_start, str):

        week_start = datetime.strptime(week_start, "%Y-%m-%d").date()

    try:

        summary = AnalyticsAggregator.generate_weekly_summary(week_start)

        return {
            "success": True,
            "week_start": str(week_start),
            "summary_id": summary.id,
            "total_views": summary.total_views,
        }

    except Exception as e:

        return {"success": False, "error": str(e), "week_start": str(week_start)}


@shared_task
def generate_monthly_analytics_summary(month_start=None):  # noqa: C901
    """Generate monthly analytics summary.

    Args:
        month_start: Month start date string in YYYY-MM-DD format
    """

    if month_start is None:

        # Default to start of current month

        today = timezone.now().date()

        month_start = date(today.year, today.month, 1)

    elif isinstance(month_start, str):

        month_start = datetime.strptime(month_start, "%Y-%m-%d").date()

    try:

        summary = AnalyticsAggregator.generate_monthly_summary(month_start)

        return {
            "success": True,
            "month_start": str(month_start),
            "summary_id": summary.id,
            "total_views": summary.total_views,
        }

    except Exception as e:

        return {"success": False, "error": str(e), "month_start": str(month_start)}


@shared_task
def cleanup_old_page_views(days=90):  # noqa: C901
    """Clean up old page view records to manage database size.

    Args:
        days: Number of days to keep (default: 90)
    """
    from django.db import transaction

    cutoff_date = timezone.now() - timedelta(days=days)

    # Use bulk delete with batching to avoid memory issues
    batch_size = 10000
    total_deleted = 0

    with transaction.atomic():
        while True:
            # Get batch of old records
            old_views = PageView.objects.filter(viewed_at__lt=cutoff_date).values_list(
                "id", flat=True
            )[:batch_size]

            if not old_views:
                break

            # Delete batch
            batch_deleted = PageView.objects.filter(id__in=list(old_views)).delete()[0]

            total_deleted += batch_deleted

            if batch_deleted < batch_size:
                break

    logger.info(f"Cleaned up {total_deleted} old page views (older than {days} days)")

    return {
        "success": True,
        "deleted_count": total_deleted,
        "cutoff_date": cutoff_date.isoformat(),
    }


@shared_task
def cleanup_old_user_activities(days=180):  # noqa: C901
    """Clean up old user activity records.

    Args:
        days: Number of days to keep (default: 180)
    """
    from django.db import transaction

    cutoff_date = timezone.now() - timedelta(days=days)

    # Use bulk delete with batching to avoid memory issues
    batch_size = 10000
    total_deleted = 0

    with transaction.atomic():
        while True:
            # Get batch of old records
            old_activities = UserActivity.objects.filter(
                created_at__lt=cutoff_date
            ).values_list("id", flat=True)[:batch_size]

            if not old_activities:
                break

            # Delete batch
            batch_deleted = UserActivity.objects.filter(
                id__in=list(old_activities)
            ).delete()[0]

            total_deleted += batch_deleted

            if batch_deleted < batch_size:
                break

    logger.info(
        f"Cleaned up {total_deleted} old user activities (older than {days} days)"
    )

    return {
        "success": True,
        "deleted_count": total_deleted,
        "cutoff_date": cutoff_date.isoformat(),
    }


@shared_task
def calculate_content_performance_scores():  # noqa: C901
    """Calculate performance scores for all content items."""

    updated_count = 0

    # Get all content types that have metrics

    content_types = ContentMetrics.objects.values(
        "content_type", "object_id"
    ).distinct()

    for item in content_types:

        try:

            AnalyticsAggregator.calculate_content_performance_score(
                item["content_type"], item["object_id"]
            )

            # Here you could update a performance score field or create reports

            updated_count += 1

        except Exception as e:

            # Log error but continue processing

            logger.error(
                f"Failed to calculate performance score for {item['content_type']}:{item['object_id']}: {e}"
            )

    return {"success": True, "updated_count": updated_count}


@shared_task
def generate_security_report():  # noqa: C901
    """Generate daily security overview report."""

    try:

        security_data = AnalyticsAggregator.get_security_overview()

        # Here you could save the report or send notifications

        # For now, just return the data

        return {
            "success": True,
            "report_date": timezone.now().isoformat(),
            "threats": security_data["threats"],
            "risks": security_data["risks"],
            "assessments": security_data["assessments"],
            "security_score": security_data["overall_security_score"],
        }

    except Exception as e:

        return {"success": False, "error": str(e)}


@shared_task
def aggregate_hourly_traffic():  # noqa: C901
    """Aggregate hourly traffic data for the last 24 hours."""

    end_time = timezone.now()

    start_time = end_time - timedelta(hours=24)

    try:

        hourly_data = AnalyticsAggregator.get_traffic_trends(days=1, period="hourly")

        return {
            "success": True,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "hourly_data": list(hourly_data),
        }

    except Exception as e:

        return {"success": False, "error": str(e)}


@shared_task
def cleanup_analytics_comprehensive(
    page_views_days=90,
    user_activities_days=180,
    search_queries_days=30,
    content_metrics_days=365,
):  # noqa: C901
    """Comprehensive analytics cleanup task.

    Args:
        page_views_days: Days to keep page views (default: 90)
        user_activities_days: Days to keep user activities (default: 180)
        search_queries_days: Days to keep search queries (default: 30)
        content_metrics_days: Days to keep content metrics (default: 365)
    """
    from django.db import transaction

    results = {
        "page_views": 0,
        "user_activities": 0,
        "search_queries": 0,
        "content_metrics": 0,
        "errors": [],
    }

    # Clean up page views
    try:
        result = cleanup_old_page_views.apply(args=[page_views_days])
        if result.successful():
            results["page_views"] = result.result.get("deleted_count", 0)
        else:
            results["errors"].append(f"Page views cleanup failed: {result.result}")
    except Exception as e:
        results["errors"].append(f"Page views cleanup error: {str(e)}")

    # Clean up user activities
    try:
        result = cleanup_old_user_activities.apply(args=[user_activities_days])
        if result.successful():
            results["user_activities"] = result.result.get("deleted_count", 0)
        else:
            results["errors"].append(f"User activities cleanup failed: {result.result}")
    except Exception as e:
        results["errors"].append(f"User activities cleanup error: {str(e)}")

    # Clean up search queries
    try:
        from apps.search.models import SearchQuery as SearchQueryLog

        cutoff_date = timezone.now() - timedelta(days=search_queries_days)

        batch_size = 10000
        total_deleted = 0

        with transaction.atomic():
            while True:
                old_queries = SearchQueryLog.objects.filter(
                    created_at__lt=cutoff_date
                ).values_list("id", flat=True)[:batch_size]

                if not old_queries:
                    break

                batch_deleted = SearchQueryLog.objects.filter(
                    id__in=list(old_queries)
                ).delete()[0]

                total_deleted += batch_deleted

                if batch_deleted < batch_size:
                    break

        results["search_queries"] = total_deleted
        logger.info(
            f"Cleaned up {total_deleted} old search queries (older than {search_queries_days} days)"
        )

    except Exception as e:
        results["errors"].append(f"Search queries cleanup error: {str(e)}")

    # Clean up old content metrics
    try:
        cutoff_date = timezone.now() - timedelta(days=content_metrics_days)

        batch_size = 5000
        total_deleted = 0

        with transaction.atomic():
            while True:
                old_metrics = ContentMetrics.objects.filter(
                    date__lt=cutoff_date.date()
                ).values_list("id", flat=True)[:batch_size]

                if not old_metrics:
                    break

                batch_deleted = ContentMetrics.objects.filter(
                    id__in=list(old_metrics)
                ).delete()[0]

                total_deleted += batch_deleted

                if batch_deleted < batch_size:
                    break

        results["content_metrics"] = total_deleted
        logger.info(
            f"Cleaned up {total_deleted} old content metrics (older than {content_metrics_days} days)"
        )

    except Exception as e:
        results["errors"].append(f"Content metrics cleanup error: {str(e)}")

    # Calculate totals
    total_cleaned = sum(
        [
            results["page_views"],
            results["user_activities"],
            results["search_queries"],
            results["content_metrics"],
        ]
    )

    logger.info(
        f"Comprehensive analytics cleanup completed. Total records cleaned: {total_cleaned}"
    )

    return {
        "success": len(results["errors"]) == 0,
        "total_cleaned": total_cleaned,
        "breakdown": results,
        "timestamp": timezone.now().isoformat(),
    }


# Periodic task configuration for Celery Beat

ANALYTICS_CELERY_BEAT_SCHEDULE = {
    "generate-daily-summary": {
        # Imports that were malformed - commented out
        #         """"task": "apps.analytics.tasks.generate_daily_analytics_summary","""
        "schedule": 60.0 * 60.0 * 2,  # Every 2 hours
        "options": {"queue": "analytics"},
    },
    "generate-weekly-summary": {
        # Imports that were malformed - commented out
        #         """"task": "apps.analytics.tasks.generate_weekly_analytics_summary","""
        "schedule": 60.0 * 60.0 * 24,  # Daily
        "options": {"queue": "analytics"},
    },
    "generate-monthly-summary": {
        # Imports that were malformed - commented out
        #         """"task": "apps.analytics.tasks.generate_monthly_analytics_summary","""
        "schedule": 60.0 * 60.0 * 24,  # Daily
        "options": {"queue": "analytics"},
    },
    "cleanup-analytics-comprehensive": {
        "task": "apps.analytics.tasks.cleanup_analytics_comprehensive",
        "schedule": 60.0 * 60.0 * 24 * 7,  # Weekly
        "options": {"queue": "maintenance"},
    },
    "calculate-performance-scores": {
        # Imports that were malformed - commented out
        #         """"task": "apps.analytics.tasks.calculate_content_performance_scores","""
        "schedule": 60.0 * 60.0 * 12,  # Twice daily
        "options": {"queue": "analytics"},
    },
    "generate-security-report": {
        # Imports that were malformed - commented out
        #         """"task": "apps.analytics.tasks.generate_security_report","""
        "schedule": 60.0 * 60.0 * 24,  # Daily
        "options": {"queue": "security"},
    },
    "aggregate-hourly-traffic": {
        # Imports that were malformed - commented out
        #         """"task": "apps.analytics.tasks.aggregate_hourly_traffic","""
        "schedule": 60.0 * 60,  # Every hour
        "options": {"queue": "analytics"},
    },
}
