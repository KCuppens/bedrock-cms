"""Simple passing tests for analytics utils"""

from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from apps.analytics.utils import (
    calculate_session_duration,
    get_client_ip,
    get_geo_data,
    parse_user_agent,
    sanitize_url,
)


class ParseUserAgentTest(TestCase):
    """Test parse_user_agent function"""

    @patch("apps.analytics.utils.HAS_USER_AGENTS", False)
    def test_parse_user_agent_without_module(self):
        """Test parsing when user_agents module is not available"""
        result = parse_user_agent("Mozilla/5.0")

        self.assertIsInstance(result, dict)
        self.assertEqual(result["browser"], "Unknown")
        self.assertEqual(result["os"], "Unknown")
        self.assertEqual(result["device_type"], "other")

    @patch("apps.analytics.utils.HAS_USER_AGENTS", True)
    @patch("apps.analytics.utils.parse")
    def test_parse_user_agent_with_module(self, mock_parse):
        """Test parsing with user_agents module"""
        mock_ua = MagicMock()
        mock_ua.is_mobile = False
        mock_ua.is_tablet = False
        mock_ua.is_pc = True
        mock_ua.browser.family = "Chrome"
        mock_ua.browser.version_string = "91.0"
        mock_ua.os.family = "Windows"
        mock_ua.os.version_string = "10"
        mock_parse.return_value = mock_ua

        result = parse_user_agent("Chrome/91.0")

        self.assertIsInstance(result, dict)
        self.assertIn("browser", result)
        self.assertIn("os", result)
        self.assertIn("device_type", result)
        self.assertEqual(result["device_type"], "desktop")


class GetClientIpTest(TestCase):
    """Test get_client_ip function"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_client_ip_from_remote_addr(self):
        """Test extracting IP from REMOTE_ADDR"""
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        ip = get_client_ip(request)

        self.assertEqual(ip, "192.168.1.1")

    def test_get_client_ip_from_x_forwarded_for(self):
        """Test extracting IP from X-Forwarded-For header"""
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "10.0.0.1, 192.168.1.1"

        ip = get_client_ip(request)

        # Should get first IP
        self.assertEqual(ip, "10.0.0.1")

    def test_get_client_ip_default(self):
        """Test default IP when no headers present"""
        request = self.factory.get("/")
        # Remove any default REMOTE_ADDR
        request.META.pop("REMOTE_ADDR", None)

        ip = get_client_ip(request)

        self.assertEqual(ip, "127.0.0.1")


class GetGeoDataTest(TestCase):
    """Test get_geo_data function"""

    def test_get_geo_data_local_ip(self):
        """Test geo data for local IP addresses"""
        result = get_geo_data("127.0.0.1")

        self.assertIsInstance(result, dict)
        self.assertIn("country", result)
        self.assertIn("city", result)
        self.assertIsNone(result["country"])
        self.assertIsNone(result["city"])

    def test_get_geo_data_private_ip(self):
        """Test geo data for private IP addresses"""
        result = get_geo_data("192.168.1.1")

        self.assertIsInstance(result, dict)
        self.assertIsNone(result["country"])
        self.assertIsNone(result["city"])

    @patch("apps.analytics.utils.HAS_GEOIP2", False)
    def test_get_geo_data_without_geoip2(self):
        """Test geo data when GeoIP2 is not available"""
        result = get_geo_data("8.8.8.8")

        self.assertIsInstance(result, dict)
        self.assertIsNone(result["country"])
        self.assertIsNone(result["city"])


class SanitizeUrlTest(TestCase):
    """Test sanitize_url function"""

    def test_sanitize_url_empty(self):
        """Test sanitizing empty URL"""
        self.assertEqual(sanitize_url(""), "")
        self.assertEqual(sanitize_url(None), "")

    def test_sanitize_url_basic(self):
        """Test basic URL sanitization"""
        url = "https://example.com/page"
        result = sanitize_url(url)

        self.assertEqual(result, url)

    def test_sanitize_url_removes_sensitive_params(self):
        """Test removal of sensitive parameters"""
        url = "https://example.com/page?user=john&password=secret"
        result = sanitize_url(url)

        self.assertIn("user=john", result)
        self.assertNotIn("password=secret", result)

    def test_sanitize_url_truncation(self):
        """Test URL truncation"""
        long_url = "https://example.com/" + "a" * 2000
        result = sanitize_url(long_url, max_length=100)

        self.assertLessEqual(len(result), 100)

    def test_sanitize_url_invalid(self):
        """Test handling of invalid URLs"""
        invalid_url = "not a valid url"
        result = sanitize_url(invalid_url)

        # Should return original (possibly truncated)
        self.assertEqual(result, invalid_url)


class CalculateSessionDurationTest(TestCase):
    """Test calculate_session_duration function"""

    @patch("apps.analytics.utils.PageView")
    def test_calculate_session_duration_no_views(self, mock_pageview):
        """Test duration with no page views"""
        mock_pageview.objects.filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        duration = calculate_session_duration("session123")

        self.assertEqual(duration, 0)

    @patch("apps.analytics.utils.PageView")
    def test_calculate_session_duration_single_view(self, mock_pageview):
        """Test duration with single page view"""
        from django.utils import timezone

        now = timezone.now()
        mock_view = MagicMock(created_at=now)

        mock_pageview.objects.filter.return_value.order_by.return_value.first.return_value = (
            mock_view
        )
        mock_pageview.objects.filter.return_value.order_by.return_value.last.return_value = (
            mock_view
        )

        duration = calculate_session_duration("session123")

        self.assertEqual(duration, 0)
