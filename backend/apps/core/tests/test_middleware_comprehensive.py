"""
Comprehensive test coverage for core middleware classes.

Tests all middleware in apps.core.middleware and apps.core.middleware_performance, including:
- SecurityHeadersMiddleware functionality and header configuration
- AdminIPAllowlistMiddleware IP filtering and CIDR support
- DemoModeMiddleware HTML injection
- PerformanceMonitoringMiddleware request timing and query tracking
- QueryCountLimitMiddleware N+1 query prevention
- CacheHitRateMiddleware cache statistics
- DatabaseConnectionPoolMiddleware connection management
- RequestThrottlingMiddleware rate limiting
- CompressionMiddleware response compression
- Middleware ordering and request/response flow
- Error handling and edge cases
- Performance impact testing
"""

import ipaddress
import json
import logging
import os
import time
from io import StringIO
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

import django
from django.conf import settings

# Configure Django settings if not already configured
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")
    django.setup()

try:
    import brotli

    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False

import django

# Configure Django settings before imports
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden, JsonResponse
from django.test import RequestFactory, TestCase, override_settings
from django.test.utils import override_settings
from django.utils.deprecation import MiddlewareMixin

from apps.core.middleware import (
    AdminIPAllowlistMiddleware,
    DemoModeMiddleware,
    SecurityHeadersMiddleware,
)
from apps.core.middleware_performance import (
    CacheHitRateMiddleware,
    CompressionMiddleware,
    DatabaseConnectionPoolMiddleware,
    PerformanceMonitoringMiddleware,
    QueryCountLimitMiddleware,
    RequestThrottlingMiddleware,
)

User = get_user_model()


class MiddlewareTestBase(TestCase):
    """Base test class for middleware tests."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.staff_user = User.objects.create_user(
            email="staff@example.com", password="testpass123", is_staff=True
        )

        # Clear cache before each test
        cache.clear()

        # Mock get_response function
        self.get_response = Mock(return_value=HttpResponse("OK"))

    def create_request(self, path="/", method="GET", **kwargs):
        """Create a request with default settings."""
        if method == "GET":
            request = self.factory.get(path, **kwargs)
        elif method == "POST":
            request = self.factory.post(path, **kwargs)
        else:
            request = getattr(self.factory, method.lower())(path, **kwargs)

        # Add session and user attributes that middleware expects
        request.session = {}
        request.user = self.user
        return request


class SecurityHeadersMiddlewareTests(MiddlewareTestBase):
    """Tests for SecurityHeadersMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = SecurityHeadersMiddleware(self.get_response)

    @override_settings(DEBUG=False)
    def test_security_headers_production(self):
        """Test security headers in production mode."""
        request = self.create_request()
        response = self.middleware(request)

        # Check CSP header
        self.assertIn("Content-Security-Policy", response)
        csp = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)

        # Check other security headers
        self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-XSS-Protection"], "1; mode=block")
        self.assertEqual(response["X-Frame-Options"], "DENY")

        # Check Permissions Policy
        self.assertIn("Permissions-Policy", response)
        permissions_policy = response["Permissions-Policy"]
        self.assertIn("camera=()", permissions_policy)
        self.assertIn("microphone=()", permissions_policy)
        self.assertIn("geolocation=()", permissions_policy)
        self.assertIn("interest-cohort=()", permissions_policy)

    @override_settings(DEBUG=True)
    def test_security_headers_debug(self):
        """Test security headers in debug mode."""
        # Clear cached headers to force recomputation
        SecurityHeadersMiddleware._cached_headers = None

        request = self.create_request()
        response = self.middleware(request)

        # Check CSP header is more permissive in debug mode
        csp = response["Content-Security-Policy"]
        self.assertIn("'unsafe-inline'", csp)
        self.assertIn("'unsafe-eval'", csp)
        self.assertIn("ws:", csp)
        self.assertIn("wss:", csp)

    @override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=True,
    )
    def test_hsts_headers(self):
        """Test HSTS headers when SSL is enabled."""
        request = self.create_request()
        response = self.middleware(request)

        # Check HSTS header
        self.assertIn("Strict-Transport-Security", response)
        hsts = response["Strict-Transport-Security"]
        self.assertIn("max-age=31536000", hsts)
        self.assertIn("includeSubDomains", hsts)
        self.assertIn("preload", hsts)

    @override_settings(SECURE_SSL_REDIRECT=False)
    def test_no_hsts_headers_without_ssl(self):
        """Test HSTS headers are not set when SSL is disabled."""
        request = self.create_request()
        response = self.middleware(request)

        # Should not have HSTS header
        self.assertNotIn("Strict-Transport-Security", response)

    def test_cached_headers_performance(self):
        """Test that headers are cached for performance."""
        # Clear cache
        SecurityHeadersMiddleware._cached_headers = None

        request1 = self.create_request()
        request2 = self.create_request()

        with patch.object(
            SecurityHeadersMiddleware, "_compute_headers"
        ) as mock_compute:
            mock_compute.return_value = {"Test-Header": "value"}

            # First request should compute headers
            self.middleware(request1)
            self.assertEqual(mock_compute.call_count, 1)

            # Second request should use cached headers
            self.middleware(request2)
            self.assertEqual(mock_compute.call_count, 1)  # Still 1, not called again

    @override_settings(DEBUG=True)
    def test_cache_invalidation_on_debug_change(self):
        """Test that cached headers are invalidated when DEBUG changes."""
        # Set initial cache with DEBUG=True
        SecurityHeadersMiddleware._cached_headers = {"Test-Header": "debug-value"}
        SecurityHeadersMiddleware._cached_debug_mode = True

        with override_settings(DEBUG=False):
            with patch.object(
                SecurityHeadersMiddleware, "_compute_headers"
            ) as mock_compute:
                mock_compute.return_value = {"Test-Header": "production-value"}

                request = self.create_request()
                response = self.middleware(request)

                # Should recompute headers due to debug mode change
                mock_compute.assert_called_once()

    def test_existing_x_frame_options_preserved(self):
        """Test that existing X-Frame-Options header is preserved."""
        # Mock response with existing X-Frame-Options
        response_with_header = HttpResponse("OK")
        response_with_header["X-Frame-Options"] = "SAMEORIGIN"
        self.get_response.return_value = response_with_header

        request = self.create_request()
        response = self.middleware(request)

        # Should preserve existing header
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")


