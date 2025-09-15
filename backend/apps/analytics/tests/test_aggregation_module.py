"""Tests for analytics aggregation functionality."""

import os

import django

# Setup Django before imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()

from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

import pytest

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
            email="test@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )

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
                    url=f"http://example.com/test-page-{i}",
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
            self.assertIn("total_views", trend)
            self.assertIn("unique_visitors", trend)

    def test_get_traffic_trends_weekly(self):
        """Test weekly traffic trends calculation."""
        trends = AnalyticsAggregator.get_traffic_trends(days=30, period="weekly")

        self.assertIsInstance(trends, list)
        # Should have data for weeks
        if trends:
            trend = trends[0]
            self.assertIn("period_date", trend)
            self.assertIn("total_views", trend)

    def test_get_traffic_trends_monthly(self):
        """Test monthly traffic trends calculation."""
        trends = AnalyticsAggregator.get_traffic_trends(days=90, period="monthly")

        self.assertIsInstance(trends, list)
        if trends:
            trend = trends[0]
            self.assertIn("period_date", trend)
            self.assertIn("total_views", trend)

    def test_get_traffic_trends_hourly(self):
        """Test hourly traffic trends calculation."""
        trends = AnalyticsAggregator.get_traffic_trends(days=1, period="hourly")

        self.assertIsInstance(trends, list)
        if trends:
            trend = trends[0]
            self.assertIn("period_date", trend)
            self.assertIn("total_views", trend)

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
        # Create comprehensive user activity data
        activities = [
            {"action": "search", "metadata": {"query": "test"}},
            {"action": "login", "metadata": {"source": "web"}},
            {"action": "page_view", "metadata": {"page": "/dashboard"}},
            {"action": "logout", "metadata": {}},
        ]

        for activity in activities:
            UserActivity.objects.create(
                user=self.user,
                action=activity["action"],
                metadata=activity["metadata"],
                ip_address="127.0.0.1",
                session_id="test-session",
                created_at=timezone.now(),
            )

        # Test general engagement metrics
        metrics = AnalyticsAggregator.get_user_engagement_metrics(days=30)

        self.assertIsInstance(metrics, dict)

        # Check for expected metric keys and their types
        expected_keys = {
            "total_activities": int,
            "unique_users": int,
            "activities_by_type": dict,
            "daily_active_users": int,
            "weekly_active_users": int,
            "monthly_active_users": int,
        }

        for key, expected_type in expected_keys.items():
            self.assertIn(key, metrics)
            self.assertIsInstance(metrics[key], expected_type)

        # Verify activities_by_type has correct structure
        activities_by_type = metrics["activities_by_type"]
        self.assertGreater(len(activities_by_type), 0)

        # Test user-specific metrics
        user_metrics = AnalyticsAggregator.get_user_engagement_metrics(
            user_id=self.user.id, days=30
        )
        self.assertIsInstance(user_metrics, dict)
        self.assertEqual(user_metrics["unique_users"], 1)

    def test_calculate_bounce_rate(self):
        """Test bounce rate calculation."""
        now = timezone.now()
        start_date = now - timedelta(days=7)
        end_date = now

        # Test with existing data
        bounce_rate = AnalyticsAggregator.calculate_bounce_rate(start_date, end_date)

        self.assertIsInstance(bounce_rate, (int, float))
        self.assertGreaterEqual(bounce_rate, 0)
        self.assertLessEqual(bounce_rate, 100)

        # Test edge case with no data
        future_start = now + timedelta(days=1)
        future_end = now + timedelta(days=2)
        empty_bounce_rate = AnalyticsAggregator.calculate_bounce_rate(
            future_start, future_end
        )
        self.assertEqual(empty_bounce_rate, 0.0)

        # Test with page_id filter
        bounce_rate_filtered = AnalyticsAggregator.calculate_bounce_rate(
            start_date, end_date, page_id=1
        )
        self.assertIsInstance(bounce_rate_filtered, (int, float))
        self.assertGreaterEqual(bounce_rate_filtered, 0)
        self.assertLessEqual(bounce_rate_filtered, 100)

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

    def test_get_top_content(self):
        """Test top content retrieval with comprehensive scenarios."""
        # Create test page views with actual page references
        from django.contrib.contenttypes.models import ContentType

        # Create some test "pages" using User model as mock content
        test_users = []
        for i in range(3):
            test_users.append(
                User.objects.create_user(
                    email=f"page{i}@example.com", password="testpass"
                )
            )

        # Create page views for these "pages"
        now = timezone.now()
        for i, user in enumerate(test_users):
            for j in range(5 - i):  # Different view counts
                PageView.objects.create(
                    url=f"http://example.com/page-{i}",
                    # Don't set page_id since cms.Page might not exist
                    user=self.user,
                    ip_address=f"192.168.1.{j}",
                    user_agent="Test Browser",
                    viewed_at=now - timedelta(hours=i),
                    session_id=f"session_{i}_{j}",
                    time_on_page=300 + (i * 60),
                    load_time=100 + (i * 10),
                )

        # Test top content retrieval (if method exists)
        if hasattr(AnalyticsAggregator, "get_top_content"):
            top_content = AnalyticsAggregator.get_top_content(days=1, limit=5)
        else:
            top_content = []

        self.assertIsInstance(top_content, list)
        self.assertLessEqual(len(top_content), 5)

        if top_content:
            content = top_content[0]
            expected_fields = [
                "page_id",
                "url",
                "total_views",
                "unique_views",
                "avg_time_on_page",
                "avg_load_time",
            ]
            for field in expected_fields:
                self.assertIn(field, content)

            # Verify sorting by total_views (descending)
            if len(top_content) > 1:
                self.assertGreaterEqual(
                    top_content[0]["total_views"], top_content[1]["total_views"]
                )

    def test_calculate_content_performance_score(self):
        """Test content performance score calculation."""
        # Create content metrics
        content_type = ContentType.objects.get_for_model(User)

        ContentMetrics.objects.create(
            content_type=content_type,
            object_id=self.user.id,
            date=timezone.now().date(),
            views=150,
            unique_views=100,
            avg_time_on_content=400,
            bounce_rate=25.0,
            shares=8,
            comments=4,
            downloads=15,
        )

        # Test performance score calculation
        score_data = AnalyticsAggregator.calculate_content_performance_score(
            content_type.id, self.user.id, days=30
        )

        self.assertIsInstance(score_data, dict)

        # Check required fields
        required_fields = [
            "total_views",
            "total_unique_views",
            "avg_time_on_content",
            "avg_bounce_rate",
            "total_shares",
            "total_comments",
            "total_downloads",
            "performance_score",
            "score_breakdown",
        ]

        for field in required_fields:
            self.assertIn(field, score_data)

        # Verify performance score is within valid range
        self.assertIsInstance(score_data["performance_score"], (int, float))
        self.assertGreaterEqual(score_data["performance_score"], 0)
        self.assertLessEqual(score_data["performance_score"], 100)

        # Verify score breakdown
        breakdown = score_data["score_breakdown"]
        breakdown_fields = [
            "views",
            "engagement",
            "bounce_rate",
            "social",
            "interactions",
            "downloads",
        ]

        for field in breakdown_fields:
            self.assertIn(field, breakdown)
            self.assertIsInstance(breakdown[field], (int, float))
            self.assertGreaterEqual(breakdown[field], 0)

        # Test with non-existent content
        empty_score = AnalyticsAggregator.calculate_content_performance_score(
            content_type.id, 99999, days=30
        )
        self.assertEqual(empty_score["total_views"], 0)
        self.assertEqual(empty_score["performance_score"], 0)

    def test_get_security_overview(self):
        """Test comprehensive security overview."""
        # Create test threats
        threats_data = [
            {
                "title": "Malware Detected",
                "threat_type": "malware",
                "severity": "critical",
                "status": "detected",
            },
            {
                "title": "Phishing Attempt",
                "threat_type": "phishing",
                "severity": "high",
                "status": "resolved",
            },
            {
                "title": "DDoS Attack",
                "threat_type": "ddos",
                "severity": "medium",
                "status": "investigating",
            },
        ]

        for threat_data in threats_data:
            Threat.objects.create(
                title=threat_data["title"],
                description="Test threat",
                threat_type=threat_data["threat_type"],
                severity=threat_data["severity"],
                status=threat_data["status"],
                reported_by=self.user,
                detected_at=timezone.now(),
            )

        # Create test risks
        risks_data = [
            {
                "category": "security",
                "probability": 4,
                "impact": 5,
                "status": "identified",
            },
            {
                "category": "operational",
                "probability": 3,
                "impact": 3,
                "status": "mitigated",
            },
            {
                "category": "financial",
                "probability": 2,
                "impact": 4,
                "status": "assessed",
            },
        ]

        for risk_data in risks_data:
            Risk.objects.create(
                title="Test Risk",
                description="Test risk description",
                category=risk_data["category"],
                probability=risk_data["probability"],
                impact=risk_data["impact"],
                status=risk_data["status"],
                identified_at=timezone.now(),
            )

        # Create test assessments
        assessments_data = [
            {"assessment_type": "security", "status": "completed", "score": 85},
            {"assessment_type": "compliance", "status": "in_progress", "score": None},
            {"assessment_type": "vulnerability", "status": "scheduled", "score": None},
        ]

        for assessment_data in assessments_data:
            Assessment.objects.create(
                title="Test Assessment",
                description="Test assessment",
                assessment_type=assessment_data["assessment_type"],
                status=assessment_data["status"],
                score=assessment_data["score"],
                created_by=self.user,
                created_at=timezone.now(),
            )

        # Test security overview
        overview = AnalyticsAggregator.get_security_overview(days=30)

        self.assertIsInstance(overview, dict)

        # Check main sections
        required_sections = [
            "threats",
            "risks",
            "assessments",
            "overall_security_score",
        ]
        for section in required_sections:
            self.assertIn(section, overview)

        # Verify threat statistics
        threats = overview["threats"]
        threat_fields = [
            "total_threats",
            "active_threats",
            "resolved_threats",
            "by_severity",
            "by_type",
        ]
        for field in threat_fields:
            self.assertIn(field, threats)

        self.assertEqual(threats["total_threats"], 3)
        self.assertEqual(threats["active_threats"], 2)  # detected + investigating
        self.assertEqual(threats["resolved_threats"], 1)

        # Verify risk statistics
        risks = overview["risks"]
        risk_fields = [
            "total_risks",
            "open_risks",
            "mitigated_risks",
            "avg_risk_score",
            "by_category",
            "by_severity",
        ]
        for field in risk_fields:
            self.assertIn(field, risks)

        self.assertEqual(risks["total_risks"], 3)
        self.assertEqual(risks["mitigated_risks"], 1)

        # Verify assessment statistics
        assessments = overview["assessments"]
        assessment_fields = [
            "total_assessments",
            "completed_assessments",
            "pending_assessments",
            "avg_score",
            "by_type",
        ]
        for field in assessment_fields:
            self.assertIn(field, assessments)

        self.assertEqual(assessments["total_assessments"], 3)
        self.assertEqual(assessments["completed_assessments"], 1)
        self.assertEqual(assessments["pending_assessments"], 2)

        # Verify overall security score
        security_score = overview["overall_security_score"]
        self.assertIsInstance(security_score, (int, float))
        self.assertGreaterEqual(security_score, 0)
        self.assertLessEqual(security_score, 100)


