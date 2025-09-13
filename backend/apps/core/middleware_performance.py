import json
import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

import brotli

"""Performance monitoring and optimization middleware."""


logger = logging.getLogger("performance")


class PerformanceMonitoringMiddleware(MiddlewareMixin):
    """Middleware to monitor and log performance metrics."""

    def process_request(self, request):
        """Start timing the request."""

        request._start_time = time.time()

        request._start_queries = len(connection.queries)

        return None

    def process_response(self, request, response):
        """Log performance metrics."""

        if not hasattr(request, "_start_time"):

            return response

        # Calculate metrics

        duration = time.time() - request._start_time

        num_queries = len(connection.queries) - request._start_queries

        # Add performance headers

        response["X-Response-Time"] = f"{duration:.3f}"

        response["X-Database-Queries"] = str(num_queries)

        response["X-Cache-Status"] = getattr(response, "_cache_status", "MISS")

        # Log slow requests

        if duration > 1.0:

            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {duration:.2f}s with {num_queries} queries"
            )

            # Log slow queries if in debug mode

            if settings.DEBUG and num_queries > 0:

                slow_queries = [
                    q
                    for q in connection.queries[request._start_queries :]
                    if float(q.get("time", 0)) > 0.1
                ]

                if slow_queries:

                    logger.warning(
                        f"Slow queries: {json.dumps(slow_queries, indent=2)}"
                    )

        # Track metrics in cache for monitoring

        if duration > 0.5:  # Track requests over 500ms

            cache_key = f"perf:slow:{request.path}"

            current = cache.get(cache_key, {"count": 0, "total_time": 0})

            current["count"] += 1

            current["total_time"] += duration

            current["avg_time"] = current["total_time"] / current["count"]

            cache.set(cache_key, current, timeout=3600)

        return response


class QueryCountLimitMiddleware(MiddlewareMixin):
    """Middleware to prevent N+1 queries by limiting query count."""

    MAX_QUERIES = 50  # Maximum queries per request

    def process_request(self, request):
        """Reset query count."""

        request._query_count_start = len(connection.queries)

        return None

    def process_response(self, request, response):
        """Check query count."""

        if not hasattr(request, "_query_count_start"):

            return response

        query_count = len(connection.queries) - request._query_count_start

        # Log excessive queries

        if query_count > self.MAX_QUERIES:

            logger.error(
                f"Excessive queries: {request.method} {request.path} "
                f"executed {query_count} queries (limit: {self.MAX_QUERIES})"
            )

            # In debug mode, return error response

            if settings.DEBUG:

                return JsonResponse(
                    {
                        "error": "Query limit exceeded",
                        "query_count": query_count,
                        "limit": self.MAX_QUERIES,
                        "path": request.path,
                    },
                    status=500,
                )

        return response


class CacheHitRateMiddleware(MiddlewareMixin):
    """Middleware to track cache hit rates."""

    def process_response(self, request, response):
        """Track cache hit/miss."""

        # Check if response has headers (HttpResponse object)

        if not hasattr(response, "get"):

            return response

        cache_status = response.get("X-Cache", "MISS")

        # Update hit rate statistics

        stats_key = "cache:stats:global"

        stats = cache.get(stats_key, {"hits": 0, "misses": 0})

        if cache_status == "HIT":

            stats["hits"] += 1

        else:

            stats["misses"] += 1

        stats["hit_rate"] = (
            stats["hits"] / (stats["hits"] + stats["misses"])
            if (stats["hits"] + stats["misses"]) > 0
            else 0
        )

        cache.set(stats_key, stats, timeout=86400)  # 24 hours

        # Add hit rate to response headers in debug mode

        if settings.DEBUG:

            response["X-Cache-Hit-Rate"] = f"{stats['hit_rate']:.2%}"

        return response


class DatabaseConnectionPoolMiddleware(MiddlewareMixin):
    """Middleware to manage database connection pooling."""

    def process_request(self, request):
        """Ensure connection is alive."""

        # Test connection and reconnect if needed

        try:

            connection.ensure_connection()

        except Exception:

            connection.close()

            connection.ensure_connection()

        return None

    def process_response(self, request, response):
        """Clean up connections for long requests."""

        # Close connection for requests that took too long

        if hasattr(request, "_start_time"):

            duration = time.time() - request._start_time

            if duration > 5.0:  # Close connection after 5 second requests

                connection.close()

        return response


class RequestThrottlingMiddleware(MiddlewareMixin):
    """Per-IP request throttling middleware."""

    def get_client_ip(self, request):
        """Get client IP address."""

        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if x_forwarded_for:

            ip = x_forwarded_for.split(",")[0]

        else:

            ip = request.META.get("REMOTE_ADDR")

        return ip

    def process_request(self, request):
        """Check throttle limits."""

        # Skip throttling for authenticated staff

        # Check if user attribute exists (AuthenticationMiddleware has run)

        if (
            hasattr(request, "user")
            and request.user.is_authenticated
            and request.user.is_staff
        ):

            return None

        ip = self.get_client_ip(request)

        cache_key = f"throttle:{ip}"

        # Get current request count

        request_count = cache.get(cache_key, 0)

        # Check limits based on path

        if request.path.startswith("/api/"):

            limit = 100  # 100 requests per minute for API

        else:

            limit = 200  # 200 requests per minute for regular pages

        if request_count >= limit:

            logger.warning(f"Rate limit exceeded for IP {ip}: {request_count} requests")

            return JsonResponse(
                {"error": "Rate limit exceeded", "retry_after": 60}, status=429
            )

        # Increment counter

        cache.set(cache_key, request_count + 1, timeout=60)

        return None


class CompressionMiddleware(MiddlewareMixin):
    """Enhanced compression middleware with Brotli support."""

    MIN_SIZE = 1024  # Minimum size to compress (1KB)

    def process_response(self, request, response):
        """Compress response if beneficial."""

        # Skip if already compressed

        if response.has_header("Content-Encoding"):

            return response

        # Check content type

        content_type = response.get("Content-Type", "")

        if not any(
            ct in content_type
            for ct in ["text/", "application/json", "application/javascript"]
        ):

            return response

        # Check size

        if len(response.content) < self.MIN_SIZE:

            return response

        # Check accepted encodings

        accepted = request.META.get("HTTP_ACCEPT_ENCODING", "")

        # Try Brotli first (better compression)

        if "br" in accepted:

            try:

                compressed = brotli.compress(response.content, quality=4)

                if len(compressed) < len(response.content):

                    response.content = compressed

                    response["Content-Encoding"] = "br"

                    response["Vary"] = "Accept-Encoding"

                    del response["Content-Length"]

            except ImportError:
                pass

        # Fall back to gzip (handled by GZipMiddleware)

        return response