class AdminIPAllowlistMiddlewareTests(MiddlewareTestBase):
    """Tests for AdminIPAllowlistMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = AdminIPAllowlistMiddleware(self.get_response)

    def test_non_admin_url_allowed(self):
        """Test that non-admin URLs are not checked."""
        request = self.create_request("/regular-page/")
        response = self.middleware(request)

        # Should pass through normally
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")

    @override_settings(ADMIN_IP_ALLOWLIST=[])
    def test_admin_url_no_allowlist(self):
        """Test admin access when no allowlist is configured."""
        request = self.create_request("/admin/")
        response = self.middleware(request)

        # Should allow access
        self.assertEqual(response.status_code, 200)

    @override_settings(ADMIN_IP_ALLOWLIST=["192.168.1.1", "10.0.0.0/8"])
    def test_admin_url_ip_allowed(self):
        """Test admin access from allowed IP."""
        request = self.create_request("/admin/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        response = self.middleware(request)

        # Should allow access
        self.assertEqual(response.status_code, 200)

    @override_settings(ADMIN_IP_ALLOWLIST=["192.168.1.1"])
    def test_admin_url_ip_denied(self):
        """Test admin access from denied IP."""
        request = self.create_request("/admin/")
        request.META["REMOTE_ADDR"] = "192.168.1.2"
        response = self.middleware(request)

        # Should deny access
        self.assertIsInstance(response, HttpResponseForbidden)
        self.assertIn("Access denied", response.content.decode())

    @override_settings(ADMIN_IP_ALLOWLIST=["10.0.0.0/8"])
    def test_admin_url_cidr_allowed(self):
        """Test admin access from IP in CIDR range."""
        request = self.create_request("/admin/")
        request.META["REMOTE_ADDR"] = "10.0.1.100"
        response = self.middleware(request)

        # Should allow access
        self.assertEqual(response.status_code, 200)

    @override_settings(ADMIN_IP_ALLOWLIST=["10.0.0.0/8"])
    def test_admin_url_cidr_denied(self):
        """Test admin access from IP outside CIDR range."""
        request = self.create_request("/admin/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        response = self.middleware(request)

        # Should deny access
        self.assertIsInstance(response, HttpResponseForbidden)

    @override_settings(ADMIN_IP_ALLOWLIST=["192.168.1.1"])
    def test_x_forwarded_for_header(self):
        """Test IP extraction from X-Forwarded-For header."""
        request = self.create_request("/admin/")
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.1, 192.168.1.2"
        request.META["REMOTE_ADDR"] = "192.168.1.3"
        response = self.middleware(request)

        # Should use first IP from X-Forwarded-For
        self.assertEqual(response.status_code, 200)

    @override_settings(ADMIN_IP_ALLOWLIST=["invalid-ip", "192.168.1.1"])
    def test_invalid_ip_in_allowlist(self):
        """Test handling of invalid IP addresses in allowlist."""
        request = self.create_request("/admin/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        response = self.middleware(request)

        # Should still allow valid IP despite invalid entry
        self.assertEqual(response.status_code, 200)

    def test_invalid_client_ip(self):
        """Test handling of invalid client IP."""
        request = self.create_request("/admin/")
        request.META["REMOTE_ADDR"] = "invalid-ip"

        with override_settings(ADMIN_IP_ALLOWLIST=["192.168.1.1"]):
            response = self.middleware(request)

        # Should deny access for invalid client IP
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_ipv6_support(self):
        """Test IPv6 address support."""
        request = self.create_request("/admin/")
        request.META["REMOTE_ADDR"] = "::1"

        with override_settings(ADMIN_IP_ALLOWLIST=["::1"]):
            response = self.middleware(request)

        # Should allow IPv6 loopback
        self.assertEqual(response.status_code, 200)

    def test_ipv6_cidr_support(self):
        """Test IPv6 CIDR range support."""
        request = self.create_request("/admin/")
        request.META["REMOTE_ADDR"] = "2001:db8::1"

        with override_settings(ADMIN_IP_ALLOWLIST=["2001:db8::/32"]):
            response = self.middleware(request)

        # Should allow IPv6 in CIDR range
        self.assertEqual(response.status_code, 200)


class DemoModeMiddlewareTests(MiddlewareTestBase):
    """Tests for DemoModeMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = DemoModeMiddleware(self.get_response)

    @override_settings(DEMO_MODE=False)
    def test_demo_mode_disabled(self):
        """Test middleware does nothing when demo mode is disabled."""
        html_response = HttpResponse(
            "<!DOCTYPE html><html><head><title>Test</title></head><body>Content</body></html>",
            content_type="text/html",
        )
        self.get_response.return_value = html_response

        request = self.create_request()
        response = self.middleware(request)

        # Should not modify response
        self.assertNotIn("demo-banner", response.content.decode())

    @override_settings(DEMO_MODE=True)
    def test_demo_mode_html_injection(self):
        """Test demo banner injection in HTML responses."""
        html_response = HttpResponse(
            "<!DOCTYPE html><html><head><title>Test</title></head><body>Content</body></html>",
            content_type="text/html",
        )
        self.get_response.return_value = html_response

        request = self.create_request()
        response = self.middleware(request)

        content = response.content.decode()
        # Should inject demo banner
        self.assertIn("demo-banner", content)
        self.assertIn("DEMO MODE", content)
        self.assertIn("demonstration environment", content)
        self.assertIn("body { margin-top: 40px !important; }", content)

    @override_settings(DEMO_MODE=True)
    def test_demo_mode_non_html_response(self):
        """Test demo mode doesn't affect non-HTML responses."""
        json_response = JsonResponse({"message": "test"})
        self.get_response.return_value = json_response

        request = self.create_request()
        response = self.middleware(request)

        # Should not modify JSON response
        content = response.content.decode()
        self.assertNotIn("demo-banner", content)

    @override_settings(DEMO_MODE=True)
    def test_demo_mode_error_response(self):
        """Test demo mode doesn't affect error responses."""
        error_response = HttpResponse(
            "<!DOCTYPE html><html><body>Error</body></html>",
            content_type="text/html",
            status=404,
        )
        self.get_response.return_value = error_response

        request = self.create_request()
        response = self.middleware(request)

        # Should not modify error response
        self.assertNotIn("demo-banner", response.content.decode())

    @override_settings(DEMO_MODE=True)
    def test_demo_mode_invalid_html(self):
        """Test demo mode handles invalid HTML gracefully."""
        invalid_html = HttpResponse("Not valid HTML", content_type="text/html")
        self.get_response.return_value = invalid_html

        request = self.create_request()
        response = self.middleware(request)

        # Should not modify invalid HTML
        self.assertEqual(response.content, b"Not valid HTML")

    @override_settings(DEMO_MODE=True)
    def test_demo_mode_content_length_update(self):
        """Test demo mode updates Content-Length header."""
        html_response = HttpResponse(
            "<!DOCTYPE html><html><body>Test</body></html>", content_type="text/html"
        )
        self.get_response.return_value = html_response

        request = self.create_request()
        response = self.middleware(request)

        # Content-Length should be updated to reflect added content
        expected_length = len(response.content)
        self.assertEqual(response["Content-Length"], str(expected_length))

    @override_settings(DEMO_MODE=True)
    def test_demo_mode_encoding_error(self):
        """Test demo mode handles encoding errors gracefully."""
        # Create response with invalid encoding
        html_response = HttpResponse(
            b"<!DOCTYPE html><html><body>\xff\xfe</body></html>",  # Invalid UTF-8
            content_type="text/html",
        )
        self.get_response.return_value = html_response

        request = self.create_request()
        response = self.middleware(request)

        # Should not raise exception and return original response
        self.assertEqual(response.status_code, 200)


