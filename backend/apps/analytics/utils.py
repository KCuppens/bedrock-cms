"""
Utility functions for analytics functionality.
"""

import re
from datetime import date, datetime, timedelta

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.geoip2 import GeoIP2
from django.utils import timezone

from user_agents import parse


def parse_user_agent(user_agent_string: str) -> dict[str, str]:
    """
    Parse user agent string to extract browser and OS information.

    Args:
        user_agent_string: Raw user agent string from request

    Returns:
        Dict containing browser, os, and device_type information
    """
    user_agent = parse(user_agent_string)

    device_type = "other"
    if user_agent.is_mobile:
        device_type = "mobile"
    elif user_agent.is_tablet:
        device_type = "tablet"
    elif user_agent.is_pc:
        device_type = "desktop"

    return {
        "browser": f"{user_agent.browser.family} {user_agent.browser.version_string}",
        "os": f"{user_agent.os.family} {user_agent.os.version_string}",
        "device_type": device_type,
    }


def get_client_ip(request) -> str:
    """
    Extract client IP address from request, handling proxies.

    Args:
        request: Django request object

    Returns:
        Client IP address as string
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # Take the first IP in the chain
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")

    return ip


def get_geo_data(ip_address: str) -> dict[str, str | None]:
    """
    Get geographic data from IP address.

    Args:
        ip_address: IP address string

    Returns:
        Dict containing country and city information
    """
    try:
        # Skip local/private IPs
        if ip_address in ["127.0.0.1", "localhost"] or ip_address.startswith(
            "192.168."
        ):
            return {"country": None, "city": None}

        g = GeoIP2()
        country = g.country(ip_address)
        city = g.city(ip_address)

        return {"country": country.get("country_code"), "city": city.get("city")}
    except Exception:
        # Fail silently if GeoIP is not configured or IP lookup fails
        return {"country": None, "city": None}


def sanitize_url(url: str, max_length: int = 1024) -> str:
    """
    Sanitize and truncate URL for storage.

    Args:
        url: Raw URL string
        max_length: Maximum length for truncation

    Returns:
        Sanitized URL string
    """
    if not url:
        return ""

    # Remove query parameters that might contain sensitive data
    sensitive_params = ["password", "token", "key", "secret", "auth"]

    try:
        from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        # Filter out sensitive parameters
        filtered_params = {
            k: v
            for k, v in query_params.items()
            if not any(sensitive in k.lower() for sensitive in sensitive_params)
        }

        # Rebuild query string
        new_query = urlencode(filtered_params, doseq=True)

        # Reconstruct URL
        sanitized_url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

        # Truncate if too long
        return sanitized_url[:max_length]

    except Exception:
        # If parsing fails, just truncate the original URL
        return url[:max_length]


def calculate_session_duration(session_id: str, end_time: datetime = None) -> int:
    """
    Calculate session duration in seconds.

    Args:
        session_id: Session identifier
        end_time: End time for calculation (defaults to now)

    Returns:
        Session duration in seconds
    """
    from .models import PageView

    if end_time is None:
        end_time = timezone.now()

    try:
        session_views = PageView.objects.filter(session_id=session_id).order_by(
            "viewed_at"
        )

        if not session_views.exists():
            return 0

        first_view = session_views.first().viewed_at
        last_view = session_views.last().viewed_at

        return int((last_view - first_view).total_seconds())

    except Exception:
        return 0


def get_content_type_and_id(obj) -> tuple[int, int]:
    """
    Get ContentType ID and object ID for any Django model instance.

    Args:
        obj: Django model instance

    Returns:
        Tuple of (content_type_id, object_id)
    """
    content_type = ContentType.objects.get_for_model(obj)
    return content_type.id, obj.id


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{hours}h {remaining_minutes}m"


def get_date_range(period: str, date_param: str = None) -> tuple[date, date]:
    """
    Get date range for analytics queries.

    Args:
        period: Period type ('day', 'week', 'month', 'quarter', 'year')
        date_param: Optional date parameter (YYYY-MM-DD format)

    Returns:
        Tuple of (start_date, end_date)
    """
    if date_param:
        try:
            target_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            target_date = timezone.now().date()
    else:
        target_date = timezone.now().date()

    if period == "day":
        return target_date, target_date

    elif period == "week":
        # Start of week (Monday)
        start_date = target_date - timedelta(days=target_date.weekday())
        end_date = start_date + timedelta(days=6)
        return start_date, end_date

    elif period == "month":
        start_date = date(target_date.year, target_date.month, 1)
        if target_date.month == 12:
            end_date = date(target_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(target_date.year, target_date.month + 1, 1) - timedelta(
                days=1
            )
        return start_date, end_date

    elif period == "quarter":
        quarter = (target_date.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        start_date = date(target_date.year, start_month, 1)

        if quarter == 4:
            end_date = date(target_date.year, 12, 31)
        else:
            end_date = date(target_date.year, start_month + 3, 1) - timedelta(days=1)

        return start_date, end_date

    elif period == "year":
        start_date = date(target_date.year, 1, 1)
        end_date = date(target_date.year, 12, 31)
        return start_date, end_date

    else:
        # Default to last 30 days
        end_date = target_date
        start_date = target_date - timedelta(days=30)
        return start_date, end_date


def is_bot_user_agent(user_agent_string: str) -> bool:
    """
    Check if user agent string indicates a bot or crawler.

    Args:
        user_agent_string: User agent string to check

    Returns:
        True if appears to be a bot
    """
    bot_patterns = [
        r"bot",
        r"crawl",
        r"spider",
        r"scraper",
        r"search",
        r"facebook",
        r"twitter",
        r"linkedin",
        r"google",
        r"bing",
        r"yahoo",
        r"duckduckgo",
        r"yandex",
        r"curl",
        r"wget",
        r"python",
        r"requests",
        r"monitoring",
        r"uptime",
        r"pingdom",
        r"datadog",
    ]

    user_agent_lower = user_agent_string.lower()

    for pattern in bot_patterns:
        if re.search(pattern, user_agent_lower):
            return True

    return False


def clean_referrer(referrer: str) -> str:
    """
    Clean and normalize referrer URL.

    Args:
        referrer: Raw referrer URL

    Returns:
        Cleaned referrer URL
    """
    if not referrer:
        return ""

    try:
        from urllib.parse import urlparse

        parsed = urlparse(referrer)

        # Remove query parameters and fragments
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        # Remove trailing slash
        if clean_url.endswith("/") and len(clean_url) > 1:
            clean_url = clean_url.rstrip("/")

        return clean_url

    except Exception:
        return referrer


def get_analytics_context(request) -> dict:
    """
    Extract analytics context from Django request.

    Args:
        request: Django request object

    Returns:
        Dict containing analytics context data
    """
    user_agent_string = request.META.get("HTTP_USER_AGENT", "")
    user_agent_data = parse_user_agent(user_agent_string)
    ip_address = get_client_ip(request)
    geo_data = get_geo_data(ip_address)

    return {
        "ip_address": ip_address,
        "user_agent": user_agent_string,
        "browser": user_agent_data["browser"],
        "os": user_agent_data["os"],
        "device_type": user_agent_data["device_type"],
        "country": geo_data["country"],
        "city": geo_data["city"],
        "referrer": clean_referrer(request.META.get("HTTP_REFERER", "")),
        "is_bot": is_bot_user_agent(user_agent_string),
        "session_key": request.session.session_key or "",
    }
