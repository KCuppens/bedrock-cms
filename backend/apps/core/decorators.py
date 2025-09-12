import hashlib
import json
from functools import wraps

from django.core.cache import cache
from django.http import HttpRequest
from rest_framework.response import Response

from apps.core.cache import cache_manager

def cache_response(
    timeout=300, key_prefix="", vary_on_headers=None, cache_errors=False
):

    Enhanced cache decorator for function/method responses.

    Args:
        timeout: Cache timeout in seconds
        key_prefix: Custom prefix for cache keys
        vary_on_headers: List of headers to include in cache key
        cache_errors: Whether to cache error responses

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(
                prefix=key_prefix or func.__name__,
                args=args,
                kwargs=kwargs,
                headers=vary_on_headers,
            )

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)

            # Only cache successful responses
            if not _is_error_response(result) or cache_errors:
                cache.set(cache_key, result, timeout)

            return result

        return wrapper

    return decorator

def cache_method_response(timeout=300, vary_on_user=True, vary_on_headers=None):

    Enhanced cache decorator specifically for viewset methods.

    Args:
        timeout: Cache timeout in seconds
        vary_on_user: Include user in cache key
        vary_on_headers: List of headers to include in cache key

    def decorator(method):
        @wraps(method)
        def wrapper(self, request, *args, **kwargs):
            # Generate comprehensive cache key
            cache_key_parts = [
                self.__class__.__name__,
                method.__name__,
                request.method,
                request.path,
            ]

            # Include user if needed
            if vary_on_user and request.user.is_authenticated:
                cache_key_parts.append(f"user:{request.user.id}")

            # Include query parameters
            if request.query_params:
                params = sorted(request.query_params.items())
                params_str = "&".join(f"{k}={v}" for k, v in params)
                cache_key_parts.append(
                    f"params:{hashlib.md5(params_str.encode(), usedforsecurity=False).hexdigest()[:8]}"
                )

            # Include specified headers
            if vary_on_headers:
                for header in vary_on_headers:
                    header_value = request.META.get(
                        f"HTTP_{header.upper().replace('-', '_')}"
                    )
                    if header_value:
                        cache_key_parts.append(f"{header}:{header_value}")

            cache_key = ":".join(cache_key_parts)

            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                # Add cache hit header
                if isinstance(cached_response, Response):
                    cached_response["X-Cache"] = "HIT"
                return cached_response

            # Execute method and cache response
            response = method(self, request, *args, **kwargs)

            # Only cache successful responses
            if isinstance(response, Response) and 200 <= response.status_code < 300:
                response["X-Cache"] = "MISS"
                cache.set(cache_key, response, timeout)

            return response

        return wrapper

    return decorator

def cache_page_response(timeout=600, cache_anonymous_only=True):

    Cache decorator for entire page responses.

    Args:
        timeout: Cache timeout in seconds
        cache_anonymous_only: Only cache for anonymous users

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Skip cache for authenticated users if specified
            if cache_anonymous_only and request.user.is_authenticated:
                return view_func(request, *args, **kwargs)

            # Generate cache key
            cache_key = f"page:{request.path}:{request.method}"
            if request.GET:
                cache_key += f":{request.GET.urlencode()}"

            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            # Execute view and cache response
            response = view_func(request, *args, **kwargs)

            # Only cache successful responses
            if response.status_code == 200:
                cache.set(cache_key, response, timeout)

            return response

        return wrapper

    return decorator

def invalidate_cache(pattern=None, exact_key=None):

    Decorator to invalidate cache after method execution.

    Args:
        pattern: Cache key pattern to invalidate
        exact_key: Exact cache key to invalidate

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            # Invalidate cache
            if exact_key:
                cache.delete(exact_key)
            elif pattern:
                # Use cache manager for pattern deletion

                cache_manager.delete_pattern(pattern)

            return result

        return wrapper

    return decorator

def conditional_cache(condition_func, timeout=300):

    Conditionally cache based on a function.

    Args:
        condition_func: Function that returns True if should cache
        timeout: Cache timeout in seconds

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check condition
            should_cache = (
                condition_func(*args, **kwargs)
                if callable(condition_func)
                else condition_func
            )

            if not should_cache:
                return func(*args, **kwargs)

            # Generate cache key
            cache_key = _generate_cache_key(
                prefix=func.__name__, args=args, kwargs=kwargs
            )

            # Try cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result

        return wrapper

    return decorator

def search_cached(timeout=3600):
    """Specific cache decorator for search operations."""
    return cache_response(timeout=timeout, key_prefix="search")

def _generate_cache_key(prefix, args=None, kwargs=None, headers=None):
    """Generate a consistent cache key."""
    key_parts = [prefix]

    if args:
        # Hash args for consistent key
        args_str = json.dumps(
            [str(arg) for arg in args if not isinstance(arg, HttpRequest)]
        )
        key_parts.append(
            hashlib.md5(args_str.encode(), usedforsecurity=False).hexdigest()[:8]
        )

    if kwargs:
        # Hash kwargs for consistent key
        kwargs_str = json.dumps(sorted(kwargs.items()))
        key_parts.append(
            hashlib.md5(kwargs_str.encode(), usedforsecurity=False).hexdigest()[:8]
        )

    if headers:
        # Include headers in key
        for header in headers:
            key_parts.append(f"{header}:{kwargs.get(header, '')}")

    return ":".join(key_parts)

def _is_error_response(response):
    """Check if response is an error."""
    if isinstance(response, Response):
        return response.status_code >= 400
    return False
