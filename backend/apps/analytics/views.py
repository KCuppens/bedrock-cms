from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.utils import timezone

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .models import (
    AnalyticsSummary,
    Assessment,
    ContentMetrics,
    PageView,
    Risk,
    Threat,
    UserActivity,
)
from .serializers import (

    AnalyticsSummarySerializer,
    AssessmentCreateSerializer,
    AssessmentSerializer,
    ContentMetricsSerializer,
    DashboardStatsSerializer,
    PageViewCreateSerializer,
    PageViewSerializer,
    RiskSerializer,
    RiskTimelineSerializer,
    ThreatCreateSerializer,
    ThreatSerializer,
    ThreatStatsSerializer,
    TopContentSerializer,
    TrafficStatsSerializer,
    UserActivityCreateSerializer,
    UserActivitySerializer,
)

User = get_user_model()

class AnalyticsPermission(permissions.BasePermission):
    """Custom permission for analytics endpoints"""

    def has_permission(self, request, view):  # noqa: C901
        if not request.user.is_authenticated:
            return False

        # Allow read access to managers and admins
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_manager() or request.user.is_admin()

        # Allow write access only to admins
        return request.user.is_admin()

@extend_schema_view(
    list=extend_schema(
        summary="List page views",
        description="Retrieve a list of page view records with filtering options.",
        parameters=[
            OpenApiParameter(
                "date_from", type=str, description="Start date (YYYY-MM-DD)"
            ),
            OpenApiParameter("date_to", type=str, description="End date (YYYY-MM-DD)"),
            OpenApiParameter("page", type=int, description="Page ID to filter by"),
            OpenApiParameter("user", type=int, description="User ID to filter by"),
        ],
    ),
    create=extend_schema(
        summary="Create page view record",
        description="Record a new page view for analytics tracking.",
    ),
)
class PageViewViewSet(viewsets.ModelViewSet):
    """ViewSet for PageView analytics"""

    queryset = PageView.objects.all()
    permission_classes = [AnalyticsPermission]
    throttle_classes = [UserRateThrottle]

    def get_serializer_class(self):  # noqa: C901
        if self.action == "create":
            return PageViewCreateSerializer
        return PageViewSerializer

    def get_queryset(self):  # noqa: C901
        queryset = PageView.objects.select_related("page", "user")

        # Date filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(viewed_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(viewed_at__date__lte=date_to)

        # Additional filters
        page_id = self.request.query_params.get("page")
        if page_id:
            queryset = queryset.filter(page_id=page_id)

        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

@extend_schema_view(
    list=extend_schema(
        summary="List user activities",
        description="Retrieve a list of user activity records with filtering options.",
        parameters=[
            OpenApiParameter(
                "action", type=str, description="Action type to filter by"
            ),
            OpenApiParameter("user", type=int, description="User ID to filter by"),
            OpenApiParameter(
                "date_from", type=str, description="Start date (YYYY-MM-DD)"
            ),
            OpenApiParameter("date_to", type=str, description="End date (YYYY-MM-DD)"),
        ],
    ),
    create=extend_schema(
        summary="Create user activity record",
        description="Record a new user activity for analytics tracking.",
    ),
)
class UserActivityViewSet(viewsets.ModelViewSet):
    """ViewSet for UserActivity analytics"""

    queryset = UserActivity.objects.all()
    permission_classes = [AnalyticsPermission]
    throttle_classes = [UserRateThrottle]

    def get_serializer_class(self):  # noqa: C901
        if self.action == "create":
            return UserActivityCreateSerializer
        return UserActivitySerializer

    def get_queryset(self):  # noqa: C901
        queryset = UserActivity.objects.select_related("user", "content_type")

        # Action filtering
        action = self.request.query_params.get("action")
        if action:
            queryset = queryset.filter(action=action)

        # User filtering
        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Date filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

