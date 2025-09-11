# Analytics System

A comprehensive analytics API system for the Bedrock CMS backend that provides detailed insights into site traffic, user behavior, content performance, and security metrics.

## Features

### Traffic Analytics
- **Page Views**: Track individual page visits with detailed metadata
- **User Activities**: Monitor user actions and interactions
- **Session Tracking**: Analyze user sessions and engagement patterns
- **Device & Browser Analytics**: Understand visitor technology preferences

### Content Performance
- **Content Metrics**: Track performance of pages, blog posts, and other content
- **Engagement Metrics**: Monitor time on page, bounce rates, and user interactions
- **SEO Metrics**: Track search impressions, clicks, and rankings

### Security Analytics
- **Threat Tracking**: Monitor and manage security threats
- **Risk Management**: Assess and track security risks
- **Security Assessments**: Schedule and manage security audits
- **Security Scoring**: Calculate overall security health scores

### Dashboard & Reporting
- **Real-time Dashboard**: Live analytics dashboard with key metrics
- **Trend Analysis**: Historical data analysis and trend identification
- **Custom Reports**: Generate reports for specific date ranges and metrics
- **Data Export**: Export analytics data in various formats

## API Endpoints

### Core Analytics
- `GET /api/v1/analytics/page-views/` - List page view records
- `POST /api/v1/analytics/page-views/` - Create page view record
- `GET /api/v1/analytics/user-activities/` - List user activities
- `POST /api/v1/analytics/user-activities/` - Create user activity record
- `GET /api/v1/analytics/content-metrics/` - List content performance metrics

### Security Analytics
- `GET /api/v1/analytics/assessments/` - List security assessments
- `POST /api/v1/analytics/assessments/` - Create security assessment
- `GET /api/v1/analytics/risks/` - List security risks
- `POST /api/v1/analytics/risks/` - Create security risk
- `GET /api/v1/analytics/threats/` - List security threats
- `POST /api/v1/analytics/threats/` - Report security threat

### Dashboard APIs
- `GET /api/v1/analytics/api/traffic/` - Traffic analytics data
- `GET /api/v1/analytics/api/views/` - Page view analytics
- `GET /api/v1/analytics/api/dashboard/` - Dashboard summary statistics
- `GET /api/v1/analytics/api/risk-timeline/` - Risk timeline data
- `GET /api/v1/analytics/api/threat-stats/` - Threat statistics

### Summary & Reporting
- `GET /api/v1/analytics/summaries/` - Analytics summary data
- `GET /api/v1/analytics/api/export/` - Export analytics data

## Data Models

### PageView
Tracks individual page visits with comprehensive metadata including:
- User and session information
- Device and browser details
- Geographic data
- Performance metrics (load time, time on page)

### UserActivity
Records user actions and interactions:
- Action types (login, logout, page operations, etc.)
- Related content objects
- Context metadata
- Session tracking

### ContentMetrics
Aggregated content performance data:
- View counts and unique visitors
- Engagement metrics
- SEO performance
- Social sharing data

### Assessment, Risk, Threat
Security-focused models for managing:
- Security assessments and audits
- Risk identification and mitigation
- Threat detection and response

### AnalyticsSummary
Pre-aggregated summary data for:
- Daily, weekly, monthly overviews
- Performance dashboards
- Trend analysis

## Permissions

The analytics system uses role-based permissions:

- **Admin**: Full access to all analytics data and security information
- **Manager**: Access to traffic and content analytics, limited security data
- **Member**: Basic analytics access for their own content

## Background Tasks

Automated data processing using Celery:

### Daily Tasks
- `generate_daily_analytics_summary` - Generate daily summary statistics
- `generate_security_report` - Create daily security overview

### Periodic Maintenance
- `cleanup_old_page_views` - Remove old page view records (90 days)
- `cleanup_old_user_activities` - Remove old activity records (180 days)
- `calculate_content_performance_scores` - Update content performance metrics

