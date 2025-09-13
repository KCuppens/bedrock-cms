"""
Tests for analytics utility functions.

Tests all utility functions in apps/analytics/utils.py for high coverage.
"""

import re
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from django.utils import timezone

from apps.analytics.utils import (
    calculate_session_duration,
    clean_referrer,
    format_duration,
    get_analytics_context,
    get_client_ip,
    get_content_type_and_id,
    get_date_range,
    get_geo_data,
    is_bot_user_agent,
    parse_user_agent,
    sanitize_url,
)

User = get_user_model()


class ParseUserAgentTest(TestCase):
    """Test parse_user_agent function."""

    def test_desktop_user_agent(self):
        """Test parsing desktop user agent."""
        ua_string = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        result = parse_user_agent(ua_string)

        self.assertEqual(result["device_type"], "desktop")
        self.assertIn("Chrome", result["browser"])
        self.assertIn("Windows", result["os"])

    def test_mobile_user_agent(self):
        """Test parsing mobile user agent."""
        ua_string = "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148"
        result = parse_user_agent(ua_string)

        self.assertEqual(result["device_type"], "mobile")
        self.assertIn("Mobile Safari", result["browser"])
        self.assertIn("iOS", result["os"])

    def test_tablet_user_agent(self):
        """Test parsing tablet user agent."""
        ua_string = "Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15"
        result = parse_user_agent(ua_string)

        self.assertEqual(result["device_type"], "tablet")

    def test_unknown_user_agent(self):
        """Test parsing unknown/bot user agent."""
        ua_string = "CustomBot/1.0"
        result = parse_user_agent(ua_string)

        self.assertEqual(result["device_type"], "other")
        self.assertIn("browser", result)
        self.assertIn("os", result)


class GetClientIpTest(TestCase):
    """Test get_client_ip function."""

    def setUp(self):
        self.factory = RequestFactory()

    def test_with_x_forwarded_for(self):
        """Test getting IP from X-Forwarded-For header."""
        request = self.factory.get("/")
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.100, 10.0.0.1"

        ip = get_client_ip(request)
        self.assertEqual(ip, "192.168.1.100")

    def test_with_remote_addr(self):
        """Test getting IP from REMOTE_ADDR."""
        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.200"

        ip = get_client_ip(request)
        self.assertEqual(ip, "192.168.1.200")

    def test_default_ip(self):
        """Test default IP when no headers present."""
        request = self.factory.get("/")

        ip = get_client_ip(request)
        self.assertEqual(ip, "127.0.0.1")


class GetGeoDataTest(TestCase):
    """Test get_geo_data function."""

    def test_local_ip_address(self):
        """Test that local IPs return empty geo data."""
        result = get_geo_data("127.0.0.1")
        self.assertEqual(result, {"country": None, "city": None})

        result = get_geo_data("192.168.1.1")
        self.assertEqual(result, {"country": None, "city": None})

    @patch("apps.analytics.utils.GeoIP2")
    def test_external_ip_success(self, mock_geoip2):
        """Test successful geo lookup for external IP."""
        mock_geo = Mock()
        mock_geo.country.return_value = {"country_code": "US"}
        mock_geo.city.return_value = {"city": "New York"}
        mock_geoip2.return_value = mock_geo

        result = get_geo_data("8.8.8.8")

        self.assertEqual(result["country"], "US")
        self.assertEqual(result["city"], "New York")

    @patch("apps.analytics.utils.GeoIP2")
    def test_geoip_exception(self, mock_geoip2):
        """Test handling of GeoIP exceptions."""
        mock_geoip2.side_effect = Exception("GeoIP error")

        result = get_geo_data("8.8.8.8")
        self.assertEqual(result, {"country": None, "city": None})


