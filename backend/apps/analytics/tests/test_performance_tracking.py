"""Comprehensive tests for analytics performance tracking functionality."""

import os

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

import time
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.analytics.models import AnalyticsSummary, PageView, UserActivity
from apps.analytics.utils import (
    calculate_session_duration,
    format_duration,
    get_analytics_context,
    get_date_range,
    is_bot_user_agent,
)
from apps.i18n.models import Locale

User = get_user_model()


class PerformanceTrackingModelTests(TestCase):
    """Test performance-related model functionality."""

    def setUp(self):
        """Set up performance tracking tests."""
        self.user = User.objects.create_user(
            email="performance@example.com", password="perfpass123"
        )

        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )

    def test_page_view_performance_metrics(self):
        """Test PageView performance metric tracking."""
        now = timezone.now()

        # Test various load times and time on page values
        performance_data = [
            {"load_time": 150, "time_on_page": 45},
            {"load_time": 300, "time_on_page": 120},
            {"load_time": 1200, "time_on_page": 300},
            {"load_time": 50, "time_on_page": 15},
            {"load_time": 2500, "time_on_page": 600},  # Slow load, long engagement
        ]

        page_views = []
        for i, perf_data in enumerate(performance_data):
            page_view = PageView.objects.create(
                url=f"http://example.com/perf-test-{i}",
                user=self.user,
                ip_address=f"192.168.1.{i+1}",
                user_agent="Performance Test Browser",
                viewed_at=now - timedelta(minutes=i),
                session_id=f"perf_session_{i}",
                load_time=perf_data["load_time"],
                time_on_page=perf_data["time_on_page"],
            )
            page_views.append(page_view)

        # Test performance aggregations
        from django.db.models import Avg, Max, Min

        perf_stats = PageView.objects.aggregate(
            avg_load_time=Avg("load_time"),
            max_load_time=Max("load_time"),
            min_load_time=Min("load_time"),
            avg_time_on_page=Avg("time_on_page"),
            max_time_on_page=Max("time_on_page"),
        )

        # Verify aggregations
        self.assertIsNotNone(perf_stats["avg_load_time"])
        self.assertEqual(perf_stats["max_load_time"], 2500)
        self.assertEqual(perf_stats["min_load_time"], 50)
        self.assertEqual(perf_stats["max_time_on_page"], 600)

        # Test performance categorization
        fast_pages = PageView.objects.filter(load_time__lt=200).count()
        slow_pages = PageView.objects.filter(load_time__gt=1000).count()

        self.assertEqual(fast_pages, 2)  # 150ms and 50ms
        self.assertEqual(slow_pages, 2)  # 1200ms and 2500ms

    def test_session_duration_calculation(self):
        """Test session duration calculation for performance analysis."""
        session_id = "duration_test_session"
        now = timezone.now()

        # Create page views in a session with specific timing
        session_views = [
            {"url": "http://example.com/start", "offset_minutes": 0},
            {"url": "http://example.com/middle1", "offset_minutes": 2},
            {"url": "http://example.com/middle2", "offset_minutes": 5},
            {"url": "http://example.com/end", "offset_minutes": 10},
        ]

        for view_data in session_views:
            PageView.objects.create(
                url=view_data["url"],
                user=self.user,
                ip_address="127.0.0.1",
                user_agent="Session Test Browser",
                viewed_at=now + timedelta(minutes=view_data["offset_minutes"]),
                session_id=session_id,
            )

        # Test session duration calculation
        duration = calculate_session_duration(session_id)

        # Session should be 10 minutes (600 seconds)
        self.assertEqual(duration, 600)

        # Test with empty session
        empty_duration = calculate_session_duration("nonexistent_session")
        self.assertEqual(empty_duration, 0)

        # Test with single page view session
        single_view_session = "single_view_session"
        PageView.objects.create(
            url="http://example.com/single",
            user=self.user,
            ip_address="127.0.0.1",
            user_agent="Single View Browser",
            viewed_at=now,
            session_id=single_view_session,
        )

        single_duration = calculate_session_duration(single_view_session)
        self.assertEqual(single_duration, 0)  # Single view = 0 duration

    def test_performance_summary_calculations(self):
        """Test performance metrics in analytics summaries."""
        today = timezone.now().date()

        # Create page views with varied performance
        performance_scenarios = [
            {"load_time": 100, "time_on_page": 30},  # Fast, quick exit
            {"load_time": 200, "time_on_page": 180},  # Fast, good engagement
            {"load_time": 1500, "time_on_page": 10},  # Slow, quick exit (bounce)
            {"load_time": 800, "time_on_page": 240},  # Medium, good engagement
        ]

        for i, scenario in enumerate(performance_scenarios):
            PageView.objects.create(
                url=f"http://example.com/summary-test-{i}",
                user=self.user if i % 2 == 0 else None,
                ip_address=f"10.0.0.{i+1}",
                user_agent="Summary Test Browser",
                viewed_at=timezone.now(),
                session_id=f"summary_session_{i}",
                load_time=scenario["load_time"],
                time_on_page=scenario["time_on_page"],
            )

        # Create analytics summary
        from apps.analytics.aggregation import AnalyticsAggregator

        summary = AnalyticsAggregator.generate_daily_summary(today)

        # Verify performance metrics in summary
        self.assertIsNotNone(summary.avg_load_time)
        self.assertGreater(summary.avg_load_time, 0)

        # Test performance thresholds
        fast_threshold = 300  # milliseconds
        slow_pages = PageView.objects.filter(
            viewed_at__date=today, load_time__gt=fast_threshold
        ).count()

        # Should have 2 slow pages (1500ms and 800ms)
        self.assertEqual(slow_pages, 2)

    def test_user_activity_performance_tracking(self):
        """Test performance tracking in user activities."""
        now = timezone.now()

        # Create activities with timing information
        activities = [
            {"action": "login", "duration": 2.5},
            {"action": "search", "duration": 0.8},
            {"action": "page_create", "duration": 15.2},
            {"action": "file_upload", "duration": 8.3},
            {"action": "logout", "duration": 0.3},
        ]

        for i, activity_data in enumerate(activities):
            # Store duration in metadata for custom tracking
            UserActivity.objects.create(
                user=self.user,
                action=activity_data["action"],
                description=f"Performance test {activity_data['action']}",
                metadata={
                    "duration_seconds": activity_data["duration"],
                    "performance_tracked": True,
                },
                ip_address="127.0.0.1",
                session_id="perf_activity_session",
                created_at=now + timedelta(seconds=i * 30),
            )

        # Analyze activity performance
        slow_activities = UserActivity.objects.filter(
            metadata__duration_seconds__gt=10.0
        )

        self.assertEqual(slow_activities.count(), 1)  # page_create at 15.2s

        # Test activity performance aggregation by action type
        from django.contrib.postgres.aggregates import JSONBAgg
        from django.db.models import Avg

        # This would work with PostgreSQL JSONB fields
        # For SQLite testing, we'll verify the data structure
        create_activities = UserActivity.objects.filter(action="page_create")
        self.assertEqual(create_activities.count(), 1)

        create_activity = create_activities.first()
        self.assertEqual(create_activity.metadata["duration_seconds"], 15.2)


