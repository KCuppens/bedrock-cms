"""
Celery tasks for analytics data processing and aggregation.
"""

from datetime import date, datetime, timedelta
from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Avg, Sum
from django.contrib.auth import get_user_model

from .models import PageView, UserActivity, AnalyticsSummary
from .aggregation import AnalyticsAggregator

User = get_user_model()


@shared_task
def generate_daily_analytics_summary(target_date=None):
    """
    Generate daily analytics summary for a specific date.
    
    Args:
        target_date: Date string in YYYY-MM-DD format, defaults to yesterday
    """
    if target_date is None:
        target_date = (timezone.now() - timedelta(days=1)).date()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
    
    try:
        summary = AnalyticsAggregator.generate_daily_summary(target_date)
        return {
            'success': True,
            'date': str(target_date),
            'summary_id': summary.id,
            'total_views': summary.total_views
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'date': str(target_date)
        }


@shared_task
def generate_weekly_analytics_summary(week_start=None):
    """
    Generate weekly analytics summary.
    
    Args:
        week_start: Week start date string in YYYY-MM-DD format
    """
    if week_start is None:
        # Default to start of current week (Monday)
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
    elif isinstance(week_start, str):
        week_start = datetime.strptime(week_start, '%Y-%m-%d').date()
    
    try:
        summary = AnalyticsAggregator.generate_weekly_summary(week_start)
        return {
            'success': True,
            'week_start': str(week_start),
            'summary_id': summary.id,
            'total_views': summary.total_views
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'week_start': str(week_start)
        }


@shared_task
def generate_monthly_analytics_summary(month_start=None):
    """
    Generate monthly analytics summary.
    
    Args:
        month_start: Month start date string in YYYY-MM-DD format
    """
    if month_start is None:
        # Default to start of current month
        today = timezone.now().date()
        month_start = date(today.year, today.month, 1)
    elif isinstance(month_start, str):
        month_start = datetime.strptime(month_start, '%Y-%m-%d').date()
    
    try:
        summary = AnalyticsAggregator.generate_monthly_summary(month_start)
        return {
            'success': True,
            'month_start': str(month_start),
            'summary_id': summary.id,
            'total_views': summary.total_views
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'month_start': str(month_start)
        }


@shared_task
def cleanup_old_page_views(days=90):
    """
    Clean up old page view records to manage database size.
    
    Args:
        days: Number of days to keep (default: 90)
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    deleted_count = PageView.objects.filter(
        viewed_at__lt=cutoff_date
    ).delete()[0]
    
    return {
        'success': True,
        'deleted_count': deleted_count,
        'cutoff_date': cutoff_date.isoformat()
    }


@shared_task
def cleanup_old_user_activities(days=180):
    """
    Clean up old user activity records.
    
    Args:
        days: Number of days to keep (default: 180)
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    deleted_count = UserActivity.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    return {
        'success': True,
        'deleted_count': deleted_count,
        'cutoff_date': cutoff_date.isoformat()
    }


@shared_task
def calculate_content_performance_scores():
    """
    Calculate performance scores for all content items.
    """
    from django.contrib.contenttypes.models import ContentType
    from .models import ContentMetrics
    
    updated_count = 0
    
    # Get all content types that have metrics
    content_types = ContentMetrics.objects.values(
        'content_type', 'object_id'
    ).distinct()
    
    for item in content_types:
        try:
            score_data = AnalyticsAggregator.calculate_content_performance_score(
                item['content_type'], item['object_id']
            )
            # Here you could update a performance score field or create reports
            updated_count += 1
        except Exception as e:
            # Log error but continue processing
            continue
    
    return {
        'success': True,
        'updated_count': updated_count
    }


@shared_task
def generate_security_report():
    """
    Generate daily security overview report.
    """
    try:
        security_data = AnalyticsAggregator.get_security_overview()
        
        # Here you could save the report or send notifications
        # For now, just return the data
        return {
            'success': True,
            'report_date': timezone.now().isoformat(),
            'threats': security_data['threats'],
            'risks': security_data['risks'],
            'assessments': security_data['assessments'],
            'security_score': security_data['overall_security_score']
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def aggregate_hourly_traffic():
    """
    Aggregate hourly traffic data for the last 24 hours.
    """
    end_time = timezone.now()
    start_time = end_time - timedelta(hours=24)
    
    try:
        hourly_data = AnalyticsAggregator.get_traffic_trends(
            days=1,
            period='hourly'
        )
        
        return {
            'success': True,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'hourly_data': list(hourly_data)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


# Periodic task configuration for Celery Beat
ANALYTICS_CELERY_BEAT_SCHEDULE = {
    'generate-daily-summary': {
        'task': 'apps.analytics.tasks.generate_daily_analytics_summary',
        'schedule': 60.0 * 60.0 * 2,  # Every 2 hours
        'options': {'queue': 'analytics'}
    },
    'generate-weekly-summary': {
        'task': 'apps.analytics.tasks.generate_weekly_analytics_summary',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'analytics'}
    },
    'generate-monthly-summary': {
        'task': 'apps.analytics.tasks.generate_monthly_analytics_summary',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'analytics'}
    },
    'cleanup-old-page-views': {
        'task': 'apps.analytics.tasks.cleanup_old_page_views',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'maintenance'}
    },
    'cleanup-old-activities': {
        'task': 'apps.analytics.tasks.cleanup_old_user_activities',
        'schedule': 60.0 * 60.0 * 24 * 7,  # Weekly
        'options': {'queue': 'maintenance'}
    },
    'calculate-performance-scores': {
        'task': 'apps.analytics.tasks.calculate_content_performance_scores',
        'schedule': 60.0 * 60.0 * 12,  # Twice daily
        'options': {'queue': 'analytics'}
    },
    'generate-security-report': {
        'task': 'apps.analytics.tasks.generate_security_report',
        'schedule': 60.0 * 60.0 * 24,  # Daily
        'options': {'queue': 'security'}
    },
    'aggregate-hourly-traffic': {
        'task': 'apps.analytics.tasks.aggregate_hourly_traffic',
        'schedule': 60.0 * 60,  # Every hour
        'options': {'queue': 'analytics'}
    }
}