class SanitizeUrlTest(TestCase):
    """Test sanitize_url function."""

    def test_empty_url(self):
        """Test sanitizing empty URL."""
        result = sanitize_url("")
        self.assertEqual(result, "")

    def test_url_with_sensitive_params(self):
        """Test removing sensitive parameters."""
        url = "https://example.com/page?password=secret&token=abc123&normal=value"
        result = sanitize_url(url)

        self.assertNotIn("password", result)
        self.assertNotIn("token", result)
        self.assertIn("normal=value", result)

    def test_url_truncation(self):
        """Test URL truncation."""
        long_url = "https://example.com/" + "a" * 2000
        result = sanitize_url(long_url, max_length=100)

        self.assertLessEqual(len(result), 100)

    def test_malformed_url(self):
        """Test handling malformed URLs."""
        malformed_url = "not-a-valid-url"
        result = sanitize_url(malformed_url)

        # Should return truncated original URL
        self.assertEqual(result, malformed_url)


class CalculateSessionDurationTest(TestCase):
    """Test calculate_session_duration function."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com"
        )

    def test_no_page_views(self):
        """Test session duration with no page views."""
        duration = calculate_session_duration("nonexistent_session")
        self.assertEqual(duration, 0)

    def test_single_page_view(self):
        """Test session duration with single page view."""
        from apps.analytics.models import PageView

        PageView.objects.create(
            session_id="test_session",
            ip_address="127.0.0.1",
            user_agent="Test",
            url="https://example.com",
        )

        duration = calculate_session_duration("test_session")
        self.assertEqual(duration, 0)  # Same start and end time

    def test_multiple_page_views(self):
        """Test session duration with multiple page views."""
        from apps.analytics.models import PageView

        # Create views with different timestamps
        first_view = PageView.objects.create(
            session_id="test_session",
            ip_address="127.0.0.1",
            user_agent="Test",
            url="https://example.com/1",
        )

        # Manually set viewed_at for second view
        second_view = PageView.objects.create(
            session_id="test_session",
            ip_address="127.0.0.1",
            user_agent="Test",
            url="https://example.com/2",
        )
        second_view.viewed_at = first_view.viewed_at + timedelta(minutes=5)
        second_view.save()

        duration = calculate_session_duration("test_session")
        self.assertEqual(duration, 300)  # 5 minutes = 300 seconds

    def test_exception_handling(self):
        """Test exception handling in session duration calculation."""
        with patch("apps.analytics.utils.PageView.objects.filter") as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            duration = calculate_session_duration("test_session")
            self.assertEqual(duration, 0)


class GetContentTypeAndIdTest(TestCase):
    """Test get_content_type_and_id function."""

    def test_get_content_type_and_id(self):
        """Test getting content type and ID for model instance."""
        user = User.objects.create_user(username="testuser", email="test@example.com")

        content_type_id, object_id = get_content_type_and_id(user)

        content_type = ContentType.objects.get_for_model(User)
        self.assertEqual(content_type_id, content_type.id)
        self.assertEqual(object_id, user.id)


class FormatDurationTest(TestCase):
    """Test format_duration function."""

    def test_seconds_only(self):
        """Test formatting duration in seconds."""
        result = format_duration(45)
        self.assertEqual(result, "45s")

    def test_minutes_and_seconds(self):
        """Test formatting duration in minutes and seconds."""
        result = format_duration(125)  # 2 minutes 5 seconds
        self.assertEqual(result, "2m 5s")

    def test_hours_and_minutes(self):
        """Test formatting duration in hours and minutes."""
        result = format_duration(3665)  # 1 hour 1 minute 5 seconds
        self.assertEqual(result, "1h 1m")

    def test_exact_minutes(self):
        """Test formatting exact minutes."""
        result = format_duration(120)  # 2 minutes exactly
        self.assertEqual(result, "2m 0s")


class GetDateRangeTest(TestCase):
    """Test get_date_range function."""

    def test_day_period(self):
        """Test getting date range for day period."""
        test_date = "2023-06-15"
        start_date, end_date = get_date_range("day", test_date)

        expected_date = date(2023, 6, 15)
        self.assertEqual(start_date, expected_date)
        self.assertEqual(end_date, expected_date)

    def test_week_period(self):
        """Test getting date range for week period."""
        test_date = "2023-06-15"  # Thursday
        start_date, end_date = get_date_range("week", test_date)

        # Week should start on Monday (2023-06-12) and end on Sunday (2023-06-18)
        self.assertEqual(start_date, date(2023, 6, 12))
        self.assertEqual(end_date, date(2023, 6, 18))

    def test_month_period(self):
        """Test getting date range for month period."""
        test_date = "2023-06-15"
        start_date, end_date = get_date_range("month", test_date)

        self.assertEqual(start_date, date(2023, 6, 1))
        self.assertEqual(end_date, date(2023, 6, 30))

    def test_quarter_period(self):
        """Test getting date range for quarter period."""
        test_date = "2023-06-15"  # Q2
        start_date, end_date = get_date_range("quarter", test_date)

        self.assertEqual(start_date, date(2023, 4, 1))
        self.assertEqual(end_date, date(2023, 6, 30))

    def test_year_period(self):
        """Test getting date range for year period."""
        test_date = "2023-06-15"
        start_date, end_date = get_date_range("year", test_date)

        self.assertEqual(start_date, date(2023, 1, 1))
        self.assertEqual(end_date, date(2023, 12, 31))

    def test_invalid_period(self):
        """Test getting date range for invalid period (defaults to 30 days)."""
        today = timezone.now().date()
        start_date, end_date = get_date_range("invalid")

        self.assertEqual(end_date, today)
        self.assertEqual(start_date, today - timedelta(days=30))

    def test_invalid_date_format(self):
        """Test handling invalid date format."""
        today = timezone.now().date()
        start_date, end_date = get_date_range("day", "invalid-date")

        # Should use today's date
        self.assertEqual(start_date, today)
        self.assertEqual(end_date, today)


class IsBotUserAgentTest(TestCase):
    """Test is_bot_user_agent function."""

    def test_obvious_bot(self):
        """Test detecting obvious bot user agents."""
        bot_agents = [
            "Googlebot/2.1",
            "Mozilla/5.0 (compatible; bingbot/2.0)",
            "facebookexternalhit/1.1",
            "Twitterbot/1.0",
            "LinkedInBot/1.0",
            "spider-bot/1.0",
            "crawl-agent",
            "search-engine-bot",
        ]

        for bot_agent in bot_agents:
            with self.subTest(bot_agent=bot_agent):
                self.assertTrue(is_bot_user_agent(bot_agent))

    def test_legitimate_browser(self):
        """Test that legitimate browsers are not detected as bots."""
        browser_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15",
        ]

        for browser_agent in browser_agents:
            with self.subTest(browser_agent=browser_agent):
                self.assertFalse(is_bot_user_agent(browser_agent))

    def test_edge_cases(self):
        """Test edge cases in bot detection."""
        # Should detect curl and wget
        self.assertTrue(is_bot_user_agent("curl/7.64.1"))
        self.assertTrue(is_bot_user_agent("Wget/1.20.3"))

        # Should detect monitoring tools
        self.assertTrue(is_bot_user_agent("Pingdom.com_bot_version_1.4"))
        self.assertTrue(is_bot_user_agent("DatadogSynthetics"))


class CleanReferrerTest(TestCase):
    """Test clean_referrer function."""

    def test_empty_referrer(self):
        """Test cleaning empty referrer."""
        result = clean_referrer("")
        self.assertEqual(result, "")

    def test_remove_query_and_fragment(self):
        """Test removing query parameters and fragments."""
        referrer = "https://example.com/page?param=value&other=123#section"
        result = clean_referrer(referrer)

        self.assertEqual(result, "https://example.com/page")

    def test_remove_trailing_slash(self):
        """Test removing trailing slash."""
        referrer = "https://example.com/page/"
        result = clean_referrer(referrer)

        self.assertEqual(result, "https://example.com/page")

    def test_keep_root_slash(self):
        """Test keeping root slash."""
        referrer = "https://example.com/"
        result = clean_referrer(referrer)

        self.assertEqual(result, "https://example.com/")

    def test_malformed_url(self):
        """Test handling malformed referrer URL."""
        referrer = "not-a-valid-url"
        result = clean_referrer(referrer)

        self.assertEqual(result, referrer)


class GetAnalyticsContextTest(TestCase):
    """Test get_analytics_context function."""

    def setUp(self):
        self.factory = RequestFactory()

    @patch("apps.analytics.utils.get_geo_data")
    def test_complete_analytics_context(self, mock_get_geo_data):
        """Test getting complete analytics context from request."""
        mock_get_geo_data.return_value = {"country": "US", "city": "New York"}

        request = self.factory.get("/", HTTP_USER_AGENT="Mozilla/5.0 Chrome/91.0")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        request.META["HTTP_REFERER"] = "https://google.com/search?q=test"
        request.session = {"session_key": "test_session_123"}

        context = get_analytics_context(request)

        self.assertEqual(context["ip_address"], "192.168.1.100")
        self.assertEqual(context["user_agent"], "Mozilla/5.0 Chrome/91.0")
        self.assertIn("browser", context)
        self.assertIn("os", context)
        self.assertIn("device_type", context)
        self.assertEqual(context["country"], "US")
        self.assertEqual(context["city"], "New York")
        self.assertEqual(context["referrer"], "https://google.com/search")
        self.assertFalse(context["is_bot"])
        self.assertEqual(context["session_key"], "test_session_123")

    def test_minimal_request(self):
        """Test analytics context with minimal request data."""
        request = self.factory.get("/")
        request.session = {}

        context = get_analytics_context(request)

        # Should handle missing data gracefully
        self.assertIn("ip_address", context)
        self.assertIn("user_agent", context)
        self.assertIn("is_bot", context)
        self.assertEqual(context["referrer"], "")
        self.assertEqual(context["session_key"], "")

    @patch("apps.analytics.utils.is_bot_user_agent")
    def test_bot_detection_in_context(self, mock_is_bot):
        """Test bot detection in analytics context."""
        mock_is_bot.return_value = True

        request = self.factory.get("/", HTTP_USER_AGENT="Googlebot/2.1")
        request.session = {}

        context = get_analytics_context(request)

        self.assertTrue(context["is_bot"])
        mock_is_bot.assert_called_with("Googlebot/2.1")


class UtilsIntegrationTest(TestCase):
    """Integration tests for utility functions."""

    def test_url_sanitization_and_cleaning_pipeline(self):
        """Test URL processing pipeline."""
        # Test complete URL processing
        url = "https://example.com/page?password=secret&normal=value#section"

        # First sanitize (removes sensitive params)
        sanitized = sanitize_url(url)
        self.assertNotIn("password=secret", sanitized)
        self.assertIn("normal=value", sanitized)

        # Then clean as referrer (removes query and fragment)
        cleaned = clean_referrer(sanitized)
        self.assertEqual(cleaned, "https://example.com/page")

    def test_user_agent_and_bot_detection_consistency(self):
        """Test consistency between user agent parsing and bot detection."""
        test_agents = [
            ("Googlebot/2.1", True),
            ("Mozilla/5.0 Chrome/91.0", False),
            ("curl/7.64.1", True),
            ("facebookexternalhit/1.1", True),
        ]

        for agent, expected_bot in test_agents:
            with self.subTest(agent=agent):
                ua_data = parse_user_agent(agent)
                is_bot = is_bot_user_agent(agent)

                self.assertEqual(is_bot, expected_bot)
                self.assertIn("browser", ua_data)
                self.assertIn("device_type", ua_data)