class PerformanceMonitoringMiddlewareTests(MiddlewareTestBase):
    """Tests for PerformanceMonitoringMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = PerformanceMonitoringMiddleware(self.get_response)

    def test_performance_headers_added(self):
        """Test that performance headers are added to response."""
        request = self.create_request()

        with patch("time.time", side_effect=[0.0, 0.5]):  # 500ms duration
            response = self.middleware(request)

        # Check performance headers
        self.assertIn("X-Response-Time", response)
        self.assertEqual(response["X-Response-Time"], "0.500")
        self.assertIn("X-Database-Queries", response)
        self.assertIn("X-Cache-Status", response)

    def test_slow_request_logging(self):
        """Test logging of slow requests."""
        request = self.create_request("/slow-page/")

        with (
            patch(
                "apps.core.middleware_performance.time.time",
                side_effect=[0.0, 2.0, 2.0, 2.0],
            ),
            patch("apps.core.middleware_performance.logger") as mock_logger,
        ):

            response = self.middleware(request)

            # Should log slow request
            mock_logger.warning.assert_called_once()
            log_call = mock_logger.warning.call_args[0][0]
            self.assertIn("Slow request", log_call)
            self.assertIn("/slow-page/", log_call)
            self.assertIn("2.00s", log_call)

    def test_cache_performance_tracking(self):
        """Test performance tracking in cache."""
        request = self.create_request("/tracked-page/")

        with (
            patch(
                "apps.core.middleware_performance.time.time",
                side_effect=[0.0, 0.6, 0.6, 0.6, 0.6, 0.6],
            ),
            patch("apps.core.middleware_performance.cache.get") as mock_cache_get,
            patch("apps.core.middleware_performance.cache.set") as mock_cache_set,
        ):

            # Mock cache.get to return default value
            mock_cache_get.return_value = {"count": 0, "total_time": 0}

            response = self.middleware(request)

            # Verify cache operations were called
            cache_key = "perf:slow:/tracked-page/"
            mock_cache_get.assert_called_with(cache_key, {"count": 0, "total_time": 0})

            # Verify cache.set was called with updated data
            expected_data = {"count": 1, "total_time": 0.6, "avg_time": 0.6}
            mock_cache_set.assert_called_with(cache_key, expected_data, timeout=3600)

    def test_no_start_time_handling(self):
        """Test handling when request has no start time."""
        request = self.create_request()
        # Don't call process_request, so no _start_time is set

        response = self.middleware.process_response(request, HttpResponse("OK"))

        # Should not add performance headers
        self.assertNotIn("X-Response-Time", response)

    @override_settings(DEBUG=True)
    def test_slow_query_logging_debug(self):
        """Test slow query logging in debug mode."""
        request = self.create_request()

        # Mock slow queries
        slow_query = {"sql": "SELECT * FROM slow_table", "time": "0.15"}
        fast_query = {"sql": "SELECT 1", "time": "0.01"}
        mock_queries = [fast_query, slow_query]

        # Mock the Django connection module entirely
        # We need to simulate the queries growing during the request
        initial_queries = []  # Empty at start
        final_queries = mock_queries  # Full list at end

        mock_connection = Mock()

        with (
            patch("time.time", side_effect=[0.0, 2.0, 2.0, 2.0, 2.0, 2.0]),
            patch("apps.core.middleware_performance.connection", mock_connection),
            patch("apps.core.middleware_performance.logger") as mock_logger,
        ):

            # First set up empty queries for process_request
            mock_connection.queries = initial_queries
            self.middleware.process_request(request)

            # Then set up full queries for process_response
            mock_connection.queries = final_queries
            response = self.middleware.process_response(request, HttpResponse("OK"))

            # Should log slow request and slow queries
            self.assertEqual(mock_logger.warning.call_count, 2)

            # Check both warnings were logged
            warning_messages = [
                str(call[0][0]) for call in mock_logger.warning.call_args_list
            ]

            # First warning should be for slow request
            self.assertTrue(
                any(
                    "Slow request" in msg and "2.00s with 2 queries" in msg
                    for msg in warning_messages
                ),
                "Slow request warning should be logged",
            )

            # Second warning should be for slow queries (only the 0.15s query)
            self.assertTrue(
                any(
                    "Slow queries" in msg and "SELECT * FROM slow_table" in msg
                    for msg in warning_messages
                ),
                "Slow queries warning should be logged",
            )

    def test_multiple_requests_tracking(self):
        """Test tracking multiple requests to same path."""
        path = "/api/test/"

        with (
            patch("apps.core.middleware_performance.time.time") as mock_time,
            patch("apps.core.middleware_performance.cache.get") as mock_cache_get,
            patch("apps.core.middleware_performance.cache.set") as mock_cache_set,
        ):

            # Set up cache mock return values
            cache_values = [
                {"count": 0, "total_time": 0},  # First request initial
                {
                    "count": 1,
                    "total_time": 0.7,
                    "avg_time": 0.7,
                },  # Second request initial
            ]
            mock_cache_get.side_effect = cache_values

            # First request
            mock_time.side_effect = [0.0, 0.7, 0.7, 0.7, 0.7]
            request1 = self.create_request(path)
            self.middleware(request1)

            # Second request
            mock_time.side_effect = [1.0, 1.8, 1.8, 1.8, 1.8]
            request2 = self.create_request(path)
            self.middleware(request2)

            # Verify cache operations
            cache_key = f"perf:slow:{path}"
            self.assertEqual(mock_cache_get.call_count, 2)
            self.assertEqual(mock_cache_set.call_count, 2)

            # Check first cache set call
            first_call = mock_cache_set.call_args_list[0]
            self.assertEqual(first_call[0][0], cache_key)
            self.assertEqual(first_call[0][1]["count"], 1)
            self.assertAlmostEqual(first_call[0][1]["total_time"], 0.7, places=2)

            # Check second cache set call
            second_call = mock_cache_set.call_args_list[1]
            self.assertEqual(second_call[0][0], cache_key)
            self.assertEqual(second_call[0][1]["count"], 2)
            self.assertAlmostEqual(
                second_call[0][1]["total_time"], 1.5, places=2
            )  # 0.7 + 0.8
            self.assertAlmostEqual(second_call[0][1]["avg_time"], 0.75, places=2)


class QueryCountLimitMiddlewareTests(MiddlewareTestBase):
    """Tests for QueryCountLimitMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = QueryCountLimitMiddleware(self.get_response)

    def test_normal_query_count(self):
        """Test normal query count within limits."""
        request = self.create_request()

        # Mock normal query count
        mock_connection = Mock()
        mock_connection.queries = [{"sql": "SELECT 1"} for _ in range(5)]

        with patch("apps.core.middleware_performance.connection", mock_connection):
            request._query_count_start = 0
            response = self.middleware.process_response(request, HttpResponse("OK"))

        # Should not interfere
        self.assertEqual(response.status_code, 200)

    def test_excessive_query_count_production(self):
        """Test excessive query count in production."""
        request = self.create_request()

        # Mock excessive queries (more than MAX_QUERIES)
        excessive_queries = [{"sql": "SELECT 1"} for _ in range(20)]
        mock_connection = Mock()
        mock_connection.queries = excessive_queries

        with (
            patch("apps.core.middleware_performance.connection", mock_connection),
            patch("apps.core.middleware_performance.logger") as mock_logger,
            override_settings(DEBUG=False),
        ):

            request._query_count_start = 0
            response = self.middleware.process_response(request, HttpResponse("OK"))

            # Should log error but not return error response
            mock_logger.error.assert_called_once()
            self.assertEqual(response.status_code, 200)

    @override_settings(DEBUG=True)
    def test_excessive_query_count_debug(self):
        """Test excessive query count in debug mode."""
        request = self.create_request("/debug-page/")

        # Mock excessive queries
        excessive_queries = [{"sql": "SELECT 1"} for _ in range(20)]
        mock_connection = Mock()
        mock_connection.queries = excessive_queries

        with (
            patch("apps.core.middleware_performance.connection", mock_connection),
            patch("apps.core.middleware_performance.logger") as mock_logger,
        ):

            request._query_count_start = 0
            response = self.middleware.process_response(request, HttpResponse("OK"))

            # Should return error response in debug mode
            self.assertIsInstance(response, JsonResponse)
            self.assertEqual(response.status_code, 500)

            # Check error response content
            data = json.loads(response.content)
            self.assertEqual(data["error"], "Query limit exceeded")
            self.assertEqual(data["query_count"], 20)
            self.assertEqual(data["limit"], 15)
            self.assertEqual(data["path"], "/debug-page/")

    def test_no_start_count_handling(self):
        """Test handling when request has no query count start."""
        request = self.create_request()
        # Don't set _query_count_start

        response = self.middleware.process_response(request, HttpResponse("OK"))

        # Should not interfere
        self.assertEqual(response.status_code, 200)

    def test_query_limit_boundary(self):
        """Test query count at exact limit."""
        request = self.create_request()

        # Mock exactly MAX_QUERIES queries
        exact_limit_queries = [{"sql": "SELECT 1"} for _ in range(15)]
        mock_connection = Mock()
        mock_connection.queries = exact_limit_queries

        with patch("apps.core.middleware_performance.connection", mock_connection):
            request._query_count_start = 0
            response = self.middleware.process_response(request, HttpResponse("OK"))

        # Should not trigger limit
        self.assertEqual(response.status_code, 200)