class PerformanceAnalyticsViewTests(TestCase):
    """Test performance analytics API endpoints."""

    def setUp(self):
        """Set up performance API tests."""
        self.client = APIClient()

        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            is_superuser=True,
        )

        self.locale, _ = Locale.objects.get_or_create(
            code="en",
            defaults={"name": "English", "native_name": "English", "is_default": True},
        )

        # Create test data with performance metrics
        now = timezone.now()
        for i in range(10):
            PageView.objects.create(
                url=f"http://example.com/api-perf-{i}",
                user=self.admin_user if i % 3 == 0 else None,
                ip_address=f"192.168.1.{i+1}",
                user_agent=f"API Test Browser {i}",
                viewed_at=now - timedelta(hours=i),
                session_id=f"api_perf_session_{i // 3}",
                load_time=100 + (i * 50),  # Increasing load times
                time_on_page=30 + (i * 20),  # Increasing engagement
            )

    def test_traffic_analytics_performance_metrics(self):
        """Test performance metrics in traffic analytics endpoint."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("analytics:analytics-api-traffic-analytics")
        response = self.client.get(url, {"days": 7, "period": "daily"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, list)

        if data:
            # Check that performance metrics are included
            first_day = data[0]
            expected_fields = [
                "date",
                "views",
                "unique_visitors",
                "bounce_rate",
                "avg_session_duration",
            ]

            for field in expected_fields:
                self.assertIn(field, first_day)

            # Verify numeric types for performance metrics
            self.assertIsInstance(first_day["bounce_rate"], (int, float))
            self.assertIsInstance(first_day["avg_session_duration"], (int, float))

    def test_dashboard_performance_summary(self):
        """Test performance metrics in dashboard summary."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("analytics:analytics-api-dashboard-summary")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        # Check performance-related metrics
        performance_fields = [
            "avg_load_time",
            "uptime_percentage",
            "views_trend",
            "visitors_trend",
        ]

        for field in performance_fields:
            self.assertIn(field, data)

        # Verify performance metrics are reasonable
        self.assertIsInstance(data["avg_load_time"], int)
        self.assertGreaterEqual(data["avg_load_time"], 0)

        self.assertIsInstance(data["uptime_percentage"], (int, float))
        self.assertGreaterEqual(data["uptime_percentage"], 0)
        self.assertLessEqual(data["uptime_percentage"], 100)

        # Verify trend data structure
        self.assertIsInstance(data["views_trend"], list)
        self.assertEqual(len(data["views_trend"]), 7)  # 7 days of trend data

    def test_page_views_analytics_performance(self):
        """Test performance data in page views analytics."""
        self.client.force_authenticate(user=self.admin_user)

        url = reverse("analytics:analytics-api-page-views-analytics")
        response = self.client.get(url, {"days": 30, "limit": 10})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIsInstance(data, list)

        if data:
            # Check performance metrics in top content
            first_page = data[0]
            expected_fields = [
                "title",
                "url",
                "views",
                "unique_views",
                "avg_time_on_page",
            ]

            for field in expected_fields:
                self.assertIn(field, first_page)

            # Verify avg_time_on_page is a numeric value
            self.assertIsInstance(first_page["avg_time_on_page"], (int, float))
            self.assertGreaterEqual(first_page["avg_time_on_page"], 0)


