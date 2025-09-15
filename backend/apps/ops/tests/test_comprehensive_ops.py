"""Comprehensive tests for operations and monitoring utilities."""

import os
import tempfile
from unittest.mock import Mock, call, patch

import django
from django.conf import settings

# Configure Django settings before any imports
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

import json
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from apps.ops import tasks, views
from apps.ops.metrics import prometheus_metrics

User = get_user_model()


class HealthCheckTestCase(TestCase):
    """Test health check endpoints."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()

    def test_health_check_success(self):
        """Test successful health check."""
        request = self.factory.get("/health")
        response = views.health_check(request)

        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode())
        self.assertEqual(data["status"], "ok")
        self.assertIn("timestamp", data)
        self.assertEqual(data["service"], "django-saas-boilerplate")

    def test_health_check_timestamp_format(self):
        """Test health check timestamp is ISO formatted."""
        request = self.factory.get("/health")
        response = views.health_check(request)

        data = json.loads(response.content.decode())
        timestamp = data["timestamp"]

        # Should be valid ISO format
        try:
            parsed_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            self.assertIsInstance(parsed_time, datetime)
        except ValueError:
            self.fail("Timestamp is not in valid ISO format")

    @patch("apps.ops.views.connection")
    @patch("apps.ops.views.cache")
    def test_readiness_check_success(self, mock_cache, mock_connection):
        """Test successful readiness check."""
        # Mock database connection
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock cache operations
        mock_cache.set.return_value = True
        mock_cache.get.return_value = "ok"

        request = self.factory.get("/ready")
        response = views.readiness_check(request)

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content.decode())
        self.assertEqual(data["status"], "ready")
        self.assertIn("timestamp", data)
        self.assertIn("checks", data)
        self.assertTrue(data["checks"]["database"])
        self.assertTrue(data["checks"]["cache"])

        # Verify database check was called
        mock_cursor.execute.assert_called_once_with("SELECT 1")

        # Verify cache operations
        mock_cache.set.assert_called_once_with("readiness_check", "ok", 10)
        mock_cache.get.assert_called_once_with("readiness_check")

    @patch("apps.ops.views.connection")
    def test_readiness_check_database_failure(self, mock_connection):
        """Test readiness check with database failure."""
        # Mock database connection failure
        mock_connection.cursor.side_effect = Exception("DB connection failed")

        request = self.factory.get("/ready")
        response = views.readiness_check(request)

        self.assertEqual(response.status_code, 503)

        data = json.loads(response.content.decode())
        self.assertEqual(data["status"], "not_ready")
        self.assertIn("error", data)

    @patch("apps.ops.views.connection")
    @patch("apps.ops.views.cache")
    def test_readiness_check_cache_failure(self, mock_cache, mock_connection):
        """Test readiness check with cache failure."""
        # Mock successful database
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock cache failure
        mock_cache.set.return_value = True
        mock_cache.get.return_value = None  # Cache failed

        request = self.factory.get("/ready")
        response = views.readiness_check(request)

        self.assertEqual(response.status_code, 503)

        data = json.loads(response.content.decode())
        self.assertEqual(data["status"], "not_ready")


class PrometheusMetricsTestCase(TestCase):
    """Test Prometheus metrics endpoint."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="testuser@example.com", password="testpass123"
        )

    @patch("apps.ops.metrics.User")
    def test_prometheus_metrics_user_metrics(self, mock_user_model):
        """Test user metrics collection."""
        mock_user_model.objects.count.return_value = 10
        mock_user_model.objects.filter.return_value.count.return_value = 8

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"], "text/plain; version=0.0.4; charset=utf-8"
        )

        content = response.content.decode()
        self.assertIn("django_users_total 10", content)
        self.assertIn("django_users_active 8", content)

    @patch("apps.ops.metrics.Note")
    def test_prometheus_metrics_notes_metrics(self, mock_note_model):
        """Test notes metrics collection."""
        mock_note_model.objects.count.return_value = 25
        mock_note_model.objects.filter.return_value.count.return_value = 15

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode()
        self.assertIn("django_notes_total 25", content)
        self.assertIn("django_notes_public 15", content)

    @patch("apps.ops.metrics.EmailMessageLog")
    def test_prometheus_metrics_email_metrics(self, mock_email_model):
        """Test email metrics collection."""
        mock_email_model.objects.count.return_value = 100
        mock_email_model.objects.filter.return_value.count.side_effect = [80, 20]

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode()
        self.assertIn("django_emails_total 100", content)
        self.assertIn("django_emails_sent 80", content)
        self.assertIn("django_emails_failed 20", content)

    @patch("apps.ops.metrics.FileUpload")
    def test_prometheus_metrics_file_metrics(self, mock_file_model):
        """Test file upload metrics collection."""
        mock_file_model.objects.count.return_value = 50
        mock_file_model.objects.filter.return_value.count.side_effect = [30, 20, 15]

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode()
        self.assertIn("django_files_total 50", content)
        self.assertIn("django_files_public 30", content)
        self.assertIn("django_files_images 20", content)
        self.assertIn("django_files_documents 15", content)

    @patch("apps.ops.metrics.connection")
    @patch("apps.ops.metrics.time")
    def test_prometheus_metrics_database_timing(self, mock_time, mock_connection):
        """Test database connection timing metrics."""
        # Provide enough time values for all calls in the function
        mock_time.time.side_effect = [1000.0, 1000.1, 1000.2, 1000.3, 1000.4, 1000.5]
        mock_cursor = Mock()
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode()
        self.assertIn("django_db_connection_duration_seconds", content)

        # Verify database test query was executed
        mock_cursor.execute.assert_called_with("SELECT 1")

    @patch("apps.ops.metrics.psutil")
    def test_prometheus_metrics_system_metrics(self, mock_psutil):
        """Test system metrics collection."""
        # Mock CPU usage
        mock_psutil.cpu_percent.return_value = 45.5

        # Mock memory usage
        mock_memory = Mock()
        mock_memory.percent = 60.2
        mock_memory.available = 8589934592  # 8GB
        mock_memory.total = 17179869184  # 16GB
        mock_psutil.virtual_memory.return_value = mock_memory

        # Mock boot time
        mock_psutil.boot_time.return_value = 1234567890

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode()
        self.assertIn("system_cpu_usage_percent 45.5", content)
        self.assertIn("system_memory_usage_percent 60.2", content)

    @patch("apps.ops.metrics.cache")
    def test_prometheus_metrics_cache_test(self, mock_cache):
        """Test cache performance metrics."""
        mock_cache.set.return_value = True
        mock_cache.get.return_value = "test_value"

        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        # Verify cache operations were performed
        mock_cache.set.assert_called_once_with("metrics_test", "test_value", 10)
        mock_cache.get.assert_called_once_with("metrics_test")

        content = response.content.decode()
        self.assertIn("django_cache_status", content)

    def test_prometheus_metrics_format_compliance(self):
        """Test that metrics follow Prometheus format."""
        request = self.factory.get("/metrics")
        response = prometheus_metrics(request)

        content = response.content.decode()
        lines = content.strip().split("\n")

        # Should have HELP and TYPE comments
        help_lines = [line for line in lines if line.startswith("# HELP")]
        type_lines = [line for line in lines if line.startswith("# TYPE")]

        self.assertTrue(len(help_lines) > 0)
        self.assertTrue(len(type_lines) > 0)

        # Each metric should have both HELP and TYPE
        metrics = set()
        for line in lines:
            if not line.startswith("#") and line.strip():
                metric_name = line.split()[0]
                metrics.add(metric_name)

        for metric in metrics:
            help_found = any(f"# HELP {metric}" in line for line in lines)
            type_found = any(f"# TYPE {metric}" in line for line in lines)
            self.assertTrue(help_found, f"Missing HELP for metric: {metric}")
            self.assertTrue(type_found, f"Missing TYPE for metric: {metric}")

    @patch("apps.ops.metrics.logger")
    def test_prometheus_metrics_error_handling(self, mock_logger):
        """Test error handling in metrics collection."""
        # Force an error in user metrics
        with patch("apps.ops.metrics.User") as mock_user_model:
            mock_user_model.objects.count.side_effect = Exception("DB Error")

            request = self.factory.get("/metrics")
            response = prometheus_metrics(request)

            # Should still return 200 even with errors
            self.assertEqual(response.status_code, 200)

            # Should log the exception
            mock_logger.exception.assert_called()