class CacheHitRateMiddlewareTests(MiddlewareTestBase):
    """Tests for CacheHitRateMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = CacheHitRateMiddleware(self.get_response)

    def test_cache_hit_tracking(self):
        """Test cache hit tracking."""
        response = HttpResponse("OK")
        response["X-Cache"] = "HIT"
        self.get_response.return_value = response

        request = self.create_request()
        response = self.middleware(request)

        # Check hit rate stats
        stats = cache.get("cache:stats:global")
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 0)
        self.assertEqual(stats["hit_rate"], 1.0)

    def test_cache_miss_tracking(self):
        """Test cache miss tracking."""
        response = HttpResponse("OK")
        response["X-Cache"] = "MISS"
        self.get_response.return_value = response

        request = self.create_request()
        response = self.middleware(request)

        # Check hit rate stats
        stats = cache.get("cache:stats:global")
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], 0.0)

    def test_no_cache_header_tracking(self):
        """Test tracking when no X-Cache header is present."""
        response = HttpResponse("OK")
        self.get_response.return_value = response

        request = self.create_request()
        response = self.middleware(request)

        # Should count as miss
        stats = cache.get("cache:stats:global")
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 1)

    def test_mixed_hit_miss_stats(self):
        """Test mixed hit/miss statistics."""
        # First request - hit
        response1 = HttpResponse("OK")
        response1["X-Cache"] = "HIT"
        self.get_response.return_value = response1

        request1 = self.create_request()
        self.middleware(request1)

        # Second request - miss
        response2 = HttpResponse("OK")
        response2["X-Cache"] = "MISS"
        self.get_response.return_value = response2

        request2 = self.create_request()
        self.middleware(request2)

        # Check combined stats
        stats = cache.get("cache:stats:global")
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_rate"], 0.5)

    @override_settings(DEBUG=True)
    def test_hit_rate_header_debug(self):
        """Test hit rate header in debug mode."""
        # Set up some initial stats
        cache.set("cache:stats:global", {"hits": 3, "misses": 1, "hit_rate": 0.75})

        response = HttpResponse("OK")
        response["X-Cache"] = "HIT"
        self.get_response.return_value = response

        request = self.create_request()
        response = self.middleware(request)

        # Should add hit rate header in debug mode
        self.assertIn("X-Cache-Hit-Rate", response)
        # Hit rate should be updated: 4 hits, 1 miss = 80%
        self.assertEqual(response["X-Cache-Hit-Rate"], "80.00%")

    @override_settings(DEBUG=False)
    def test_no_hit_rate_header_production(self):
        """Test no hit rate header in production."""
        response = HttpResponse("OK")
        self.get_response.return_value = response

        request = self.create_request()
        response = self.middleware(request)

        # Should not add hit rate header in production
        self.assertNotIn("X-Cache-Hit-Rate", response)

    def test_non_http_response_handling(self):
        """Test handling of non-HTTP response objects."""
        # Mock response without get method
        mock_response = Mock()
        del mock_response.get  # Remove get method
        self.get_response.return_value = mock_response

        request = self.create_request()
        response = self.middleware(request)

        # Should return original response without modification
        self.assertEqual(response, mock_response)


class DatabaseConnectionPoolMiddlewareTests(MiddlewareTestBase):
    """Tests for DatabaseConnectionPoolMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = DatabaseConnectionPoolMiddleware(self.get_response)

    @patch("apps.core.middleware_performance.connection")
    def test_connection_ensure(self, mock_connection):
        """Test connection is ensured on request start."""
        request = self.create_request()

        # Call process_request directly since that's where the logic is
        self.middleware.process_request(request)

        # Should ensure connection
        mock_connection.ensure_connection.assert_called_once()

    @patch("apps.core.middleware_performance.connection")
    def test_connection_recovery(self, mock_connection):
        """Test connection recovery on failure."""
        # First ensure_connection fails, then succeeds
        mock_connection.ensure_connection.side_effect = [
            Exception("Connection lost"),
            None,
        ]

        request = self.create_request()
        self.middleware.process_request(request)

        # Should close and retry connection
        mock_connection.close.assert_called_once()
        self.assertEqual(mock_connection.ensure_connection.call_count, 2)

    @patch("apps.core.middleware_performance.connection")
    def test_long_request_connection_cleanup(self, mock_connection):
        """Test connection cleanup for long requests."""
        request = self.create_request()

        # Mock long request duration
        with patch(
            "apps.core.middleware_performance.time.time", return_value=6.0
        ):  # Current time is 6.0
            request._start_time = 0.0  # Start time was 0.0, so duration = 6.0 seconds
            response = self.middleware.process_response(request, HttpResponse("OK"))

        # Should close connection for long request
        mock_connection.close.assert_called()

    @patch("apps.core.middleware_performance.connection")
    def test_short_request_no_cleanup(self, mock_connection):
        """Test no connection cleanup for short requests."""
        request = self.create_request()

        # Mock short request duration
        with patch("time.time", side_effect=[0.0, 1.0]):  # 1 second request
            request._start_time = 0.0
            response = self.middleware.process_response(request, HttpResponse("OK"))

        # Should not close connection for short request
        mock_connection.close.assert_not_called()

    @patch("apps.core.middleware_performance.connection")
    def test_no_start_time_no_cleanup(self, mock_connection):
        """Test no cleanup when request has no start time."""
        request = self.create_request()
        # Don't set _start_time

        response = self.middleware.process_response(request, HttpResponse("OK"))

        # Should not close connection
        mock_connection.close.assert_not_called()