class PerformanceUtilityTests(TestCase):
    """Test performance-related utility functions."""

    def test_duration_formatting(self):
        """Test duration formatting utility."""
        test_cases = [
            (30, "30s"),
            (90, "1m 30s"),
            (3661, "1h 1m"),
            (7200, "2h 0m"),
            (0, "0s"),
        ]

        for seconds, expected in test_cases:
            result = format_duration(seconds)
            self.assertEqual(result, expected)

    def test_bot_detection_performance(self):
        """Test bot detection for performance analysis."""
        # Test various user agents
        user_agents = [
            ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0", False),
            ("Googlebot/2.1", True),
            ("Mozilla/5.0 compatible; Bingbot/2.0", True),
            ("curl/7.68.0", True),
            ("python-requests/2.25.1", True),
            ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_7) Safari/604.1", False),
            ("facebookexternalhit/1.1", True),
        ]

        for user_agent, is_bot in user_agents:
            result = is_bot_user_agent(user_agent)
            self.assertEqual(result, is_bot, f"Failed for user agent: {user_agent}")

    def test_date_range_performance(self):
        """Test date range utility performance."""
        # Test various period types
        periods = ["day", "week", "month", "quarter", "year"]
        base_date = "2024-06-15"

        for period in periods:
            start_date, end_date = get_date_range(period, base_date)

            # Verify date types
            self.assertIsInstance(start_date, date)
            self.assertIsInstance(end_date, date)

            # Verify logical order
            self.assertLessEqual(start_date, end_date)

            # Verify reasonable ranges
            date_diff = (end_date - start_date).days

            if period == "day":
                self.assertEqual(date_diff, 0)
            elif period == "week":
                self.assertEqual(date_diff, 6)
            elif period == "month":
                self.assertLessEqual(date_diff, 31)
            elif period == "quarter":
                self.assertLessEqual(date_diff, 92)
            elif period == "year":
                self.assertLessEqual(date_diff, 366)

    def test_analytics_context_extraction(self):
        """Test analytics context extraction performance."""

        # Mock request object
        class MockRequest:
            def __init__(self):
                self.META = {
                    "HTTP_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
                    "HTTP_X_FORWARDED_FOR": "203.0.113.1",
                    "HTTP_REFERER": "https://example.com/referrer",
                }
                self.session = type(
                    "Session", (), {"session_key": "test_session_123"}
                )()

        mock_request = MockRequest()

        # Test context extraction
        context = get_analytics_context(mock_request)

        # Verify expected fields
        expected_fields = [
            "ip_address",
            "user_agent",
            "browser",
            "os",
            "device_type",
            "country",
            "city",
            "referrer",
            "is_bot",
            "session_key",
        ]

        for field in expected_fields:
            self.assertIn(field, context)

        # Verify specific values
        self.assertEqual(context["ip_address"], "203.0.113.1")
        self.assertEqual(context["session_key"], "test_session_123")
        self.assertEqual(context["referrer"], "https://example.com/referrer")
        self.assertFalse(context["is_bot"])