@extend_schema_view(
    list=extend_schema(
        summary="List content metrics",
        description="Retrieve content performance metrics with filtering options.",
        parameters=[
            OpenApiParameter(
                "date_from", type=str, description="Start date (YYYY-MM-DD)"
            ),
            OpenApiParameter("date_to", type=str, description="End date (YYYY-MM-DD)"),
            OpenApiParameter(
                "content_category",
                type=str,
                description="Content category to filter by",
            ),
        ],
    )
)
class ContentMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ContentMetrics analytics"""

    queryset = ContentMetrics.objects.all()
    serializer_class = ContentMetricsSerializer
    permission_classes = [AnalyticsPermission]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):  # noqa: C901
        queryset = ContentMetrics.objects.select_related("content_type")

        # Date filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        # Category filtering
        category = self.request.query_params.get("content_category")
        if category:
            queryset = queryset.filter(content_category=category)

        return queryset

@extend_schema_view(
    list=extend_schema(
        summary="List assessments",
        description="Retrieve security and compliance assessments.",
        parameters=[
            OpenApiParameter(
                "assessment_type", type=str, description="Assessment type to filter by"
            ),
            OpenApiParameter("status", type=str, description="Status to filter by"),
            OpenApiParameter(
                "assigned_to", type=int, description="Assigned user ID to filter by"
            ),
        ],
    ),
    create=extend_schema(
        summary="Create assessment",
        description="Create a new security or compliance assessment.",
    ),
)
class AssessmentViewSet(viewsets.ModelViewSet):
    """ViewSet for Assessment management"""

    queryset = Assessment.objects.all()
    permission_classes = [AnalyticsPermission]
    throttle_classes = [UserRateThrottle]

    def get_serializer_class(self):  # noqa: C901
        if self.action == "create":
            return AssessmentCreateSerializer
        return AssessmentSerializer

    def get_queryset(self):  # noqa: C901
        queryset = Assessment.objects.select_related("assigned_to", "created_by")

        # Type filtering
        assessment_type = self.request.query_params.get("assessment_type")
        if assessment_type:
            queryset = queryset.filter(assessment_type=assessment_type)

        # Status filtering
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Assignment filtering
        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        return queryset

@extend_schema_view(
    list=extend_schema(
        summary="List risks",
        description="Retrieve risk management records.",
        parameters=[
            OpenApiParameter(
                "category", type=str, description="Risk category to filter by"
            ),
            OpenApiParameter("status", type=str, description="Status to filter by"),
            OpenApiParameter(
                "severity", type=str, description="Severity level to filter by"
            ),
        ],
    )
)
class RiskViewSet(viewsets.ModelViewSet):
    """ViewSet for Risk management"""

    queryset = Risk.objects.all()
    serializer_class = RiskSerializer
    permission_classes = [AnalyticsPermission]
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):  # noqa: C901
        queryset = Risk.objects.select_related("owner", "assigned_to", "assessment")

        # Category filtering
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        # Status filtering
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Severity filtering
        severity = self.request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity)

        return queryset

@extend_schema_view(
    list=extend_schema(
        summary="List threats",
        description="Retrieve security threat records.",
        parameters=[
            OpenApiParameter(
                "threat_type", type=str, description="Threat type to filter by"
            ),
            OpenApiParameter("status", type=str, description="Status to filter by"),
            OpenApiParameter(
                "severity", type=str, description="Severity level to filter by"
            ),
        ],
    ),
    create=extend_schema(
        summary="Create threat record", description="Report a new security threat."
    ),
)
class ThreatViewSet(viewsets.ModelViewSet):
    """ViewSet for Threat management"""

    queryset = Threat.objects.all()
    permission_classes = [AnalyticsPermission]
    throttle_classes = [UserRateThrottle]

    def get_serializer_class(self):  # noqa: C901
        if self.action == "create":
            return ThreatCreateSerializer
        return ThreatSerializer

    def get_queryset(self):  # noqa: C901
        queryset = Threat.objects.select_related("assigned_to", "reported_by")

        # Type filtering
        threat_type = self.request.query_params.get("threat_type")
        if threat_type:
            queryset = queryset.filter(threat_type=threat_type)

        # Status filtering
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Severity filtering
        severity = self.request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(severity=severity)

        return queryset

@extend_schema_view(
    list=extend_schema(
        summary="List analytics summaries",
        description="Retrieve daily, weekly, or monthly analytics summaries.",
    )
)
class AnalyticsSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AnalyticsSummary data"""

    queryset = AnalyticsSummary.objects.all()
    serializer_class = AnalyticsSummarySerializer
    permission_classes = [AnalyticsPermission]
    throttle_classes = [UserRateThrottle]

# Custom analytics API views