### Real-time Aggregation
- `aggregate_hourly_traffic` - Process hourly traffic data
- `generate_weekly_analytics_summary` - Weekly summaries
- `generate_monthly_analytics_summary` - Monthly summaries

## Usage Examples

### Frontend Integration

The analytics system is designed to work with frontend components like:

- **TrafficViewsChart.tsx**: Traffic analytics visualization
- **AssessmentsTable.tsx**: Security assessments management
- **RiskTimeline.tsx**: Risk tracking over time
- **ThreatCards.tsx**: Threat monitoring dashboard

### Recording Page Views

```python
from apps.analytics.models import PageView
from apps.analytics.utils import get_analytics_context

# In your view
context = get_analytics_context(request)
PageView.objects.create(
    page=page,
    user=request.user if request.user.is_authenticated else None,
    url=request.build_absolute_uri(),
    title=page.title,
    session_id=context['session_key'],
    ip_address=context['ip_address'],
    user_agent=context['user_agent'],
    device_type=context['device_type'],
    browser=context['browser'],
    os=context['os'],
    country=context['country'],
    city=context['city'],
    referrer=context['referrer']
)
```

### Recording User Activities

```python
from apps.analytics.models import UserActivity
from django.contrib.contenttypes.models import ContentType

# Track user action
UserActivity.objects.create(
    user=request.user,
    action='page_create',
    description=f'Created page: {page.title}',
    content_type=ContentType.objects.get_for_model(page),
    object_id=page.id,
    ip_address=get_client_ip(request),
    user_agent=request.META.get('HTTP_USER_AGENT', ''),
    session_id=request.session.session_key or ''
)
```

### Querying Analytics Data

```python
from apps.analytics.aggregation import AnalyticsAggregator
from datetime import date, timedelta

# Get traffic trends
trends = AnalyticsAggregator.get_traffic_trends(days=30, period='daily')

# Get top content
top_content = AnalyticsAggregator.get_top_content(days=7, limit=10)

# Get security overview
security_data = AnalyticsAggregator.get_security_overview(days=30)

# Calculate bounce rate
bounce_rate = AnalyticsAggregator.calculate_bounce_rate(
    start_date=date.today() - timedelta(days=7),
    end_date=date.today()
)
```

## Configuration

Add to your Django settings:

```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    # ...
    'apps.analytics',
]

# Add Celery beat schedule for analytics tasks
from apps.analytics.tasks import ANALYTICS_CELERY_BEAT_SCHEDULE

CELERY_BEAT_SCHEDULE.update(ANALYTICS_CELERY_BEAT_SCHEDULE)
```

## Database Migrations

Run migrations to create the analytics tables:

```bash
python manage.py makemigrations analytics
python manage.py migrate
```

## Security Considerations

- IP addresses are stored for analytics but can be anonymized
- User agent strings are stored but contain no personal information
- Geographic data is limited to country/city level
- Sensitive URL parameters are automatically filtered
- Bot traffic can be filtered using user agent detection

## Performance

- Database indexes are optimized for common query patterns
- Old data is automatically cleaned up to manage storage
- Summary data is pre-aggregated for dashboard performance
- Background tasks handle heavy calculations

## Customization

The analytics system is designed to be extensible:

- Add new activity types in `UserActivity.ACTION_TYPES`
- Extend models with additional fields as needed
- Create custom aggregation functions in `aggregation.py`
- Add new API endpoints in `views.py`
- Customize permissions for your use case

## Troubleshooting

### Common Issues

1. **GeoIP not working**: Install GeoIP database or disable geo tracking
2. **High database usage**: Adjust cleanup task frequencies
3. **Slow dashboard**: Enable Redis caching for aggregated data
4. **Missing user agent data**: Check that requests include User-Agent header

### Performance Optimization

1. **Database Indexes**: Additional indexes can be added for custom queries
2. **Caching**: Implement Redis caching for frequently accessed data
3. **Archiving**: Archive old data to separate tables for long-term storage
4. **Sampling**: Implement sampling for high-traffic sites

This analytics system provides comprehensive insights while maintaining good performance and security practices.