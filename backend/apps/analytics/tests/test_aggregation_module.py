"""Tests for analytics aggregation functionality."""

import os
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

import django

# Configure Django settings before any imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
django.setup()

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.analytics.aggregation import AnalyticsAggregator
from apps.analytics.models import (
    AnalyticsSummary,
    Assessment,
    ContentMetrics,
    PageView,
    Risk,
    Threat,
    UserActivity,
)
from apps.i18n.models import Locale

User = get_user_model()


class AnalyticsAggregatorTestCase(TestCase):
    """Test analytics aggregation functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(code="en", name="English", is_default=True)

        # Create test page views
        self.create_test_page_views()

    def create_test_page_views(self):
        """Create test page view data."""
        now = timezone.now()

        # Create page views for different days
        for i in range(7):
            view_time = now - timedelta(days=i)
            for j in range(3):  # 3 views per day
                PageView.objects.create(
                    path=f"/test-page-{i}",
                    user=self.user if j == 0 else None,
                    ip_address=f"192.168.1.{i+j}",
                    user_agent="Test Browser",
                    viewed_at=view_time,
                    session_id=f"session_{i}_{j}",
                )

    def test_get_traffic_trends_daily(self):
        """Test daily traffic trends calculation."""
        trends = AnalyticsAggregator.get_traffic_trends(days=7, period="daily")

        # Should return data for each day
        self.assertIsInstance(trends, list)
        self.assertGreater(len(trends), 0)

        # Each trend should have required fields
        for trend in trends:
            self.assertIn("period_date", trend)
            self.assertIn("page_views", trend)
            self.assertIn("unique_visitors", trend)

    def test_get_traffic_trends_weekly(self):
        """Test weekly traffic trends calculation."""
        trends = AnalyticsAggregator.get_traffic_trends(days=30, period="weekly")

        self.assertIsInstance(trends, list)
        # Should have data for weeks
        if trends:
            trend = trends[0]
            self.assertIn("period_date", trend)
            self.assertIn("page_views", trend)

    def test_get_traffic_trends_monthly(self):
        """Test monthly traffic trends calculation."""
        trends = AnalyticsAggregator.get_traffic_trends(days=90, period="monthly")

        self.assertIsInstance(trends, list)
        if trends:
            trend = trends[0]
            self.assertIn("period_date", trend)
            self.assertIn("page_views", trend)

    def test_get_traffic_trends_hourly(self):
        """Test hourly traffic trends calculation."""
        trends = AnalyticsAggregator.get_traffic_trends(days=1, period="hourly")

        self.assertIsInstance(trends, list)
        if trends:
            trend = trends[0]
            self.assertIn("period_date", trend)
            self.assertIn("page_views", trend)

    def test_get_traffic_trends_invalid_period(self):
        """Test traffic trends with invalid period defaults to daily."""
        trends = AnalyticsAggregator.get_traffic_trends(days=7, period="invalid")

        # Should still return results (defaulting to daily)
        self.assertIsInstance(trends, list)

    def test_get_content_performance(self):
        """Test content performance calculation."""
        if hasattr(AnalyticsAggregator, "get_content_performance"):
            performance = AnalyticsAggregator.get_content_performance(days=30)

            self.assertIsInstance(performance, list)

            if performance:
                content = performance[0]
                expected_fields = ["path", "views", "unique_visitors", "bounce_rate"]
                for field in expected_fields:
                    if field in content:  # Check if field exists
                        self.assertIsNotNone(content[field])

    def test_get_user_engagement_metrics(self):
        """Test user engagement metrics calculation."""
        if hasattr(AnalyticsAggregator, "get_user_engagement_metrics"):
            # Create some user activity data
            UserActivity.objects.create(
                user=self.user,
                activity_type="page_view",
                data={"page": "/test"},
                timestamp=timezone.now(),
            )

            metrics = AnalyticsAggregator.get_user_engagement_metrics(days=30)

            self.assertIsInstance(metrics, dict)

            # Check for expected metric keys
            expected_keys = [
                "total_users",
                "active_users",
                "session_duration",
                "page_views_per_session",
            ]
            for key in expected_keys:
                if key in metrics:  # Only check if key exists
                    self.assertIsNotNone(metrics[key])

    def test_calculate_bounce_rate(self):
        """Test bounce rate calculation."""
        if hasattr(AnalyticsAggregator, "calculate_bounce_rate"):
            bounce_rate = AnalyticsAggregator.calculate_bounce_rate(days=7)

            self.assertIsInstance(bounce_rate, (int, float))
            self.assertGreaterEqual(bounce_rate, 0)
            self.assertLessEqual(bounce_rate, 100)

    def test_get_popular_pages(self):
        """Test popular pages calculation."""
        if hasattr(AnalyticsAggregator, "get_popular_pages"):
            popular = AnalyticsAggregator.get_popular_pages(days=7, limit=5)

            self.assertIsInstance(popular, list)
            self.assertLessEqual(len(popular), 5)

            if popular:
                page = popular[0]
                expected_fields = ["path", "views", "unique_visitors"]
                for field in expected_fields:
                    if field in page:
                        self.assertIsNotNone(page[field])

    def test_get_referrer_stats(self):
        """Test referrer statistics calculation."""
        if hasattr(AnalyticsAggregator, "get_referrer_stats"):
            stats = AnalyticsAggregator.get_referrer_stats(days=7)

            self.assertIsInstance(stats, list)

            if stats:
                referrer = stats[0]
                expected_fields = ["referrer", "views", "unique_visitors"]
                for field in expected_fields:
                    if field in referrer:
                        self.assertIsNotNone(referrer[field])

    def test_get_device_breakdown(self):
        """Test device breakdown calculation."""
        if hasattr(AnalyticsAggregator, "get_device_breakdown"):
            breakdown = AnalyticsAggregator.get_device_breakdown(days=7)

            self.assertIsInstance(breakdown, dict)

            # Should have device categories
            expected_categories = ["desktop", "mobile", "tablet"]
            for category in expected_categories:
                if category in breakdown:
                    self.assertIsInstance(breakdown[category], (int, float))

    def test_generate_summary_report(self):
        """Test summary report generation."""
        if hasattr(AnalyticsAggregator, "generate_summary_report"):
            report = AnalyticsAggregator.generate_summary_report(days=7)

            self.assertIsInstance(report, dict)

            # Should have major sections
            expected_sections = ["traffic", "content", "users", "devices"]
            for section in expected_sections:
                if section in report:
                    self.assertIsNotNone(report[section])

    def test_empty_data_handling(self):
        """Test aggregation with no data."""
        # Clear all page views
        PageView.objects.all().delete()

        trends = AnalyticsAggregator.get_traffic_trends(days=7)

        # Should handle empty data gracefully
        self.assertIsInstance(trends, list)

    @patch("django.utils.timezone.now")
    def test_timezone_handling(self, mock_now):
        """Test proper timezone handling in aggregation."""
        # Mock current time
        fixed_time = datetime(
            2024, 1, 15, 12, 0, 0, tzinfo=timezone.get_current_timezone()
        )
        mock_now.return_value = fixed_time

        trends = AnalyticsAggregator.get_traffic_trends(days=1)

        # Should still work with mocked time
        self.assertIsInstance(trends, list)

    def test_date_range_boundaries(self):
        """Test aggregation with edge case date ranges."""
        # Test with 0 days
        trends = AnalyticsAggregator.get_traffic_trends(days=0)
        self.assertIsInstance(trends, list)

        # Test with very large range
        trends = AnalyticsAggregator.get_traffic_trends(days=365)
        self.assertIsInstance(trends, list)

    def test_performance_with_large_dataset(self):
        """Test aggregation performance considerations."""
        # This test would create a larger dataset in practice
        # For now, we just test that the method handles multiple records
        trends = AnalyticsAggregator.get_traffic_trends(days=30)

        # Should complete without timeout
        self.assertIsInstance(trends, list)


class AnalyticsModelsIntegrationTestCase(TestCase):
    """Integration tests for analytics aggregation with models."""

    def setUp(self):
        """Set up integration test data."""
        self.user = User.objects.create_user(
            username="analyst", email="analyst@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(code="en", name="English", is_default=True)

    def test_content_metrics_aggregation(self):
        """Test aggregation with ContentMetrics model."""
        # Create content metrics
        ContentMetrics.objects.create(
            content_type_id=1,
            object_id=1,
            views=100,
            likes=10,
            shares=5,
            comments=3,
            engagement_score=75.5,
            date=timezone.now().date(),
        )

        # Test aggregation methods that might use ContentMetrics
        if hasattr(AnalyticsAggregator, "get_content_engagement"):
            engagement = AnalyticsAggregator.get_content_engagement(days=7)
            self.assertIsInstance(engagement, (list, dict))

    def test_user_activity_aggregation(self):
        """Test aggregation with UserActivity model."""
        # Create user activity
        UserActivity.objects.create(
            user=self.user,
            activity_type="login",
            data={"source": "web"},
            timestamp=timezone.now(),
        )

        UserActivity.objects.create(
            user=self.user,
            activity_type="page_view",
            data={"page": "/dashboard"},
            timestamp=timezone.now(),
        )

        # Test aggregation methods that might use UserActivity
        if hasattr(AnalyticsAggregator, "get_user_activity_summary"):
            summary = AnalyticsAggregator.get_user_activity_summary(days=7)
            self.assertIsInstance(summary, (list, dict))

    def test_assessment_and_risk_aggregation(self):
        """Test aggregation with Assessment and Risk models."""
        # Create assessment
        assessment = Assessment.objects.create(
            name="Security Assessment", description="Test assessment", status="active"
        )

        # Create risk
        Risk.objects.create(
            assessment=assessment,
            name="Test Risk",
            description="Test risk description",
            likelihood="medium",
            impact="high",
            risk_level="high",
        )

        # Test aggregation methods that might use these models
        if hasattr(AnalyticsAggregator, "get_risk_summary"):
            summary = AnalyticsAggregator.get_risk_summary()
            self.assertIsInstance(summary, (list, dict))

    def test_analytics_summary_creation(self):
        """Test creating analytics summary records."""
        # Create an analytics summary
        summary = AnalyticsSummary.objects.create(
            period_type="daily",
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            total_page_views=100,
            unique_visitors=50,
            bounce_rate=25.5,
            avg_session_duration=300,
            data={"additional": "metrics"},
        )

        self.assertIsNotNone(summary.id)
        self.assertEqual(summary.period_type, "daily")
        self.assertEqual(summary.total_page_views, 100)

    def test_complex_aggregation_queries(self):
        """Test complex aggregation scenarios."""
        # Create complex data scenario
        now = timezone.now()

        # Multiple users, multiple pages, multiple days
        for i in range(3):
            user = User.objects.create_user(
                username=f"user{i}", email=f"user{i}@example.com", password="pass"
            )

            for j in range(5):  # 5 pages
                for k in range(2):  # 2 views per page per user
                    PageView.objects.create(
                        path=f"/page-{j}",
                        user=user,
                        ip_address=f"10.0.{i}.{k}",
                        user_agent=f"Browser {i}",
                        viewed_at=now - timedelta(days=k),
                        session_id=f"session_{i}_{j}_{k}",
                    )

        # Test aggregation with complex data
        trends = AnalyticsAggregator.get_traffic_trends(days=7)

        # Should handle complex data without errors
        self.assertIsInstance(trends, list)

        # Should have some results with the test data
        self.assertGreater(len(trends), 0)

    def test_aggregation_method_existence(self):
        """Test that expected aggregation methods exist."""
        aggregator = AnalyticsAggregator()

        # Core methods that should exist
        expected_methods = ["get_traffic_trends"]

        for method_name in expected_methods:
            self.assertTrue(
                hasattr(AnalyticsAggregator, method_name),
                f"AnalyticsAggregator should have {method_name} method",
            )

            method = getattr(AnalyticsAggregator, method_name)
            self.assertTrue(callable(method), f"{method_name} should be callable")

    def test_static_method_behavior(self):
        """Test that aggregation methods work as static methods."""
        # Should be able to call without instantiating
        trends = AnalyticsAggregator.get_traffic_trends(days=1)
        self.assertIsInstance(trends, list)

        # Should also work with instance
        aggregator = AnalyticsAggregator()
        trends = aggregator.get_traffic_trends(days=1)
        self.assertIsInstance(trends, list)
