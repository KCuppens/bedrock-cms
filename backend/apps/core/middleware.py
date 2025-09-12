import ipaddress

from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Middleware to add security headers"""

    # Cache computed headers at class level
    _cached_headers = None
    _cached_debug_mode = None

    @classmethod
    def _get_cached_headers(cls):
        """Get or compute cached headers"""
        current_debug = settings.DEBUG

        # Recompute if debug mode changed or not cached
        if cls._cached_headers is None or cls._cached_debug_mode != current_debug:
            cls._cached_debug_mode = current_debug
            cls._cached_headers = cls._compute_headers()

        return cls._cached_headers

    @classmethod
    def _compute_headers(cls):
        """Compute security headers once"""
        headers = {}

        # CSP directives
        csp_directives = cls._get_csp_directives()
        headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # Other security headers
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-XSS-Protection"] = "1; mode=block"

        # Permissions Policy
        permissions_policy = [
            "camera=()",
            "microphone=()",
            "geolocation=()",
            "interest-cohort=()",
        ]
        headers["Permissions-Policy"] = ", ".join(permissions_policy)

        return headers

    @classmethod
    def _get_csp_directives(cls):
        """Get CSP directives based on settings"""
        if settings.DEBUG:
            return [
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "img-src 'self' data: https: blob:",
                "connect-src 'self' ws: wss:",
                "style-src 'self' 'unsafe-inline'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            ]
        else:
            return [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net",
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",
                "img-src 'self' data: https:",
                "font-src 'self' https://cdn.jsdelivr.net",
                "connect-src 'self'",
                "media-src 'self'",
                "object-src 'none'",
                "child-src 'none'",
                "worker-src 'none'",
                "frame-ancestors 'none'",
                "form-action 'self'",
                "base-uri 'self'",
                "manifest-src 'self'",
            ]

    def process_response(self, request, response):
        """Add security headers to all responses"""
        # Get cached headers
        headers = self._get_cached_headers()

        # Apply cached headers
        for header, value in headers.items():
            response[header] = value

        # HSTS handling (dynamic based on settings)
        if getattr(settings, "SECURE_SSL_REDIRECT", False):
            max_age = getattr(settings, "SECURE_HSTS_SECONDS", 31536000)
            hsts_header = f"max-age={max_age}"

            if getattr(settings, "SECURE_HSTS_INCLUDE_SUBDOMAINS", True):
                hsts_header += "; includeSubDomains"

            if getattr(settings, "SECURE_HSTS_PRELOAD", True):
                hsts_header += "; preload"

            response["Strict-Transport-Security"] = hsts_header

        # X-Frame-Options (ensure it's there)
        if "X-Frame-Options" not in response:
            response["X-Frame-Options"] = "DENY"

        return response

class AdminIPAllowlistMiddleware(MiddlewareMixin):
    """Middleware to restrict admin access by IP address"""

    def process_request(self, request):
        """Check IP allowlist for admin URLs"""

        # Only check admin URLs
        if not request.path.startswith("/admin"):
            return None

        # Get IP allowlist from settings
        allowed_ips = getattr(settings, "ADMIN_IP_ALLOWLIST", [])

        # If no allowlist configured, allow all
        if not allowed_ips:
            return None

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if IP is in allowlist
        if not self._ip_in_allowlist(client_ip, allowed_ips):
            return HttpResponseForbidden("Access denied: IP not in allowlist")

        return None

    def _get_client_ip(self, request):
        """Get the real client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def _ip_in_allowlist(self, client_ip, allowed_ips):
        """Check if client IP is in the allowlist (supports CIDR notation)"""
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)

            for allowed_ip in allowed_ips:
                try:
                    # Try as network (CIDR notation)
                    if "/" in allowed_ip:
                        network = ipaddress.ip_network(allowed_ip, strict=False)
                        if client_ip_obj in network:
                            return True
                    else:
                        # Try as single IP
                        if client_ip_obj == ipaddress.ip_address(allowed_ip):
                            return True
                except ValueError:
                    # Skip invalid IP/network entries

            return False

        except ValueError:
            # Invalid client IP
            return False

class DemoModeMiddleware(MiddlewareMixin):
    """Middleware to add demo mode banner"""

    def process_response(self, request, response):
        """Add demo mode banner to HTML responses"""

        # Only add banner if DEMO_MODE is enabled
        if not getattr(settings, "DEMO_MODE", False):
            return response

        # Only modify HTML responses
        content_type = response.get("Content-Type", "")
        if "text/html" not in content_type:
            return response

        # Only modify successful responses
        if response.status_code != 200:
            return response

        # Add demo banner to HTML content
        if hasattr(response, "content"):
            # Use escaped content for security
            demo_banner = """
            <div id="demo-banner" style="
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background: #ff6b35;
                color: white;
                text-align: center;
                padding: 8px;
                font-family: sans-serif;
                font-size: 14px;
                font-weight: bold;
                z-index: 10000;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            ">
                🚧 DEMO MODE - This is a demonstration environment
            </div>
            <style>
                body { margin-top: 40px !important; }
            </style>

            try:
                content = response.content.decode("utf-8", errors="ignore")

                # Only insert in valid HTML documents
                if "<!DOCTYPE" in content.upper() and "<body" in content.lower():
                    body_end = content.find(">", content.find("<body"))
                    if body_end != -1:
                        content = (
                            content[: body_end + 1]
                            + demo_banner
                            + content[body_end + 1 :]
                        )
                        response.content = content.encode("utf-8")
                        response["Content-Length"] = len(response.content)
            except Exception:
                # Fail silently if content can't be modified

        return response