class AnalyticsAPIViewSet(viewsets.GenericViewSet):
    """Custom analytics endpoints for dashboard and reporting"""

    permission_classes = [AnalyticsPermission]
    throttle_classes = [UserRateThrottle]

    @extend_schema(
        summary="Get traffic analytics",
        description="Retrieve traffic analytics data for dashboard charts.",
        parameters=[
            OpenApiParameter(
                "days", type=int, description="Number of days to include (default: 30)"
            ),
            OpenApiParameter(
                "period",
                type=str,
                description="Grouping period: daily, weekly, monthly",
            ),
        ],
        responses=TrafficStatsSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="traffic")
    def traffic_analytics(self, request):  # noqa: C901
        """Get traffic analytics data"""
        days = int(request.query_params.get("days", 30))
        period = request.query_params.get("period", "daily")

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Choose truncation function based on period
        if period == "weekly":
            trunc_func = TruncWeek
        elif period == "monthly":
            trunc_func = TruncMonth
        else:
            trunc_func = TruncDate

        # Aggregate page view data
        queryset = (
            PageView.objects.filter(viewed_at__date__range=[start_date, end_date])
            .annotate(period_date=trunc_func("viewed_at"))
            .values("period_date")
            .annotate(
                views=Count("id"),
                unique_visitors=Count("session_id", distinct=True),
                avg_session_duration=Avg("time_on_page"),
            )
            .order_by("period_date")
        )

        # Calculate bounce rate for each period
        data = []
        for item in queryset:
            # Get sessions with only one page view (bounced sessions)
            bounced_sessions = PageView.objects.filter(
                viewed_at__date=item["period_date"],
                session_id__in=PageView.objects.filter(
                    viewed_at__date=item["period_date"]
                )
                .values("session_id")
                .annotate(page_count=Count("id"))
                .filter(page_count=1)
                .values_list("session_id", flat=True),
            ).count()

            total_sessions = item["unique_visitors"]
            bounce_rate = (
                (bounced_sessions / total_sessions * 100) if total_sessions > 0 else 0
            )

            data.append(
                {
                    "date": item["period_date"],
                    "views": item["views"],
                    "unique_visitors": item["unique_visitors"],
                    "bounce_rate": round(bounce_rate, 2),
                    "avg_session_duration": item["avg_session_duration"] or 0,
                }
            )

        serializer = TrafficStatsSerializer(data, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get page view analytics",
        description="Retrieve detailed page view analytics.",
        parameters=[
            OpenApiParameter(
                "days", type=int, description="Number of days to include (default: 30)"
            ),
            OpenApiParameter(
                "limit", type=int, description="Limit results (default: 20)"
            ),
        ],
        responses=TopContentSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="views")
    def page_views_analytics(self, request):  # noqa: C901
        """Get page view analytics"""
        days = int(request.query_params.get("days", 30))
        limit = int(request.query_params.get("limit", 20))

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Get top performing content
        top_pages = (
            PageView.objects.filter(
                viewed_at__date__range=[start_date, end_date], page__isnull=False
            )
            .values("page__title", "url")
            .annotate(
                views=Count("id"),
                unique_views=Count("session_id", distinct=True),
                avg_time_on_page=Avg("time_on_page"),
            )
            .order_by("-views")[:limit]
        )

        data = []
        for page in top_pages:
            data.append(
                {
                    "title": page["page__title"],
                    "url": page["url"],
                    "views": page["views"],
                    "unique_views": page["unique_views"],
                    "avg_time_on_page": page["avg_time_on_page"] or 0,
                }
            )

        serializer = TopContentSerializer(data, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get dashboard summary",
        description="Retrieve summary statistics for the main dashboard.",
        responses=DashboardStatsSerializer,
    )
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard_summary(self, request):  # noqa: C901
        """Get dashboard summary statistics"""
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        # Today's stats
        today_views = PageView.objects.filter(viewed_at__date=today).count()
        today_visitors = (
            PageView.objects.filter(viewed_at__date=today)
            .values("session_id")
            .distinct()
            .count()
        )

        # Security stats
        active_threats = Threat.objects.filter(
            status__in=["detected", "investigating", "contained"]
        ).count()

        open_risks = Risk.objects.filter(status__in=["identified", "assessed"]).count()

        pending_assessments = Assessment.objects.filter(
            status__in=["scheduled", "in_progress"]
        ).count()

        # Performance stats
        avg_load_time = (
            PageView.objects.filter(
                viewed_at__date__gte=thirty_days_ago, load_time__isnull=False
            ).aggregate(avg_load_time=Avg("load_time"))["avg_load_time"]
            or 0
        )

        # Get trend data (last 7 days)
        trend_start = today - timedelta(days=7)
        daily_views = []
        daily_visitors = []
        daily_threats = []

        for i in range(7):
            date = trend_start + timedelta(days=i)
            views = PageView.objects.filter(viewed_at__date=date).count()
            visitors = (
                PageView.objects.filter(viewed_at__date=date)
                .values("session_id")
                .distinct()
                .count()
            )
            threats = Threat.objects.filter(detected_at__date=date).count()

            daily_views.append(views)
            daily_visitors.append(visitors)
            daily_threats.append(threats)

        data = {
            "today_views": today_views,
            "today_visitors": today_visitors,
            "active_threats": active_threats,
            "open_risks": open_risks,
            "pending_assessments": pending_assessments,
            "avg_load_time": int(avg_load_time),
            "uptime_percentage": 99.9,  # This would come from monitoring system
            "views_trend": daily_views,
            "visitors_trend": daily_visitors,
            "threat_trend": daily_threats,
        }

        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)

    @extend_schema(
        summary="Get risk timeline",
        description="Retrieve risk timeline data for dashboard visualization.",
        parameters=[
            OpenApiParameter(
                "days", type=int, description="Number of days to include (default: 30)"
            ),
        ],
        responses=RiskTimelineSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="risk-timeline")
    def risk_timeline(self, request):  # noqa: C901
        """Get risk timeline data"""
        days = int(request.query_params.get("days", 30))

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Aggregate risk data by date
        timeline_data = []

        for i in range(days + 1):
            date = start_date + timedelta(days=i)

            risks_identified = Risk.objects.filter(identified_at__date=date).count()

            risks_mitigated = Risk.objects.filter(
                status="mitigated", last_reviewed__date=date
            ).count()

            avg_risk_score = (
                Risk.objects.filter(
                    identified_at__date__lte=date, status__in=["identified", "assessed"]
                ).aggregate(avg_score=Avg("risk_score"))["avg_score"]
                or 0
            )

            timeline_data.append(
                {
                    "date": date,
                    "risks_identified": risks_identified,
                    "risks_mitigated": risks_mitigated,
                    "risk_score_avg": round(avg_risk_score, 2),
                }
            )

        serializer = RiskTimelineSerializer(timeline_data, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Get threat statistics",
        description="Retrieve threat statistics and trends.",
        parameters=[
            OpenApiParameter(
                "days", type=int, description="Number of days to include (default: 30)"
            ),
        ],
        responses=ThreatStatsSerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="threat-stats")
    def threat_statistics(self, request):  # noqa: C901
        """Get threat statistics"""
        days = int(request.query_params.get("days", 30))

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Get threat statistics by type
        threat_stats = (
            Threat.objects.filter(detected_at__date__range=[start_date, end_date])
            .values("threat_type")
            .annotate(count=Count("id"), severity_breakdown=Count("severity"))
            .order_by("-count")
        )

        data = []
        for stat in threat_stats:
            # Get severity breakdown for this threat type
            severity_breakdown = (
                Threat.objects.filter(
                    threat_type=stat["threat_type"],
                    detected_at__date__range=[start_date, end_date],
                )
                .values("severity")
                .annotate(count=Count("id"))
            )

            severity_dict = {
                item["severity"]: item["count"] for item in severity_breakdown
            }

            # Get daily trend for last 7 days
            trend_start = end_date - timedelta(days=7)
            trend = []
            for i in range(7):
                date = trend_start + timedelta(days=i)
                count = Threat.objects.filter(
                    threat_type=stat["threat_type"], detected_at__date=date
                ).count()
                trend.append(count)

            data.append(
                {
                    "threat_type": stat["threat_type"],
                    "count": stat["count"],
                    "severity_breakdown": severity_dict,
                    "trend": trend,
                }
            )

        serializer = ThreatStatsSerializer(data, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Export analytics data",
        description="Export analytics data in various formats.",
        parameters=[
            OpenApiParameter(
                "format", type=str, description="Export format: csv, json"
            ),
            OpenApiParameter(
                "type",
                type=str,
                description="Data type: traffic, threats, risks, assessments",
            ),
            OpenApiParameter("days", type=int, description="Number of days to include"),
        ],
    )
    @action(detail=False, methods=["get"], url_path="export")
    def export_data(self, request):  # noqa: C901
        """Export analytics data"""
        # This would implement data export functionality
        # For now, return a placeholder response
        return Response(
            {
                "message": "Export functionality would be implemented here",
                "available_formats": ["csv", "json", "pdf"],
                "available_types": ["traffic", "threats", "risks", "assessments"],
            }
        )
