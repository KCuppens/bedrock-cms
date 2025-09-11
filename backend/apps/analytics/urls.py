from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PageViewViewSet,
    UserActivityViewSet,
    ContentMetricsViewSet,
    AssessmentViewSet,
    RiskViewSet,
    ThreatViewSet,
    AnalyticsSummaryViewSet,
    AnalyticsAPIViewSet,
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r"page-views", PageViewViewSet, basename="pageviews")
router.register(r"user-activities", UserActivityViewSet, basename="useractivities")
router.register(r"content-metrics", ContentMetricsViewSet, basename="contentmetrics")
router.register(r"assessments", AssessmentViewSet, basename="assessments")
router.register(r"risks", RiskViewSet, basename="risks")
router.register(r"threats", ThreatViewSet, basename="threats")
router.register(r"summaries", AnalyticsSummaryViewSet, basename="summaries")
router.register(r"api", AnalyticsAPIViewSet, basename="analytics-api")

app_name = "analytics"

urlpatterns = [
    # Include all router URLs
    path("", include(router.urls)),
    # Additional custom endpoints can be added here if needed
    # For example:
    # path('custom-report/', CustomReportView.as_view(), name='custom-report'),
]
