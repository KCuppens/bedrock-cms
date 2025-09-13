"""Comprehensive tests for analytics utility functions to boost coverage"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from django.utils import timezone

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
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"

        result = parse_user_agent(user_agent)

        self.assertEqual(result["browser"], "Unknown")
        self.assertEqual(result["os"], "Unknown")
        self.assertEqual(result["device_type"], "other")

    @patch("apps.analytics.utils.HAS_USER_AGENTS", True)
    @patch("apps.analytics.utils.parse")
    def test_parse_user_agent_desktop(self, mock_parse):
        """Test parsing desktop user agent"""
        mock_ua = MagicMock()
        mock_ua.is_mobile = False
        mock_ua.is_tablet = False
        mock_ua.is_pc = True
        mock_ua.browser.family = "Chrome"
        mock_ua.browser.version_string = "91.0"
        mock_ua.os.family = "Windows"
        mock_ua.os.version_string = "10"
        mock_parse.return_value = mock_ua

        result = parse_user_agent("Chrome on Windows")

        self.assertEqual(result["browser"], "Chrome 91.0")
        self.assertEqual(result["os"], "Windows 10")
        self.assertEqual(result["device_type"], "desktop")

    @patch("apps.analytics.utils.HAS_USER_AGENTS", True)
    @patch("apps.analytics.utils.parse")
    def test_parse_user_agent_mobile(self, mock_parse):
        """Test parsing mobile user agent"""
        mock_ua = MagicMock()
        mock_ua.is_mobile = True
        mock_ua.is_tablet = False
        mock_ua.is_pc = False
        mock_ua.browser.family = "Safari"
        mock_ua.browser.version_string = "14.0"
        mock_ua.os.family = "iOS"
        mock_ua.os.version_string = "14.6"
        mock_parse.return_value = mock_ua

        result = parse_user_agent("Safari on iPhone")

        self.assertEqual(result["device_type"], "mobile")

    @patch("apps.analytics.utils.HAS_USER_AGENTS", True)
    @patch("apps.analytics.utils.parse")
    def test_parse_user_agent_tablet(self, mock_parse):
        """Test parsing tablet user agent"""
        mock_ua = MagicMock()
        mock_ua.is_mobile = False
        mock_ua.is_tablet = True
        mock_ua.is_pc = False
        mock_ua.browser.family = "Safari"
        mock_ua.browser.version_string = "14.0"
        mock_ua.os.family = "iOS"
        mock_ua.os.version_string = "14.6"
        mock_parse.return_value = mock_ua

        result = parse_user_agent("Safari on iPad")

        self.assertEqual(result["device_type"], "tablet")


class GetClientIpTest(TestCase):
    """Test get_client_ip function"""

    def setUp(self):
        self.factory = RequestFactory()

    def test_get_client_ip_from_x_forwarded_for(self):
        """Test extracting IP from X-Forwarded-For header"""
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.1, 10.0.0.1, 172.16.0.1"

        ip = get_client_ip(request)

        self.assertEqual(ip, "192.168.1.1")

    def test_get_client_ip_from_x_forwarded_for_single(self):
        """Test extracting single IP from X-Forwarded-For"""
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.100"

        ip = get_client_ip(request)

        self.assertEqual(ip, "192.168.1.100")

    def test_get_client_ip_from_remote_addr(self):
        """Test extracting IP from REMOTE_ADDR"""
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.50"

        ip = get_client_ip(request)

        self.assertEqual(ip, "192.168.1.50")

    def test_get_client_ip_default(self):
        """Test default IP when no headers present"""
        request = self.factory.get("/")

        ip = get_client_ip(request)

        self.assertEqual(ip, "127.0.0.1")


class GetGeoDataTest(TestCase):
    """Test get_geo_data function"""

    def test_get_geo_data_local_ip(self):
        """Test geo data for local IP addresses"""
        result = get_geo_data("127.0.0.1")
        self.assertIsNone(result["country"])
        self.assertIsNone(result["city"])

        result = get_geo_data("localhost")
        self.assertIsNone(result["country"])
        self.assertIsNone(result["city"])

        result = get_geo_data("192.168.1.1")
        self.assertIsNone(result["country"])
        self.assertIsNone(result["city"])

    @patch("apps.analytics.utils.HAS_GEOIP2", False)
    def test_get_geo_data_without_geoip2(self):
        """Test geo data when GeoIP2 is not available"""
        result = get_geo_data("8.8.8.8")

        self.assertIsNone(result["country"])
        self.assertIsNone(result["city"])

    @patch("apps.analytics.utils.HAS_GEOIP2", True)
    @patch("apps.analytics.utils.GeoIP2")
    def test_get_geo_data_success(self, mock_geoip2_class):
        """Test successful geo data lookup"""
        mock_geoip = MagicMock()
        mock_geoip.country.return_value = {"country_code": "US"}
        mock_geoip.city.return_value = {"city": "New York"}
        mock_geoip2_class.return_value = mock_geoip

        result = get_geo_data("8.8.8.8")

        self.assertEqual(result["country"], "US")
        self.assertEqual(result["city"], "New York")

    @patch("apps.analytics.utils.HAS_GEOIP2", True)
    @patch("apps.analytics.utils.GeoIP2")
    def test_get_geo_data_exception(self, mock_geoip2_class):
        """Test geo data when lookup fails"""
        mock_geoip2_class.side_effect = Exception("GeoIP error")

        result = get_geo_data("8.8.8.8")

        self.assertIsNone(result["country"])
        self.assertIsNone(result["city"])


class SanitizeUrlTest(TestCase):
    """Test sanitize_url function"""

    def test_sanitize_url_empty(self):
        """Test sanitizing empty URL"""
        result = sanitize_url("")
        self.assertEqual(result, "")

    def test_sanitize_url_removes_sensitive_params(self):
        """Test removal of sensitive query parameters"""
        url = (
            "https://example.com/page?user=john&password=secret&token=abc123&safe=value"
        )

        result = sanitize_url(url)

        self.assertNotIn("password=", result)
        self.assertNotIn("token=", result)
        self.assertIn("user=john", result)
        self.assertIn("safe=value", result)

    def test_sanitize_url_case_insensitive(self):
        """Test case-insensitive parameter matching"""
        url = "https://example.com?PASSWORD=secret&Token=abc&AUTH=xyz"

        result = sanitize_url(url)

        self.assertNotIn("PASSWORD=", result)
        self.assertNotIn("Token=", result)
        self.assertNotIn("AUTH=", result)

    def test_sanitize_url_truncation(self):
        """Test URL truncation"""
        long_url = "https://example.com/" + "a" * 2000

        result = sanitize_url(long_url, max_length=100)

        self.assertEqual(len(result), 100)

    def test_sanitize_url_invalid_url(self):
        """Test handling of invalid URLs"""
        invalid_url = "not a valid url at all"

        result = sanitize_url(invalid_url)

        # Should return truncated original on parse failure
        self.assertEqual(result, invalid_url)

    def test_sanitize_url_preserves_structure(self):
        """Test URL structure is preserved"""
        url = "https://example.com:8080/path/to/page?query=value#fragment"

        result = sanitize_url(url)

        self.assertIn("example.com:8080", result)
        self.assertIn("/path/to/page", result)
        self.assertIn("query=value", result)
        self.assertIn("#fragment", result)


class CalculateSessionDurationTest(TestCase):
    """Test calculate_session_duration function"""

    @patch("apps.analytics.utils.PageView")
    def test_calculate_session_duration_with_pageviews(self, mock_pageview):
        """Test calculating duration from page views"""
        now = timezone.now()
        first_view = MagicMock(created_at=now)
        last_view = MagicMock(created_at=now + timedelta(minutes=30))

        mock_pageview.objects.filter.return_value.order_by.return_value.first.return_value = (
            first_view
        )
        mock_pageview.objects.filter.return_value.order_by.return_value.last.return_value = (
            last_view
        )

        duration = calculate_session_duration("session123")

        self.assertEqual(duration, 1800)  # 30 minutes in seconds

    @patch("apps.analytics.utils.PageView")
    def test_calculate_session_duration_single_pageview(self, mock_pageview):
        """Test duration with single page view"""
        now = timezone.now()
        single_view = MagicMock(created_at=now)

        mock_pageview.objects.filter.return_value.order_by.return_value.first.return_value = (
            single_view
        )
        mock_pageview.objects.filter.return_value.order_by.return_value.last.return_value = (
            single_view
        )

        duration = calculate_session_duration("session123")

        self.assertEqual(duration, 0)

    @patch("apps.analytics.utils.PageView")
    def test_calculate_session_duration_no_pageviews(self, mock_pageview):
        """Test duration with no page views"""
        mock_pageview.objects.filter.return_value.order_by.return_value.first.return_value = (
            None
        )

        duration = calculate_session_duration("session123")

        self.assertEqual(duration, 0)