class RequestThrottlingMiddlewareTests(MiddlewareTestBase):
    """Tests for RequestThrottlingMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = RequestThrottlingMiddleware(self.get_response)

    def test_staff_user_bypass(self):
        """Test staff users bypass throttling."""
        request = self.create_request("/api/test/")
        request.user = self.staff_user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Make many requests quickly
        for _ in range(150):
            response = self.middleware(request)
            if response is not None:  # Middleware intercepted
                break
        else:
            response = self.get_response(request)

        # Should not be throttled
        self.assertEqual(response.status_code, 200)

    def test_api_request_throttling(self):
        """Test API request throttling."""
        request = self.create_request("/api/test/")
        request.user = self.user  # Not staff
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Make requests up to limit
        for i in range(100):
            response = self.middleware.process_request(request)
            if response is not None:
                break

        # Should allow up to 100 requests
        self.assertIsNone(response)

        # 101st request should be throttled
        response = self.middleware.process_request(request)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 429)

    def test_regular_page_throttling(self):
        """Test regular page throttling."""
        request = self.create_request("/regular-page/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Make requests up to limit (200 for regular pages)
        response = None
        for i in range(200):
            response = self.middleware.process_request(request)
            if response is not None:
                break

        # Should allow up to 200 requests
        self.assertIsNone(response)

        # 201st request should be throttled
        response = self.middleware.process_request(request)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 429)

    def test_x_forwarded_for_ip_extraction(self):
        """Test IP extraction from X-Forwarded-For header."""
        request = self.create_request("/api/test/")
        request.user = self.user
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.1, 192.168.1.2"
        request.META["REMOTE_ADDR"] = "192.168.1.3"

        # Should use first IP from X-Forwarded-For
        throttle_key = "throttle:192.168.1.1"

        # Set high request count to trigger throttle
        cache.set(throttle_key, 150)

        response = self.middleware.process_request(request)
        self.assertIsInstance(response, JsonResponse)

    def test_different_ips_separate_limits(self):
        """Test different IPs have separate throttle limits."""
        request1 = self.create_request("/api/test/")
        request1.user = self.user
        request1.META["REMOTE_ADDR"] = "192.168.1.1"

        request2 = self.create_request("/api/test/")
        request2.user = self.user
        request2.META["REMOTE_ADDR"] = "192.168.1.2"

        # Exhaust limit for first IP
        cache.set("throttle:192.168.1.1", 100)

        # First IP should be throttled
        response1 = self.middleware.process_request(request1)
        self.assertIsInstance(response1, JsonResponse)

        # Second IP should not be throttled
        response2 = self.middleware.process_request(request2)
        self.assertIsNone(response2)

    def test_throttle_counter_increment(self):
        """Test throttle counter is properly incremented."""
        request = self.create_request("/api/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Make first request
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

        # Check counter was incremented
        count = cache.get("throttle:192.168.1.1")
        self.assertEqual(count, 1)

        # Make second request
        response = self.middleware.process_request(request)
        self.assertIsNone(response)

        # Check counter was incremented again
        count = cache.get("throttle:192.168.1.1")
        self.assertEqual(count, 2)

    def test_throttle_response_content(self):
        """Test throttle response content."""
        request = self.create_request("/api/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Set high request count to trigger throttle
        cache.set("throttle:192.168.1.1", 150)

        response = self.middleware.process_request(request)

        # Check response content
        data = json.loads(response.content)
        self.assertEqual(data["error"], "Rate limit exceeded")
        self.assertEqual(data["retry_after"], 60)

    def test_no_user_attribute(self):
        """Test handling when request has no user attribute."""
        request = self.create_request("/api/test/")
        # Don't set user attribute (AuthenticationMiddleware hasn't run)
        del request.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Should proceed with throttling check
        response = self.middleware.process_request(request)
        self.assertIsNone(response)  # Should not be throttled on first request


class CompressionMiddlewareTests(MiddlewareTestBase):
    """Tests for CompressionMiddleware."""

    def setUp(self):
        super().setUp()
        self.middleware = CompressionMiddleware(self.get_response)

    def test_small_response_not_compressed(self):
        """Test small responses are not compressed."""
        small_content = "x" * 500  # Less than MIN_SIZE
        response = HttpResponse(small_content, content_type="text/html")
        self.get_response.return_value = response

        request = self.create_request()
        request.META["HTTP_ACCEPT_ENCODING"] = "gzip, br"

        response = self.middleware(request)

        # Should not be compressed
        self.assertNotIn("Content-Encoding", response)

    def test_non_compressible_content_type(self):
        """Test non-compressible content types are not compressed."""
        large_content = "x" * 2000
        response = HttpResponse(large_content, content_type="image/jpeg")
        self.get_response.return_value = response

        request = self.create_request()
        request.META["HTTP_ACCEPT_ENCODING"] = "gzip, br"

        response = self.middleware(request)

        # Should not be compressed
        self.assertNotIn("Content-Encoding", response)

    def test_already_compressed_response(self):
        """Test already compressed responses are left alone."""
        large_content = "x" * 2000
        response = HttpResponse(large_content, content_type="text/html")
        response["Content-Encoding"] = "gzip"
        self.get_response.return_value = response

        request = self.create_request()
        request.META["HTTP_ACCEPT_ENCODING"] = "gzip, br"

        response = self.middleware(request)

        # Should not modify existing compression
        self.assertEqual(response["Content-Encoding"], "gzip")

    def test_brotli_compression(self):
        """Test Brotli compression when supported."""
        large_content = "x" * 2000
        compressed_content = b"compressed_content"

        response = HttpResponse(large_content, content_type="text/html")
        self.get_response.return_value = response

        # Mock Brotli compression
        with patch("apps.core.middleware_performance.HAS_BROTLI", True):
            mock_brotli = Mock()
            mock_brotli.compress = Mock(return_value=compressed_content)

            with patch.dict("sys.modules", {"brotli": mock_brotli}):

                request = self.create_request()
                request.META["HTTP_ACCEPT_ENCODING"] = "gzip, br"

                # Reload the module to pick up the mocked brotli
                import importlib

                import apps.core.middleware_performance

                importlib.reload(apps.core.middleware_performance)

                # Create new middleware instance with reloaded module
                middleware = apps.core.middleware_performance.CompressionMiddleware(
                    self.get_response
                )

                response = middleware(request)

                # Should use Brotli compression
                mock_brotli.compress.assert_called_once_with(
                    large_content.encode(), quality=4
                )
                self.assertEqual(response["Content-Encoding"], "br")
                self.assertEqual(response["Vary"], "Accept-Encoding")
                self.assertNotIn("Content-Length", response)

    def test_brotli_compression_no_benefit(self):
        """Test Brotli compression when it doesn't reduce size."""
        large_content = "x" * 2000
        # Mock compression that doesn't reduce size
        with patch("apps.core.middleware_performance.HAS_BROTLI", True):
            mock_brotli = Mock()
            mock_brotli.compress = Mock(
                return_value=b"x" * 3000
            )  # Larger than original

            with patch.dict("sys.modules", {"brotli": mock_brotli}):

                response = HttpResponse(large_content, content_type="text/html")
                self.get_response.return_value = response

                request = self.create_request()
                request.META["HTTP_ACCEPT_ENCODING"] = "br"

                # Reload module and create new middleware
                import importlib

                import apps.core.middleware_performance

                importlib.reload(apps.core.middleware_performance)

                middleware = apps.core.middleware_performance.CompressionMiddleware(
                    self.get_response
                )
                response = middleware(request)

                # Should not use compression if it doesn't help
                self.assertNotIn("Content-Encoding", response)

    @patch("apps.core.middleware_performance.HAS_BROTLI", False)
    def test_no_brotli_support(self):
        """Test handling when Brotli is not supported."""
        large_content = "x" * 2000
        response = HttpResponse(large_content, content_type="text/html")
        self.get_response.return_value = response

        request = self.create_request()
        request.META["HTTP_ACCEPT_ENCODING"] = "br"

        response = self.middleware(request)

        # Should not use Brotli compression
        self.assertNotIn("Content-Encoding", response)

    def test_brotli_compression_exception(self):
        """Test Brotli compression exception handling."""
        large_content = "x" * 2000
        response = HttpResponse(large_content, content_type="text/html")
        self.get_response.return_value = response

        # Mock Brotli compression failure
        with patch("apps.core.middleware_performance.HAS_BROTLI", True):
            mock_brotli = Mock()
            mock_brotli.compress = Mock(side_effect=Exception("Compression failed"))

            with patch.dict("sys.modules", {"brotli": mock_brotli}):

                request = self.create_request()
                request.META["HTTP_ACCEPT_ENCODING"] = "br"

                # Reload module and create new middleware
                import importlib

                import apps.core.middleware_performance

                importlib.reload(apps.core.middleware_performance)

                middleware = apps.core.middleware_performance.CompressionMiddleware(
                    self.get_response
                )
                response = middleware(request)

                # Should handle exception gracefully
                self.assertNotIn("Content-Encoding", response)

    def test_compressible_content_types(self):
        """Test various compressible content types."""
        compressible_types = [
            "text/html",
            "text/css",
            "text/javascript",
            "application/json",
            "application/javascript",
        ]

        for content_type in compressible_types:
            with self.subTest(content_type=content_type):
                large_content = "x" * 2000
                response = HttpResponse(large_content, content_type=content_type)

                with patch("apps.core.middleware_performance.HAS_BROTLI", True):
                    mock_brotli = Mock()
                    mock_brotli.compress = Mock(return_value=b"compressed")

                    with patch.dict("sys.modules", {"brotli": mock_brotli}):
                        self.get_response.return_value = response

                        request = self.create_request()
                        request.META["HTTP_ACCEPT_ENCODING"] = "br"

                        # Reload module and create new middleware
                        import importlib

                        import apps.core.middleware_performance

                        importlib.reload(apps.core.middleware_performance)

                        middleware = (
                            apps.core.middleware_performance.CompressionMiddleware(
                                self.get_response
                            )
                        )
                        response = middleware(request)

                        # Should attempt compression
                        mock_brotli.compress.assert_called_once()

    def test_no_accept_encoding(self):
        """Test handling when client doesn't send Accept-Encoding."""
        large_content = "x" * 2000
        response = HttpResponse(large_content, content_type="text/html")
        self.get_response.return_value = response

        request = self.create_request()
        # No Accept-Encoding header

        response = self.middleware(request)

        # Should not compress
        self.assertNotIn("Content-Encoding", response)


