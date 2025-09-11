"""
Analytics aggregation functions for calculating metrics and summaries.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from django.db.models import Count, Avg, Sum, Q, F, Min, Max
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncHour
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from .models import (
    PageView,
    UserActivity,
    ContentMetrics,
    Assessment,
    Risk,
    Threat,
    AnalyticsSummary
)

User = get_user_model()


class AnalyticsAggregator:
    """Main aggregation class for analytics calculations"""
    
    @staticmethod
    def get_traffic_trends(
        days: int = 30,
        period: str = 'daily'
    ) -> List[Dict]:
        """
        Calculate traffic trends over a specified period.
        
        Args:
            days: Number of days to look back
            period: Aggregation period ('daily', 'weekly', 'monthly', 'hourly')
            
        Returns:
            List of dictionaries containing trend data
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Choose truncation function based on period
        trunc_functions = {
            'hourly': TruncHour,
            'daily': TruncDate,
            'weekly': TruncWeek,
            'monthly': TruncMonth
        }
        
        trunc_func = trunc_functions.get(period, TruncDate)
        
        # Aggregate page view data
        trends = PageView.objects.filter(
            viewed_at__gte=start_date
        ).annotate(
            period_date=trunc_func('viewed_at')
        ).values('period_date').annotate(
            total_views=Count('id'),
            unique_visitors=Count('session_id', distinct=True),
            unique_users=Count('user', distinct=True),
            avg_load_time=Avg('load_time'),
            avg_time_on_page=Avg('time_on_page')
        ).order_by('period_date')
        
        return list(trends)
    
    @staticmethod
    def calculate_bounce_rate(
        start_date: datetime,
        end_date: datetime,
        page_id: Optional[int] = None
    ) -> float:
        """
        Calculate bounce rate for a given period.
        
        Args:
            start_date: Start date for calculation
            end_date: End date for calculation
            page_id: Optional page ID to filter by
            
        Returns:
            Bounce rate as percentage
        """
        base_query = PageView.objects.filter(
            viewed_at__range=[start_date, end_date]
        )
        
        if page_id:
            base_query = base_query.filter(page_id=page_id)
        
        # Get all sessions
        total_sessions = base_query.values('session_id').distinct().count()
        
        if total_sessions == 0:
            return 0.0
        
        # Get sessions with only one page view (bounced sessions)
        single_page_sessions = base_query.values('session_id').annotate(
            page_count=Count('id')
        ).filter(page_count=1).count()
        
        return (single_page_sessions / total_sessions) * 100
    
    @staticmethod
    def get_top_content(
        days: int = 30,
        limit: int = 20,
        content_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get top performing content by views and engagement.
        
        Args:
            days: Number of days to look back
            limit: Maximum number of results to return
            content_type: Optional content type filter
            
        Returns:
            List of top performing content with metrics
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        query = PageView.objects.filter(
            viewed_at__date__range=[start_date, end_date],
            page__isnull=False
        )
        
        top_content = query.values(
            'page_id',
            'page__title',
            'url'
        ).annotate(
            total_views=Count('id'),
            unique_views=Count('session_id', distinct=True),
            avg_time_on_page=Avg('time_on_page'),
            avg_load_time=Avg('load_time')
        ).order_by('-total_views')[:limit]
        
        return list(top_content)
    
    @staticmethod
    def get_user_engagement_metrics(
        user_id: Optional[int] = None,
        days: int = 30
    ) -> Dict:
        """
        Calculate user engagement metrics.
        
        Args:
            user_id: Optional specific user ID
            days: Number of days to look back
            
        Returns:
            Dictionary containing engagement metrics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        base_query = UserActivity.objects.filter(
            created_at__range=[start_date, end_date]
        )
        
        if user_id:
            base_query = base_query.filter(user_id=user_id)
        
        # Calculate various engagement metrics
        metrics = {
            'total_activities': base_query.count(),
            'unique_users': base_query.values('user').distinct().count(),
            'activities_by_type': dict(
                base_query.values('action').annotate(
                    count=Count('id')
                ).values_list('action', 'count')
            ),
            'daily_active_users': base_query.filter(
                created_at__date=timezone.now().date()
            ).values('user').distinct().count(),
            'weekly_active_users': base_query.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).values('user').distinct().count(),
            'monthly_active_users': base_query.values('user').distinct().count()
        }
        
        return metrics
    
    @staticmethod
    def calculate_content_performance_score(
        content_type_id: int,
        object_id: int,
        days: int = 30
    ) -> Dict:
        """
        Calculate a comprehensive performance score for content.
        
        Args:
            content_type_id: ContentType ID
            object_id: Object ID
            days: Number of days to analyze
            
        Returns:
            Dictionary with performance metrics and score
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get content metrics
        try:
            metrics = ContentMetrics.objects.filter(
                content_type_id=content_type_id,
                object_id=object_id,
                date__range=[start_date, end_date]
            ).aggregate(
                total_views=Sum('views'),
                total_unique_views=Sum('unique_views'),
                avg_time_on_content=Avg('avg_time_on_content'),
                avg_bounce_rate=Avg('bounce_rate'),
                total_shares=Sum('shares'),
                total_comments=Sum('comments'),
                total_downloads=Sum('downloads')
            )
        except ContentMetrics.DoesNotExist:
            metrics = {
                'total_views': 0,
                'total_unique_views': 0,
                'avg_time_on_content': 0,
                'avg_bounce_rate': 100,
                'total_shares': 0,
                'total_comments': 0,
                'total_downloads': 0
            }
        
        # Calculate performance score (0-100)
        # This is a weighted score based on various metrics
        views_score = min((metrics['total_views'] or 0) / 100, 1) * 30
        engagement_score = min((metrics['avg_time_on_content'] or 0) / 300, 1) * 20
        bounce_score = (100 - (metrics['avg_bounce_rate'] or 100)) / 100 * 15
        social_score = min((metrics['total_shares'] or 0) / 10, 1) * 15
        interaction_score = min((metrics['total_comments'] or 0) / 5, 1) * 10
        download_score = min((metrics['total_downloads'] or 0) / 20, 1) * 10
        
        performance_score = (
            views_score + engagement_score + bounce_score + 
            social_score + interaction_score + download_score
        )
        
        return {
            **metrics,
            'performance_score': round(performance_score, 2),
            'score_breakdown': {
                'views': round(views_score, 2),
                'engagement': round(engagement_score, 2),
                'bounce_rate': round(bounce_score, 2),
                'social': round(social_score, 2),
                'interactions': round(interaction_score, 2),
                'downloads': round(download_score, 2)
            }
        }
    
    @staticmethod
    def get_security_overview(days: int = 30) -> Dict:
        """
        Get security overview including threats, risks, and assessments.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with security metrics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Threat analysis
        threats = Threat.objects.filter(detected_at__gte=start_date)
        threat_stats = {
            'total_threats': threats.count(),
            'active_threats': threats.filter(
                status__in=['detected', 'investigating', 'contained']
            ).count(),
            'resolved_threats': threats.filter(status='resolved').count(),
            'by_severity': dict(
                threats.values('severity').annotate(
                    count=Count('id')
                ).values_list('severity', 'count')
            ),
            'by_type': dict(
                threats.values('threat_type').annotate(
                    count=Count('id')
                ).values_list('threat_type', 'count')
            )
        }
        
        # Risk analysis
        risks = Risk.objects.filter(identified_at__gte=start_date)
        risk_stats = {
            'total_risks': risks.count(),
            'open_risks': risks.filter(
                status__in=['identified', 'assessed']
            ).count(),
            'mitigated_risks': risks.filter(status='mitigated').count(),
            'avg_risk_score': risks.aggregate(
                avg_score=Avg('risk_score')
            )['avg_score'] or 0,
            'by_category': dict(
                risks.values('category').annotate(
                    count=Count('id')
                ).values_list('category', 'count')
            ),
            'by_severity': dict(
                risks.values('severity').annotate(
                    count=Count('id')
                ).values_list('severity', 'count')
            )
        }
        
        # Assessment analysis
        assessments = Assessment.objects.filter(created_at__gte=start_date)
        assessment_stats = {
            'total_assessments': assessments.count(),
            'completed_assessments': assessments.filter(
                status='completed'
            ).count(),
            'pending_assessments': assessments.filter(
                status__in=['scheduled', 'in_progress']
            ).count(),
            'avg_score': assessments.filter(
                score__isnull=False
            ).aggregate(avg_score=Avg('score'))['avg_score'] or 0,
            'by_type': dict(
                assessments.values('assessment_type').annotate(
                    count=Count('id')
                ).values_list('assessment_type', 'count')
            )
        }
        
        return {
            'threats': threat_stats,
            'risks': risk_stats,
            'assessments': assessment_stats,
            'overall_security_score': AnalyticsAggregator._calculate_security_score(
                threat_stats, risk_stats, assessment_stats
            )
        }
    
    @staticmethod
    def _calculate_security_score(
        threat_stats: Dict,
        risk_stats: Dict,
        assessment_stats: Dict
    ) -> float:
        """
        Calculate an overall security score based on various metrics.
        
        Args:
            threat_stats: Threat statistics
            risk_stats: Risk statistics  
            assessment_stats: Assessment statistics
            
        Returns:
            Security score (0-100)
        """
        # Base score
        score = 100.0
        
        # Deduct points for active threats
        active_threats = threat_stats.get('active_threats', 0)
        score -= min(active_threats * 5, 30)
        
        # Deduct points for open risks
        open_risks = risk_stats.get('open_risks', 0)
        score -= min(open_risks * 3, 25)
        
        # Deduct points for high/critical severity issues
        high_severity_count = 0
        for severity in ['high', 'critical', 'very_high']:
            high_severity_count += threat_stats.get('by_severity', {}).get(severity, 0)
            high_severity_count += risk_stats.get('by_severity', {}).get(severity, 0)
        
        score -= min(high_severity_count * 8, 35)
        
        # Bonus for recent assessments
        recent_assessments = assessment_stats.get('completed_assessments', 0)
        score += min(recent_assessments * 2, 10)
        
        return max(score, 0)
    
    @staticmethod
    def generate_daily_summary(target_date: date) -> AnalyticsSummary:
        """
        Generate or update daily analytics summary.
        
        Args:
            target_date: Date to generate summary for
            
        Returns:
            AnalyticsSummary instance
        """
        # Get or create summary
        summary, created = AnalyticsSummary.objects.get_or_create(
            date=target_date,
            period_type='daily',
            defaults={}
        )
        
        # Calculate traffic metrics
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())
        
        page_views = PageView.objects.filter(
            viewed_at__range=[day_start, day_end]
        )
        
        summary.total_views = page_views.count()
        summary.unique_visitors = page_views.values('session_id').distinct().count()
        summary.returning_visitors = page_views.filter(
            user__isnull=False
        ).values('user').distinct().count()
        
        # Calculate average session duration and bounce rate
        if summary.total_views > 0:
            summary.avg_session_duration = page_views.aggregate(
                avg_duration=Avg('time_on_page')
            )['avg_duration'] or 0
            
            summary.bounce_rate = AnalyticsAggregator.calculate_bounce_rate(
                day_start, day_end
            )
        
        # User activity metrics
        activities = UserActivity.objects.filter(
            created_at__range=[day_start, day_end]
        )
        
        summary.new_users = User.objects.filter(
            date_joined__date=target_date
        ).count()
        
        summary.active_users = activities.values('user').distinct().count()
        summary.user_actions = activities.count()
        
        # Content metrics
        summary.pages_published = activities.filter(
            action='page_publish'
        ).count()
        
        summary.files_uploaded = activities.filter(
            action='file_upload'
        ).count()
        
        summary.content_updates = activities.filter(
            action='page_update'
        ).count()
        
        # Security metrics
        summary.threats_detected = Threat.objects.filter(
            detected_at__date=target_date
        ).count()
        
        summary.risks_identified = Risk.objects.filter(
            identified_at__date=target_date
        ).count()
        
        summary.assessments_completed = Assessment.objects.filter(
            completed_at__date=target_date
        ).count()
        
        # Performance metrics
        summary.avg_load_time = page_views.aggregate(
            avg_load_time=Avg('load_time')
        )['avg_load_time'] or 0
        
        # Uptime would be calculated from monitoring data
        summary.uptime_percentage = 99.9  # Placeholder
        
        summary.save()
        return summary
    
    @staticmethod
    def generate_weekly_summary(week_start: date) -> AnalyticsSummary:
        """Generate weekly analytics summary"""
        week_end = week_start + timedelta(days=6)
        
        summary, created = AnalyticsSummary.objects.get_or_create(
            date=week_start,
            period_type='weekly',
            defaults={}
        )
        
        # Aggregate daily summaries for the week
        daily_summaries = AnalyticsSummary.objects.filter(
            date__range=[week_start, week_end],
            period_type='daily'
        )
        
        if daily_summaries.exists():
            summary.total_views = daily_summaries.aggregate(
                total=Sum('total_views')
            )['total'] or 0
            
            summary.unique_visitors = daily_summaries.aggregate(
                total=Sum('unique_visitors')
            )['total'] or 0
            
            # Calculate averages for other metrics
            summary.avg_session_duration = daily_summaries.aggregate(
                avg=Avg('avg_session_duration')
            )['avg'] or 0
            
            summary.bounce_rate = daily_summaries.aggregate(
                avg=Avg('bounce_rate')
            )['avg'] or 0
            
            # Sum user metrics
            summary.new_users = daily_summaries.aggregate(
                total=Sum('new_users')
            )['total'] or 0
            
            summary.active_users = daily_summaries.aggregate(
                avg=Avg('active_users')
            )['avg'] or 0
            
            # Sum other metrics
            for field in [
                'user_actions', 'pages_published', 'files_uploaded',
                'content_updates', 'threats_detected', 'risks_identified',
                'assessments_completed'
            ]:
                setattr(summary, field, daily_summaries.aggregate(
                    total=Sum(field)
                )['total'] or 0)
            
            # Average performance metrics
            summary.avg_load_time = daily_summaries.aggregate(
                avg=Avg('avg_load_time')
            )['avg'] or 0
            
            summary.uptime_percentage = daily_summaries.aggregate(
                avg=Avg('uptime_percentage')
            )['avg'] or 100
        
        summary.save()
        return summary
    
    @staticmethod
    def generate_monthly_summary(month_start: date) -> AnalyticsSummary:
        """Generate monthly analytics summary"""
        # Calculate month end
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
        
        summary, created = AnalyticsSummary.objects.get_or_create(
            date=month_start,
            period_type='monthly',
            defaults={}
        )
        
        # Aggregate daily summaries for the month
        daily_summaries = AnalyticsSummary.objects.filter(
            date__range=[month_start, month_end],
            period_type='daily'
        )
        
        if daily_summaries.exists():
            # Similar aggregation logic as weekly but for monthly period
            summary.total_views = daily_summaries.aggregate(
                total=Sum('total_views')
            )['total'] or 0
            
            summary.unique_visitors = daily_summaries.aggregate(
                total=Sum('unique_visitors')
            )['total'] or 0
            
            # Calculate other metrics...
            # (Similar pattern as weekly summary)
        
        summary.save()
        return summary