import logging
import time

from django.core.cache import cache

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

"""
Custom throttling classes for enhanced API security.
"""


class WriteOperationThrottle(UserRateThrottle):
    """
    Throttle class specifically for write operations (POST, PUT, PATCH, DELETE).

    More restrictive than read operations to prevent abuse.
    """

    scope = "write"

    def allow_request(self, request, view):
        """Only apply throttling to write operations."""

        if request.method in ["GET", "HEAD", "OPTIONS"]:

            return True

        return super().allow_request(request, view)


class BurstWriteThrottle(UserRateThrottle):
    """
    Short-term burst protection for write operations.

    Prevents rapid successive writes that could indicate automation or abuse.
    """

    scope = "burst_write"

    def allow_request(self, request, view):
        """Only apply to write operations with burst protection."""

        if request.method in ["GET", "HEAD", "OPTIONS"]:

            return True

        return super().allow_request(request, view)


class PublishOperationThrottle(UserRateThrottle):
    """
    Special throttle for publish/unpublish operations.

    These are particularly sensitive operations that should be limited.
    """

    scope = "publish"

    def allow_request(self, request, view):
        """Apply throttling to publish/unpublish endpoints."""

        # Only apply to specific actions

        action = getattr(view, "action", None)

        if action in ["publish", "unpublish"]:

            return super().allow_request(request, view)

        return True


class MediaUploadThrottle(UserRateThrottle):
    """
    Throttle for media uploads to prevent storage abuse.
    """

    scope = "media_upload"

    def allow_request(self, request, view):
        """Apply throttling to media upload endpoints."""

        # Check if this is a media upload

        if "assets" in request.path and request.method == "POST":

            return super().allow_request(request, view)

        return True


class LoginAttemptThrottle(AnonRateThrottle):
    """
    Strict throttling for login attempts to prevent brute force attacks.

    Tracks by IP address for anonymous users.
    """

    scope = "login"

    def get_cache_key(self, request, view):
        """Use IP address as the throttle key for login attempts."""

        if request.user.is_authenticated:

            # For authenticated users, use their user ID

            ident = str(request.user.pk)

        else:

            # For anonymous users, use IP address

            ident = self.get_ident(request)

        return self.cache_format % {"scope": self.scope, "ident": ident}


class AdminOperationThrottle(UserRateThrottle):
    """
    Throttle for admin-level operations.

    More generous limits for admin users, but still protected.
    """

    scope = "admin"

    def allow_request(self, request, view):
        """Apply different rates based on user role."""

        if not request.user.is_authenticated:

            return False

        # Admin users get higher limits

        if request.user.is_staff or request.user.is_superuser:

            return super().allow_request(request, view)

        # Non-admin users get normal throttling

        # Fall back to regular user throttling

        return True


class SecurityScanThrottle(AnonRateThrottle):
    """
    Detect and throttle potential security scanning attempts.



    This throttle looks for patterns that might indicate:

    - Directory traversal attempts

    - SQL injection attempts

    - XSS attempts

    - Other malicious patterns
    """

    scope = "security_scan"

    SUSPICIOUS_PATTERNS = [
        "../",  # Directory traversal
        "..\\",  # Windows directory traversal
        "<script",  # XSS attempts
        "javascript:",  # XSS attempts
        "SELECT ",  # SQL injection
        "INSERT ",  # SQL injection
        "DELETE ",  # SQL injection
        "DROP ",  # SQL injection
        "UNION ",  # SQL injection
        "1=1",  # SQL injection
        "1'='1",  # SQL injection
        "eval(",  # Code execution
        "exec(",  # Code execution
        """"system(",  # Command execution""",
    ]

    def is_suspicious_request(self, request):
        """Check if the request contains suspicious patterns."""

        # Check query parameters

        for _key, value in request.GET.items():

            if isinstance(value, str):

                for pattern in self.SUSPICIOUS_PATTERNS:

                    if pattern.lower() in value.lower():

                        return True

        # Check POST data if available

        if hasattr(request, "data") and request.data:

            for _key, value in request.data.items():

                if isinstance(value, str):

                    for pattern in self.SUSPICIOUS_PATTERNS:

                        if pattern.lower() in value.lower():

                            return True

        # Check path for suspicious patterns

        path = request.path.lower()

        for pattern in self.SUSPICIOUS_PATTERNS:

            if pattern.lower() in path:

                return True

        return False

    def allow_request(self, request, view):
        """Apply extra throttling to suspicious requests."""

        if self.is_suspicious_request(request):

            # Log the suspicious request

            logger = logging.getLogger(__name__)

            logger.warning(
                f"Suspicious request detected from {self.get_ident(request)}: "
                f"{request.method} {request.path} - Query: {dict(request.GET)} - "
                f"User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}"
            )

            # Apply stricter throttling

            return super().allow_request(request, view)

        return True


# Utility function to get comprehensive rate limit info


def get_rate_limit_status(request, throttle_classes=None):
    """
    Get current rate limit status for a request across multiple throttle classes.

    Args:
        request: The Django request object
        throttle_classes: List of throttle classes to check

    Returns:
        Dict with rate limit information for each throttle class
    """

    if throttle_classes is None:

        throttle_classes = [
            WriteOperationThrottle,
            BurstWriteThrottle,
            PublishOperationThrottle,
            MediaUploadThrottle,
            LoginAttemptThrottle,
            AdminOperationThrottle,
        ]

    status = {}

    for throttle_class in throttle_classes:

        throttle = throttle_class()

        # Get the cache key for this throttle

        cache_key = throttle.get_cache_key(request, None)

        if not cache_key:
            continue

        # Get current request history

        history = cache.get(cache_key, [])

        # Calculate remaining requests

        now = time.time()

        # Remove old entries

        history = [
            timestamp for timestamp in history if timestamp > now - throttle.duration
        ]

        remaining = throttle.num_requests - len(history)

        status[throttle_class.__name__] = {
            "scope": getattr(throttle, "scope", "unknown"),
            "limit": throttle.num_requests,
            "remaining": max(0, remaining),
            "reset_time": now + throttle.duration,
            "duration": throttle.duration,
        }

    return status