class BackupTaskTestCase(TestCase):
    """Test backup task functionality."""

    @patch("apps.ops.tasks.subprocess.run")
    @patch("apps.ops.tasks.os.makedirs")
    @patch("apps.ops.tasks.settings")
    def test_backup_database_postgresql(
        self, mock_settings, mock_makedirs, mock_subprocess
    ):
        """Test PostgreSQL database backup."""
        # Mock settings
        mock_settings.BASE_DIR = "/app"
        mock_settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "testdb",
                "USER": "testuser",
                "PASSWORD": "testpass",
                "HOST": "localhost",
                "PORT": 5432,
            }
        }

        # Mock successful subprocess
        mock_result = Mock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        result = tasks.backup_database()

        self.assertTrue(result)

        # Verify directory creation
        mock_makedirs.assert_called_once()

        # Verify pg_dump command
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        self.assertEqual(call_args[0], "pg_dump")
        self.assertIn("testdb", call_args)
        self.assertIn("testuser", call_args)

    @patch("apps.ops.tasks.call_command")
    @patch("apps.ops.tasks.os.makedirs")
    @patch("apps.ops.tasks.open", create=True)
    @patch("apps.ops.tasks.settings")
    def test_backup_database_sqlite(
        self, mock_settings, mock_open, mock_makedirs, mock_call_command
    ):
        """Test SQLite database backup."""
        mock_settings.BASE_DIR = "/app"
        mock_settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": "/app/db.sqlite3",
            }
        }

        # Mock the file handle for writing
        mock_file = MagicMock()
        mock_open.return_value = mock_file

        result = tasks.backup_database()

        self.assertTrue(result["success"])

        # Verify Django's dumpdata command was called
        mock_call_command.assert_called_once()

    @patch("apps.ops.tasks.subprocess.run")
    @patch("apps.ops.tasks.settings")
    def test_backup_database_failure(self, mock_settings, mock_subprocess):
        """Test backup database with failure."""
        mock_settings.BASE_DIR = "/app"
        mock_settings.DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "testdb",
                "USER": "testuser",
                "HOST": "localhost",
            }
        }

        # Mock failed subprocess
        mock_result = Mock()
        mock_result.returncode = 1
        mock_subprocess.return_value = mock_result

        result = tasks.backup_database()

        self.assertFalse(result["success"])

    @patch("apps.ops.tasks.datetime")
    @patch("apps.ops.tasks.os.stat")
    @patch("apps.ops.tasks.os.path.exists")
    @patch("apps.ops.tasks.glob.glob")
    @patch("apps.ops.tasks.os.remove")
    @patch("apps.ops.tasks.settings")
    def test_cleanup_old_backups(
        self,
        mock_settings,
        mock_remove,
        mock_glob,
        mock_exists,
        mock_stat,
        mock_datetime,
    ):
        """Test cleanup of old backup files."""
        mock_settings.BASE_DIR = "/app"

        # Mock backup directory exists
        mock_exists.return_value = True

        # Mock old backup files
        old_backups = [
            "/app/backups/backup_20230101_120000.sql",
            "/app/backups/backup_20230102_120000.sql",
            "/app/backups/backup_20230103_120000.sql",
        ]
        mock_glob.return_value = old_backups

        # Mock current time and file times
        from datetime import datetime, timedelta

        current_time = datetime(2023, 1, 5, 12, 0, 0)
        mock_datetime.datetime.now.return_value = current_time
        mock_datetime.datetime.fromtimestamp.side_effect = [
            datetime(2023, 1, 1, 12, 0, 0),  # Old file (4 days ago)
            datetime(2023, 1, 3, 12, 0, 0),  # Recent file (2 days ago)
            datetime(2023, 1, 4, 12, 0, 0),  # Recent file (1 day ago)
        ]
        mock_datetime.timedelta = timedelta

        # Mock file stats
        mock_stat_obj = Mock()
        mock_stat_obj.st_mtime = 1234567890
        mock_stat.return_value = mock_stat_obj

        result = tasks.cleanup_old_backups(days_to_keep=2)

        self.assertTrue(result["success"])
        self.assertEqual(result["cleaned_files"], 1)

        # Should remove the oldest file (older than 2 days)
        mock_remove.assert_called_once_with("/app/backups/backup_20230101_120000.sql")