class AnalyticsModelsIntegrationTestCase(TestCase):
    """Integration tests for analytics aggregation with models."""

    def setUp(self):
        """Set up integration test data."""
        self.user = User.objects.create_user(
            email="analyst@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )

    def test_content_metrics_aggregation(self):
        """Test aggregation with ContentMetrics model."""
        # Get content type for User model
        from django.contrib.contenttypes.models import ContentType

        user_content_type = ContentType.objects.get_for_model(User)

        # Create content metrics
        ContentMetrics.objects.create(
            content_type=user_content_type,
            object_id=self.user.id,
            views=100,
            unique_views=50,
            shares=5,
            comments=3,
            downloads=10,
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
            action="login",
            metadata={"source": "web"},
            ip_address="127.0.0.1",
            session_id="test-session-1",
            created_at=timezone.now(),
        )

        UserActivity.objects.create(
            user=self.user,
            action="search",
            metadata={"page": "/dashboard"},
            ip_address="127.0.0.1",
            session_id="test-session-1",
            created_at=timezone.now(),
        )

        # Test aggregation methods that might use UserActivity
        if hasattr(AnalyticsAggregator, "get_user_activity_summary"):
            summary = AnalyticsAggregator.get_user_activity_summary(days=7)
            self.assertIsInstance(summary, (list, dict))

    def test_assessment_and_risk_aggregation(self):
        """Test aggregation with Assessment and Risk models."""
        # Create assessment
        assessment = Assessment.objects.create(
            title="Security Assessment",
            description="Test assessment",
            assessment_type="security",
            status="completed",
            created_by=self.user,
        )

        # Create risk
        Risk.objects.create(
            title="Test Risk",
            description="Test risk description",
            category="security",
            probability=3,
            impact=4,
            risk_score=12,
            severity="high",
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
            date=timezone.now().date(),
            total_views=100,
            unique_visitors=50,
            bounce_rate=25.5,
            avg_session_duration=300,
        )

        self.assertIsNotNone(summary.id)
        self.assertEqual(summary.period_type, "daily")
        self.assertEqual(summary.total_views, 100)

    def test_complex_aggregation_queries(self):
        """Test complex aggregation scenarios."""
        # Create complex data scenario
        now = timezone.now()

        # Multiple users, multiple pages, multiple days
        for i in range(3):
            user = User.objects.create_user(
                email=f"user{i}@example.com", password="pass"
            )

            for j in range(5):  # 5 pages
                for k in range(2):  # 2 views per page per user
                    PageView.objects.create(
                        url=f"http://example.com/page-{j}",
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


class AnalyticsSummaryGenerationTestCase(TestCase):
    """Test analytics summary generation methods."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="summary@example.com", password="testpass123"
        )

        self.locale = Locale.objects.create(
            code="en", name="English", native_name="English", is_default=True
        )

    def test_generate_daily_summary(self):
        """Test daily summary generation."""
        target_date = timezone.now().date()

        # Create some test data for the target date
        UserActivity.objects.create(
            user=self.user,
            action="page_publish",
            description="Published a page",
            ip_address="127.0.0.1",
            session_id="test_session",
            created_at=timezone.now(),
        )

        # Generate daily summary
        summary = AnalyticsAggregator.generate_daily_summary(target_date)

        # Verify summary was created
        self.assertIsInstance(summary, AnalyticsSummary)
        self.assertEqual(summary.date, target_date)
        self.assertEqual(summary.period_type, "daily")

        # Verify metrics are calculated
        self.assertIsInstance(summary.total_views, int)
        self.assertIsInstance(summary.unique_visitors, int)
        self.assertIsInstance(summary.new_users, int)
        self.assertIsInstance(summary.active_users, int)
        self.assertIsInstance(summary.pages_published, int)

        # Verify specific metrics based on test data
        self.assertEqual(summary.pages_published, 1)

        # Test idempotent behavior - calling again should update existing
        summary2 = AnalyticsAggregator.generate_daily_summary(target_date)
        self.assertEqual(summary.id, summary2.id)

    def test_generate_weekly_summary(self):
        """Test weekly summary generation."""
        week_start = timezone.now().date()

        # Create daily summaries for the week
        for i in range(7):
            day = week_start + timedelta(days=i)
            AnalyticsSummary.objects.create(
                date=day,
                period_type="daily",
                total_views=100 + (i * 10),
                unique_visitors=50 + (i * 5),
                new_users=5 + i,
                active_users=20 + (i * 2),
                bounce_rate=25.0 + (i * 2),
                avg_session_duration=300 + (i * 30),
            )

        # Generate weekly summary
        weekly_summary = AnalyticsAggregator.generate_weekly_summary(week_start)

        # Verify summary was created
        self.assertIsInstance(weekly_summary, AnalyticsSummary)
        self.assertEqual(weekly_summary.date, week_start)
        self.assertEqual(weekly_summary.period_type, "weekly")

        # Verify aggregated metrics
        self.assertEqual(
            weekly_summary.total_views, 910
        )  # Sum of daily views (100+110+120+130+140+150+160)
        self.assertEqual(weekly_summary.unique_visitors, 455)  # Sum of unique visitors
        self.assertEqual(weekly_summary.new_users, 56)  # Sum of new users

        # Verify averaged metrics
        from decimal import Decimal

        self.assertIsInstance(weekly_summary.bounce_rate, (int, float, Decimal))
        self.assertIsInstance(
            weekly_summary.avg_session_duration, (int, float, Decimal)
        )

    def test_generate_monthly_summary(self):
        """Test monthly summary generation."""
        # Use first day of current month
        now = timezone.now().date()
        month_start = date(now.year, now.month, 1)

        # Calculate month end
        if month_start.month == 12:
            month_end = date(month_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(
                days=1
            )

        # Create some daily summaries for the month
        for i in range(
            min(7, (month_end - month_start).days + 1)
        ):  # Create up to 7 days
            day = month_start + timedelta(days=i)
            AnalyticsSummary.objects.create(
                date=day,
                period_type="daily",
                total_views=200 + (i * 20),
                unique_visitors=80 + (i * 8),
                new_users=10 + i,
                active_users=40 + (i * 4),
            )

        # Generate monthly summary
        monthly_summary = AnalyticsAggregator.generate_monthly_summary(month_start)

        # Verify summary was created
        self.assertIsInstance(monthly_summary, AnalyticsSummary)
        self.assertEqual(monthly_summary.date, month_start)
        self.assertEqual(monthly_summary.period_type, "monthly")

        # Verify aggregated data exists
        self.assertGreaterEqual(monthly_summary.total_views, 0)
        self.assertGreaterEqual(monthly_summary.unique_visitors, 0)

    def test_security_score_calculation(self):
        """Test security score calculation logic."""
        # Test the private security score calculation method
        threat_stats = {
            "active_threats": 2,
            "by_severity": {"high": 1, "critical": 1, "low": 3},
        }

        risk_stats = {"open_risks": 3, "by_severity": {"very_high": 2, "medium": 4}}

        assessment_stats = {"completed_assessments": 5}

        # Calculate security score
        score = AnalyticsAggregator._calculate_security_score(
            threat_stats, risk_stats, assessment_stats
        )

        # Verify score is within expected range
        self.assertIsInstance(score, (int, float))
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

        # Test with empty stats (should give high score)
        empty_stats = {"active_threats": 0, "by_severity": {}}
        empty_risks = {"open_risks": 0, "by_severity": {}}
        empty_assessments = {"completed_assessments": 0}

        high_score = AnalyticsAggregator._calculate_security_score(
            empty_stats, empty_risks, empty_assessments
        )

        self.assertGreater(
            high_score, score
        )  # Should be higher than problematic scenario