class MiddlewareOrderingTests(MiddlewareTestBase):
    """Tests for middleware ordering and interaction."""

    def test_performance_monitoring_order(self):
        """Test PerformanceMonitoringMiddleware timing accuracy."""
        middleware1 = PerformanceMonitoringMiddleware(self.get_response)
        middleware2 = QueryCountLimitMiddleware(self.get_response)

        request = self.create_request()

        # Process request through both middlewares
        middleware1.process_request(request)
        middleware2.process_request(request)

        with patch("time.time", side_effect=[1.0]):
            # Process response back through middlewares (reverse order)
            response = HttpResponse("OK")
            response = middleware2.process_response(request, response)
            response = middleware1.process_response(request, response)

        # Should have performance headers from first middleware
        self.assertIn("X-Response-Time", response)

    def test_throttling_before_processing(self):
        """Test throttling middleware blocks before expensive processing."""
        throttling_middleware = RequestThrottlingMiddleware(
            lambda req: HttpResponse("Expensive")
        )

        request = self.create_request("/api/test/")
        request.user = self.user
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Set high request count to trigger throttle
        cache.set("throttle:192.168.1.1", 150)

        response = throttling_middleware(request)

        # Should return throttle response, not expensive processing result
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("Expensive", response.content.decode())


class MiddlewareErrorHandlingTests(MiddlewareTestBase):
    """Tests for middleware error handling and recovery."""

    @pytest.mark.skip(reason="Database connection issues in CI")
    def test_security_middleware_error_recovery(self):
        """Test SecurityHeadersMiddleware handles errors gracefully."""
        middleware = SecurityHeadersMiddleware(self.get_response)

        # Mock settings access to raise exception
        with patch(
            "apps.core.middleware.settings.DEBUG",
            side_effect=Exception("Settings error"),
        ):
            request = self.create_request()

            # Should not raise exception
            try:
                response = middleware(request)
                self.assertEqual(response.status_code, 200)
            except Exception:
                self.fail("Middleware should handle settings errors gracefully")

    @pytest.mark.skip(reason="Database connection issues in CI")
    def test_performance_middleware_timing_error(self):
        """Test PerformanceMonitoringMiddleware handles timing errors."""
        middleware = PerformanceMonitoringMiddleware(self.get_response)

        request = self.create_request()

        # Process request normally
        middleware.process_request(request)

        # Mock time.time to raise exception
        with patch("time.time", side_effect=Exception("Time error")):
            response = HttpResponse("OK")

            # Should not raise exception
            try:
                response = middleware.process_response(request, response)
                self.assertEqual(response.status_code, 200)
            except Exception:
                self.fail("Middleware should handle timing errors gracefully")

    def test_cache_middleware_cache_error(self):
        """Test CacheHitRateMiddleware handles cache errors."""
        middleware = CacheHitRateMiddleware(self.get_response)

        request = self.create_request()
        response = HttpResponse("OK")

        # Mock cache operations to raise exception
        with (
            patch("django.core.cache.cache.get", side_effect=Exception("Cache error")),
            patch("django.core.cache.cache.set", side_effect=Exception("Cache error")),
        ):

            # Should not raise exception
            try:
                response = middleware(request)
                self.assertEqual(response.status_code, 200)
            except Exception:
                self.fail("Middleware should handle cache errors gracefully")

    def test_connection_middleware_db_error(self):
        """Test DatabaseConnectionPoolMiddleware handles database errors."""
        middleware = DatabaseConnectionPoolMiddleware(self.get_response)

        request = self.create_request()

        # Mock connection operations to raise exception
        with patch(
            "django.db.connection.ensure_connection", side_effect=Exception("DB error")
        ):

            # Should not raise exception
            try:
                response = middleware(request)
                self.assertEqual(response.status_code, 200)
            except Exception:
                self.fail("Middleware should handle database errors gracefully")

    def test_compression_middleware_compression_error(self):
        """Test CompressionMiddleware handles compression errors gracefully."""
        middleware = CompressionMiddleware(self.get_response)

        large_content = "x" * 2000
        response = HttpResponse(large_content, content_type="text/html")
        self.get_response.return_value = response

        request = self.create_request()
        request.META["HTTP_ACCEPT_ENCODING"] = "br"

        # Mock compression to raise exception
        with patch("apps.core.middleware_performance.HAS_BROTLI", True):
            mock_brotli = Mock()
            mock_brotli.compress = Mock(side_effect=Exception("Compression failed"))

            with patch.dict("sys.modules", {"brotli": mock_brotli}):
                # Reload module and create new middleware
                import importlib

                import apps.core.middleware_performance

                importlib.reload(apps.core.middleware_performance)

                middleware = apps.core.middleware_performance.CompressionMiddleware(
                    self.get_response
                )

                # Should not raise exception
                try:
                    response = middleware(request)
                    self.assertEqual(response.status_code, 200)
                    # Should not have compression headers due to error
                    self.assertNotIn("Content-Encoding", response)
                except Exception:
                    self.fail("Middleware should handle compression errors gracefully")
