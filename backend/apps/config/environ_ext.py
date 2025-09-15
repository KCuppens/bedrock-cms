"""Extended environ functionality to support additional cache and email schemes."""

import environ


class ExtendedEnv(environ.Env):
    """Extended Env class with support for additional cache schemes."""

    def cache(self, var="CACHE_URL", cache_url=None, backend=None, **options):
        """Parse cache URLs with support for additional schemes."""
        if cache_url:
            url = cache_url
        else:
            try:
                url = self.get_value(var, cast=str)
            except (KeyError, environ.ImproperlyConfigured):
                url = None

        if not url:
            return super().cache(var, cache_url, backend, **options)

        # Handle additional cache schemes
        if url.startswith("dummy://"):
            return {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        elif url.startswith("locmem://"):
            return {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "unique-snowflake",
            }
        elif url.startswith("memcached://"):
            # Parse memcached URL
            from urllib.parse import urlparse

            parsed = urlparse(url)
            location = f"{parsed.hostname}:{parsed.port or 11211}"
            return {
                "BACKEND": "django.core.cache.backends.memcached.PyMemcacheCache",
                "LOCATION": location,
            }
        else:
            # Fall back to parent implementation for redis:// etc
            return super().cache(var, cache_url, backend, **options)

    def email_url(self, var="EMAIL_URL", backend=None, **options):
        """Parse email URLs with support for console scheme."""
        try:
            url = self.get_value(var, cast=str)
        except (KeyError, environ.ImproperlyConfigured):
            url = None

        if not url:
            # Try parent implementation
            try:
                return super().email_url(var, backend, **options)
            except AttributeError:
                # Method doesn't exist in parent, return default
                return {
                    "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend",
                }

        # Handle console:// scheme
        if url.startswith("console://"):
            return {
                "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend",
            }
        else:
            # Try parent implementation
            try:
                return super().email_url(var, backend, **options)
            except (AttributeError, Exception):
                # Fall back to parsing manually
                from urllib.parse import urlparse

                parsed = urlparse(url)

                if parsed.scheme in ("smtp", "smtps"):
                    config = {
                        "EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                        "EMAIL_HOST": parsed.hostname,
                        "EMAIL_PORT": parsed.port
                        or (465 if parsed.scheme == "smtps" else 587),
                        "EMAIL_USE_TLS": parsed.scheme == "smtp",
                        "EMAIL_USE_SSL": parsed.scheme == "smtps",
                    }
                    if parsed.username:
                        config["EMAIL_HOST_USER"] = parsed.username
                    if parsed.password:
                        config["EMAIL_HOST_PASSWORD"] = parsed.password
                    return config
                else:
                    return {
                        "EMAIL_BACKEND": "django.core.mail.backends.console.EmailBackend",
                    }