class PerformanceBenchmarkTests(TestCase):
    """Test performance benchmarks and optimization."""

    def setUp(self):
        """Set up benchmark tests."""
        self.user = User.objects.create_user(
            email="benchmark@example.com", password="benchpass123"
        )

    def test_bulk_data_creation_performance(self):
        """Test performance of bulk data creation."""
        # Measure time for bulk creation vs individual creation
        import time

        # Test bulk creation
        bulk_data = []
        for i in range(100):
            bulk_data.append(
                PageView(
                    url=f"http://example.com/bulk-{i}",
                    user=self.user,
                    ip_address=f"10.1.{i // 256}.{i % 256}",
                    user_agent="Bulk Creation Browser",
                    viewed_at=timezone.now() - timedelta(minutes=i),
                    session_id=f"bulk_session_{i // 10}",
                    load_time=100 + (i % 50),
                )
            )

        start_time = time.time()
        PageView.objects.bulk_create(bulk_data, batch_size=50)
        bulk_time = time.time() - start_time

        # Verify all records were created
        self.assertEqual(PageView.objects.count(), 100)

        # Bulk creation should complete relatively quickly
        self.assertLess(bulk_time, 5.0)  # Should take less than 5 seconds

    def test_query_performance_optimization(self):
        """Test query optimization for performance tracking."""
        # Create test data
        for i in range(50):
            PageView.objects.create(
                url=f"http://example.com/query-opt-{i}",
                user=self.user,
                ip_address=f"192.168.100.{i+1}",
                user_agent="Query Optimization Browser",
                viewed_at=timezone.now() - timedelta(minutes=i),
                session_id=f"opt_session_{i // 5}",
                load_time=150 + (i * 10),
            )

        # Test optimized query with select_related
        start_time = time.time()

        optimized_queryset = PageView.objects.select_related("user").filter(
            user__isnull=False
        )

        # Force evaluation
        optimized_results = list(optimized_queryset)
        optimized_time = time.time() - start_time

        # Test non-optimized query
        start_time = time.time()

        non_optimized_queryset = PageView.objects.filter(user__isnull=False)
        non_optimized_results = list(non_optimized_queryset)
        non_optimized_time = time.time() - start_time

        # Both should return the same results
        self.assertEqual(len(optimized_results), len(non_optimized_results))

        # Both queries should complete within reasonable time
        # Note: In test environments, optimization differences may be minimal
        self.assertLess(optimized_time, 1.0)  # Should complete within 1 second
        self.assertLess(non_optimized_time, 1.0)  # Should complete within 1 second

    @override_settings(DEBUG=True)
    def test_database_query_count(self):
        """Test database query count for performance endpoints."""
        from django.db import connection
        from django.test.utils import override_settings

        # Create test data
        for i in range(10):
            PageView.objects.create(
                url=f"http://example.com/query-count-{i}",
                user=self.user,
                ip_address="127.0.0.1",
                user_agent="Query Count Browser",
                viewed_at=timezone.now() - timedelta(hours=i),
                session_id=f"query_count_session_{i // 3}",
            )

        # Reset query count
        connection.queries_log.clear()

        # Test traffic trends query count
        from apps.analytics.aggregation import AnalyticsAggregator

        start_query_count = len(connection.queries)
        trends = AnalyticsAggregator.get_traffic_trends(days=7, period="daily")
        end_query_count = len(connection.queries)

        # Should be efficient with minimal queries
        query_count = end_query_count - start_query_count
        self.assertLessEqual(query_count, 5)  # Should use at most 5 queries

        # Verify results are returned
        self.assertIsInstance(trends, list)

    def test_memory_usage_monitoring(self):
        """Test memory usage patterns for large analytics operations."""
        import gc
        import sys

        # Force garbage collection before test
        gc.collect()

        # Get initial memory usage (approximate)
        initial_objects = len(gc.get_objects())

        # Create and process data
        bulk_data = []
        for i in range(1000):
            bulk_data.append(
                PageView(
                    url=f"http://example.com/memory-{i}",
                    user=self.user if i % 10 == 0 else None,
                    ip_address=f"172.16.{i // 256}.{i % 256}",
                    user_agent="Memory Test Browser",
                    viewed_at=timezone.now() - timedelta(seconds=i),
                    session_id=f"memory_session_{i // 20}",
                )
            )

        PageView.objects.bulk_create(bulk_data, batch_size=100)

        # Process data in chunks to avoid memory buildup
        total_processed = 0
        chunk_size = 100

        for offset in range(0, 1000, chunk_size):
            chunk = PageView.objects.all()[offset : offset + chunk_size]
            # Process chunk (simulate analytics calculations)
            for page_view in chunk:
                # Simulate processing
                _ = page_view.url + str(page_view.load_time or 0)
            total_processed += len(chunk)

        # Force garbage collection
        gc.collect()

        # Check that we processed all data
        self.assertEqual(total_processed, 1000)

        # Memory usage should not have grown excessively
        final_objects = len(gc.get_objects())
        object_growth = final_objects - initial_objects

        # Object growth should be reasonable (allowing for test framework overhead)
        self.assertLess(object_growth, 10000)  # Arbitrary reasonable limit
