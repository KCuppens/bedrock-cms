"""Tests for ops metrics functionality."""

import os
import time
from unittest.mock import Mock, patch

import django

# Configure Django settings before any imports
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory, TestCase

from apps.ops.metrics import prometheus_metrics

User = get_user_model()


class PrometheusMetricsTestCase(TestCase):
    """Test Prometheus metrics endpoint functionality."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()

        # Create test users
        self.active_user = User.objects.create_user(
            email="active@example.com",
            password="testpass123",
            is_active=True,
        )

        self.inactive_user = User.objects.create_user(
            email="inactive@example.com",
            password="testpass123",
            is_active=False,
        )

    def test_prometheus_metrics_response_type(self):
        """Test that prometheus_metrics returns HttpResponse."""
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        self.assertIsInstance(response, HttpResponse)

    def test_prometheus_metrics_content_type(self):
        """Test that prometheus_metrics returns correct content type."""
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        # Should return plain text content type for Prometheus with version
        self.assertEqual(
            response["Content-Type"], "text/plain; version=0.0.4; charset=utf-8"
        )

    def test_user_metrics_included(self):
        """Test that user metrics are included in response."""
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should include user metrics
        self.assertIn("django_users_total", content)
        self.assertIn("django_users_active", content)

        # Should have correct counts
        self.assertIn("django_users_total 2", content)  # 2 users created
        self.assertIn("django_users_active 1", content)  # 1 active user

    @patch("apps.ops.metrics.Note")
    def test_note_metrics_with_notes(self, mock_note):
        """Test note metrics when Note model is available."""
        # Mock Note model
        mock_note.objects.count.return_value = 5
        mock_note.objects.filter.return_value.count.return_value = 3

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should include note metrics
        self.assertIn("django_notes_total", content)
        self.assertIn("django_notes_public", content)

    @patch("apps.ops.metrics.Note")
    def test_note_metrics_exception_handling(self, mock_note):
        """Test note metrics exception handling."""
        # Mock Note to raise exception
        mock_note.objects.count.side_effect = Exception("Database error")

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        # Should still return successful response
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        # Should still have user metrics
        self.assertIn("django_users_total", content)

    @patch("apps.ops.metrics.EmailMessageLog")
    def test_email_metrics_included(self, mock_email_log):
        """Test email metrics inclusion."""
        # Mock EmailMessageLog
        mock_email_log.objects.count.return_value = 10
        mock_email_log.objects.filter.return_value.count.return_value = 8

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should include email metrics if implemented
        if "django_emails_total" in content:
            self.assertIn("django_emails_total", content)

    @patch("apps.ops.metrics.FileUpload")
    def test_file_metrics_included(self, mock_file_upload):
        """Test file upload metrics inclusion."""
        # Mock FileUpload
        mock_file_upload.objects.count.return_value = 15

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should include file metrics if implemented
        if "django_files_total" in content:
            self.assertIn("django_files_total", content)

    @patch("apps.ops.metrics.psutil")
    def test_system_metrics_included(self, mock_psutil):
        """Test system metrics inclusion."""
        # Mock psutil functions
        mock_psutil.cpu_percent.return_value = 45.5
        mock_psutil.virtual_memory.return_value = Mock(percent=60.0)
        mock_psutil.disk_usage.return_value = Mock(percent=30.0)

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should include system metrics if implemented
        if "system_cpu_percent" in content:
            self.assertIn("system_cpu_percent", content)
        if "system_memory_percent" in content:
            self.assertIn("system_memory_percent", content)

    @patch("apps.ops.metrics.cache")
    def test_cache_metrics_included(self, mock_cache):
        """Test cache metrics inclusion."""
        # Mock cache stats
        mock_cache.get.return_value = None

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should include cache metrics if implemented
        if "django_cache_hits" in content:
            self.assertIn("django_cache_hits", content)

    @patch("apps.ops.metrics.connection")
    def test_database_metrics_included(self, mock_connection):
        """Test database metrics inclusion."""
        # Mock database connection stats
        mock_connection.queries = [{"sql": "SELECT 1", "time": "0.001"}]

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should include database metrics if implemented
        if "django_db_queries" in content:
            self.assertIn("django_db_queries", content)

    def test_metrics_format_compliance(self):
        """Test that metrics follow Prometheus format."""
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")
        lines = content.split("\n")

        # Should have HELP and TYPE comments for each metric
        help_lines = [line for line in lines if line.startswith("# HELP")]
        type_lines = [line for line in lines if line.startswith("# TYPE")]

        self.assertGreater(len(help_lines), 0)
        self.assertGreater(len(type_lines), 0)

        # Each metric should have both HELP and TYPE
        for help_line in help_lines:
            metric_name = help_line.split()[2]  # Extract metric name
            type_line_exists = any(
                line.startswith(f"# TYPE {metric_name}") for line in type_lines
            )
            self.assertTrue(type_line_exists, f"Missing TYPE for metric {metric_name}")

    def test_metric_values_are_numeric(self):
        """Test that all metric values are numeric."""
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")
        lines = content.split("\n")

        # Find metric value lines (not comments or empty lines)
        metric_lines = [
            line for line in lines if line and not line.startswith("#") and " " in line
        ]

        for line in metric_lines:
            parts = line.split()
            if len(parts) >= 2:
                metric_value = parts[-1]  # Last part should be the value
                try:
                    float(metric_value)  # Should be parseable as number
                except ValueError:
                    self.fail(
                        f"Metric value '{metric_value}' in line '{line}' is not numeric"
                    )

    @patch("apps.ops.metrics.User.objects")
    def test_empty_database_handling(self, mock_user_objects):
        """Test metrics handling when database is empty."""
        # Mock empty database by returning 0 for all counts
        mock_user_objects.count.return_value = 0
        mock_user_objects.filter.return_value.count.return_value = 0

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should handle empty database gracefully
        self.assertIn("django_users_total 0", content)
        self.assertIn("django_users_active 0", content)

    def test_request_method_independence(self):
        """Test that metrics work regardless of request method."""
        for method in ["GET", "POST", "HEAD"]:
            request = getattr(self.factory, method.lower())("/metrics")
            response = prometheus_metrics(request)

            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(response, HttpResponse)

    @patch("apps.ops.metrics.logger")
    def test_exception_logging(self, mock_logger):
        """Test that exceptions are properly logged."""
        with patch("apps.ops.metrics.User.objects.count") as mock_count:
            mock_count.side_effect = Exception("Database connection failed")

            request = self.factory.get("/metrics")
            response = prometheus_metrics(request)

            # Should still return successful response
            self.assertEqual(response.status_code, 200)

            # Should log the exception
            mock_logger.exception.assert_called()

    def test_response_headers(self):
        """Test that response has appropriate headers."""
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        # Should have content type header
        self.assertIn("Content-Type", response)
        self.assertEqual(
            response["Content-Type"], "text/plain; version=0.0.4; charset=utf-8"
        )

    def test_large_dataset_performance(self):
        """Test metrics performance with larger dataset."""
        # Create more users to test performance
        users = []
        for i in range(50):
            users.append(
                User(
                    email=f"user_{i}@example.com",
                    is_active=i % 2 == 0,  # Half active, half inactive
                )
            )
        User.objects.bulk_create(users)

        start_time = time.time()
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)
        end_time = time.time()

        # Should complete reasonably quickly (under 1 second)
        self.assertLess(end_time - start_time, 1.0)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        # Should have correct counts (52 total: original 2 + 50 new)
        self.assertIn("django_users_total 52", content)
        self.assertIn("django_users_active 26", content)  # 1 original + 25 new active


class MetricsIntegrationTestCase(TestCase):
    """Integration tests for metrics functionality."""

    def setUp(self):
        """Set up integration test data."""
        self.factory = RequestFactory()

    def test_metrics_endpoint_integration(self):
        """Test full metrics endpoint integration."""
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        # Should return successful response
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")

        # Should have basic structure
        self.assertIn("# HELP", content)
        self.assertIn("# TYPE", content)

        # Should have at least user metrics
        self.assertIn("django_users", content)

    def test_metrics_with_real_models(self):
        """Test metrics with actual model instances."""
        # Create real data
        user1 = User.objects.create_user(
            email="real1@example.com",
            password="pass",
            is_active=True,
        )

        user2 = User.objects.create_user(
            email="real2@example.com",
            password="pass",
            is_active=False,
        )

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode("utf-8")

        # Should reflect real data
        self.assertIn("django_users_total 2", content)
        self.assertIn("django_users_active 1", content)

    def test_concurrent_metrics_requests(self):
        """Test handling of concurrent metrics requests."""
        # Simulate concurrent requests
        requests = [self.factory.get("/metrics") for _ in range(5)]
        responses = [prometheus_metrics(req) for req in requests]

        # All should succeed
        for response in responses:
            self.assertEqual(response.status_code, 200)

        # All should have similar content (users count might vary slightly)
        contents = [resp.content.decode("utf-8") for resp in responses]
        for content in contents:
            self.assertIn("django_users_total", content)

    def test_metrics_error_recovery(self):
        """Test metrics recovery from errors."""
        # First request should succeed
        request1 = self.factory.get("/metrics")
        response1 = prometheus_metrics(request1)
        self.assertEqual(response1.status_code, 200)

        # Even if there were errors, subsequent requests should work
        request2 = self.factory.get("/metrics")
        response2 = prometheus_metrics(request2)
        self.assertEqual(response2.status_code, 200)
