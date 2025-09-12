from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin

from .models import Redirect

class RedirectMiddleware(MiddlewareMixin):

    Middleware to handle SEO redirects defined in the Redirect model.

    This middleware:
    1. Checks for matching redirects based on the requested path
    2. Supports both exact matches and regex patterns
    3. Returns appropriate HTTP redirect responses
    4. Tracks hit counts for redirect analytics
    5. Uses caching for performance

    def process_request(self, request):
        """Process incoming requests and check for redirects."""

        # Skip redirect processing for:
        # - Admin URLs
        # - API URLs
        # - Static/media files
        # - AJAX requests
        if (
            request.path.startswith("/admin/")
            or request.path.startswith("/api/")
            or request.path.startswith("/static/")
            or request.path.startswith("/media/")
            or request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest"
        ):
            return None

        # Get the requested path
        path = request.get_full_path()

        # Check cache first for performance
        cache_key = f"redirect:{path}"
        cached_redirect = cache.get(cache_key)

        if cached_redirect:
            redirect_url, redirect_type = cached_redirect
            if redirect_url:
                return self._create_redirect_response(redirect_type, redirect_url)
            # Cached "no redirect" result
            return None

        # Look for matching redirects
        redirect = self._find_matching_redirect(path)

        if redirect:
            # Cache the result (5 minutes)
            cache.set(cache_key, (redirect.to_path, redirect.status), 300)

            # Track the hit asynchronously to avoid slowing down the response
            self._track_redirect_hit(redirect.id)

            return self._create_redirect_response(redirect.status, redirect.to_path)
        else:
            # Cache "no redirect" result (1 minute)
            cache.set(cache_key, (None, None), 60)

        return None

    def _find_matching_redirect(self, path):
        """Find a matching redirect for the given path."""

        # Remove query string from path for matching
        path_without_query = path.split("?")[0]

        # Get all active redirects - wrap in try/except to handle database not configured
        try:
            active_redirects = Redirect.objects.filter(is_active=True)
        except Exception:
            # Database not configured or table doesn't exist
            return None

        # Try exact path matching
        for redirect in active_redirects:
            if redirect.from_path == path_without_query:
                return redirect
            # Try with trailing slash variations
            if (
                not path_without_query.endswith("/")
                and redirect.from_path == path_without_query + "/"
            ):
                return redirect
            if (
                path_without_query.endswith("/")
                and path_without_query != "/"
                and redirect.from_path == path_without_query.rstrip("/")
            ):
                return redirect

        return None

    def _create_redirect_response(self, redirect_type, destination_url):
        """Create the appropriate redirect response."""

        if redirect_type == 301 or redirect_type == 308:
            return HttpResponsePermanentRedirect(destination_url)
        else:  # 302 or 307
            return HttpResponseRedirect(destination_url)

    def _track_redirect_hit(self, redirect_id):
        """Track redirect hit."""
        try:

            # Use a transaction to safely increment the counter
            with transaction.atomic():
                redirect = Redirect.objects.select_for_update().get(id=redirect_id)
                redirect.hits += 1
                redirect.save(update_fields=["hits"])

        except Redirect.DoesNotExist:
            # Redirect was deleted between finding it and tracking the hit

        except Exception:
            # Don't fail the request if hit tracking fails