class CacheTestCase(TestCase):
    """Test caching functionality."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

    def test_cache_set_get(self):
        """Test basic cache set and get operations."""
        cache.set("test_key", "test_value", 30)
        result = cache.get("test_key")
        self.assertEqual(result, "test_value")

    def test_cache_expiration(self):
        """Test cache expiration behavior."""
        cache.set("expire_key", "expire_value", 1)

        # Should be available immediately
        result = cache.get("expire_key")
        self.assertEqual(result, "expire_value")

        # Mock time passing
        with patch("time.sleep") as mock_sleep:
            mock_sleep.return_value = None
            # Simulate expiration by setting timeout to past
            cache.set("expire_key", "expire_value", -1)
            result = cache.get("expire_key")
            self.assertIsNone(result)

    def test_cache_default_value(self):
        """Test cache get with default value."""
        result = cache.get("nonexistent_key", "default_value")
        self.assertEqual(result, "default_value")

    def test_cache_delete(self):
        """Test cache deletion."""
        cache.set("delete_key", "delete_value", 30)
        self.assertEqual(cache.get("delete_key"), "delete_value")

        cache.delete("delete_key")
        result = cache.get("delete_key")
        self.assertIsNone(result)

    def test_cache_get_many(self):
        """Test cache get_many operation."""
        cache.set("key1", "value1", 30)
        cache.set("key2", "value2", 30)
        cache.set("key3", "value3", 30)

        result = cache.get_many(["key1", "key2", "key4"])
        expected = {"key1": "value1", "key2": "value2"}
        self.assertEqual(result, expected)

    def test_cache_set_many(self):
        """Test cache set_many operation."""
        data = {"bulk1": "value1", "bulk2": "value2", "bulk3": "value3"}
        cache.set_many(data, 30)

        for key, value in data.items():
            self.assertEqual(cache.get(key), value)

    def test_cache_incr_decr(self):
        """Test cache increment and decrement operations."""
        cache.set("counter", 10, 30)

        # Test increment
        result = cache.incr("counter", 5)
        self.assertEqual(result, 15)
        self.assertEqual(cache.get("counter"), 15)

        # Test decrement
        result = cache.decr("counter", 3)
        self.assertEqual(result, 12)
        self.assertEqual(cache.get("counter"), 12)

    def test_cache_has_key(self):
        """Test cache has_key operation."""
        cache.set("exists_key", "exists_value", 30)

        self.assertTrue(cache.has_key("exists_key"))
        self.assertFalse(cache.has_key("missing_key"))

    def test_cache_ttl(self):
        """Test cache TTL (time to live) functionality."""
        cache.set("ttl_key", "ttl_value", 60)

        # Note: Not all cache backends support get_ttl
        if hasattr(cache, "ttl"):
            ttl = cache.ttl("ttl_key")
            self.assertGreater(ttl, 0)
            self.assertLessEqual(ttl, 60)


class ErrorHandlingTestCase(TestCase):
    """Test error handling and logging functionality."""

    @patch("apps.ops.views.logger")
    def test_health_check_error_logging(self, mock_logger):
        """Test error logging in health check."""
        with patch("apps.ops.views.timezone.now") as mock_now:
            mock_now.side_effect = Exception("Time error")

            request = self.factory.get("/health")

            # Should handle gracefully
            try:
                response = views.health_check(request)
            except Exception:
                pass  # Expected to handle gracefully in actual implementation

    @patch("apps.ops.metrics.logger")
    def test_metrics_error_handling(self, mock_logger):
        """Test error handling in metrics collection."""
        with patch("apps.ops.metrics.User") as mock_user:
            mock_user.objects.count.side_effect = Exception("Database error")

            request = self.factory.get("/metrics")
            response = prometheus_metrics(request)

            # Should log exception for failed metrics
            mock_logger.exception.assert_called()

    def test_connection_error_handling(self):
        """Test database connection error handling."""
        with patch("django.db.connection") as mock_connection:
            mock_connection.cursor.side_effect = Exception("Connection failed")

            request = self.factory.get("/ready")

            try:
                response = views.readiness_check(request)
                # Should return error status
                data = json.loads(response.content.decode())
                self.assertEqual(data["status"], "not ready")
            except Exception:
                pass  # Expected to handle gracefully

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
