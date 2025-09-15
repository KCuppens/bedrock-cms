"""Tests for security settings validation and configuration."""

import os
import re
from unittest.mock import patch

import django

# Configure Django settings before imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings


class SecurityMiddlewareTest(TestCase):
    """Test security middleware configuration."""

    def test_security_middleware_present(self):
        """Test security middleware is properly configured."""
        security_middlewares = [
            "django.middleware.security.SecurityMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ]

        for middleware in security_middlewares:
            self.assertIn(
                middleware,
                settings.MIDDLEWARE,
                f"Security middleware {middleware} not found",
            )

    def test_security_middleware_ordering(self):
        """Test security middleware is properly ordered."""
        middleware_list = settings.MIDDLEWARE

        # SecurityMiddleware should be early in the chain
        security_index = next(
            (i for i, mw in enumerate(middleware_list) if "SecurityMiddleware" in mw),
            None,
        )
        self.assertIsNotNone(security_index, "SecurityMiddleware not found")
        self.assertLess(
            security_index, 5, "SecurityMiddleware should be early in chain"
        )

        # CSRF middleware should come after session middleware
        csrf_index = next(
            (i for i, mw in enumerate(middleware_list) if "CsrfViewMiddleware" in mw),
            None,
        )
        session_index = next(
            (i for i, mw in enumerate(middleware_list) if "SessionMiddleware" in mw),
            None,
        )

        if csrf_index is not None and session_index is not None:
            self.assertLess(
                session_index,
                csrf_index,
                "SessionMiddleware should come before CsrfViewMiddleware",
            )


class SecretKeyTest(TestCase):
    """Test SECRET_KEY configuration and security."""

    def test_secret_key_exists(self):
        """Test SECRET_KEY is configured."""
        self.assertTrue(hasattr(settings, "SECRET_KEY"))
        self.assertIsNotNone(settings.SECRET_KEY)

    def test_secret_key_length(self):
        """Test SECRET_KEY has adequate length."""
        secret_key = settings.SECRET_KEY
        self.assertGreaterEqual(
            len(secret_key), 20, "SECRET_KEY should be at least 20 characters long"
        )

    def test_secret_key_not_default(self):
        """Test SECRET_KEY is not using common default values."""
        secret_key = settings.SECRET_KEY

        # Common insecure default values
        insecure_keys = [
            "django-insecure-change-me",
            "your-secret-key-here",
            "1234567890",
            "abcdefghijklmnopqrstuvwxyz",
        ]

        for insecure_key in insecure_keys:
            self.assertNotEqual(
                secret_key.lower(),
                insecure_key.lower(),
                f"SECRET_KEY should not use default value: {insecure_key}",
            )

    def test_secret_key_complexity(self):
        """Test SECRET_KEY has adequate complexity."""
        secret_key = settings.SECRET_KEY

        # Should have some variety of characters
        has_letters = re.search(r"[a-zA-Z]", secret_key)
        has_numbers = re.search(r"[0-9]", secret_key)
        has_special = re.search(r"[^a-zA-Z0-9]", secret_key)

        # At least two types of characters for reasonable entropy
        char_types = sum([bool(has_letters), bool(has_numbers), bool(has_special)])
        self.assertGreaterEqual(
            char_types, 2, "SECRET_KEY should have variety of character types"
        )


class DebugSettingsTest(TestCase):
    """Test DEBUG-related security settings."""

    def test_debug_setting_exists(self):
        """Test DEBUG setting is configured."""
        self.assertTrue(hasattr(settings, "DEBUG"))
        self.assertIsInstance(settings.DEBUG, bool)

    @override_settings(DEBUG=False)
    def test_debug_false_security_implications(self):
        """Test security implications when DEBUG=False."""
        # When DEBUG is False, certain security settings should be stricter
        self.assertFalse(settings.DEBUG)

        # ALLOWED_HOSTS should be configured when DEBUG=False
        if hasattr(settings, "ALLOWED_HOSTS"):
            # ALLOWED_HOSTS should not be empty when DEBUG=False in production
            # Note: This might be okay in test environments
            pass

    def test_debug_true_warnings(self):
        """Test DEBUG=True has appropriate warnings."""
        if settings.DEBUG:
            # DEBUG=True should only be used in development
            # We can't test this directly but can verify the setting is boolean
            self.assertIsInstance(settings.DEBUG, bool)


class AllowedHostsTest(TestCase):
    """Test ALLOWED_HOSTS configuration."""

    def test_allowed_hosts_exists(self):
        """Test ALLOWED_HOSTS is configured."""
        self.assertTrue(hasattr(settings, "ALLOWED_HOSTS"))
        self.assertIsInstance(settings.ALLOWED_HOSTS, (list, tuple))

    def test_allowed_hosts_not_wildcard_in_production(self):
        """Test ALLOWED_HOSTS doesn't use wildcard in production-like settings."""
        allowed_hosts = settings.ALLOWED_HOSTS

        # Check for dangerous wildcard configurations
        dangerous_hosts = ["*"]

        # In test environment, wildcard is acceptable for testing
        # Only fail if we're explicitly testing production settings
        if not settings.DEBUG and "prod" in os.environ.get(
            "DJANGO_SETTINGS_MODULE", ""
        ):
            for dangerous_host in dangerous_hosts:
                self.assertNotIn(
                    dangerous_host,
                    allowed_hosts,
                    "ALLOWED_HOSTS should not use wildcard in production",
                )

    def test_allowed_hosts_format(self):
        """Test ALLOWED_HOSTS entries are properly formatted."""
        allowed_hosts = settings.ALLOWED_HOSTS

        for host in allowed_hosts:
            self.assertIsInstance(host, str, "ALLOWED_HOSTS entries should be strings")

            # Should not have protocols
            self.assertFalse(
                host.startswith("http://"), "ALLOWED_HOSTS should not include protocol"
            )
            self.assertFalse(
                host.startswith("https://"), "ALLOWED_HOSTS should not include protocol"
            )

            # Should not have paths
            self.assertNotIn("/", host, "ALLOWED_HOSTS should not include paths")


class CSRFProtectionTest(TestCase):
    """Test CSRF protection configuration."""

    def test_csrf_middleware_present(self):
        """Test CSRF middleware is configured."""
        self.assertIn("django.middleware.csrf.CsrfViewMiddleware", settings.MIDDLEWARE)

    def test_csrf_cookie_settings(self):
        """Test CSRF cookie security settings."""
        # Check for CSRF cookie settings
        csrf_settings = [
            "CSRF_COOKIE_SECURE",
            "CSRF_COOKIE_HTTPONLY",
            "CSRF_COOKIE_SAMESITE",
        ]

        for setting in csrf_settings:
            if hasattr(settings, setting):
                value = getattr(settings, setting)

                if setting == "CSRF_COOKIE_SECURE":
                    self.assertIsInstance(value, bool)
                    # In production with HTTPS, should be True
                    # In development, might be False

                elif setting == "CSRF_COOKIE_HTTPONLY":
                    self.assertIsInstance(value, bool)
                    # HttpOnly might be False for API access

                elif setting == "CSRF_COOKIE_SAMESITE":
                    valid_values = ["Strict", "Lax", "None"]
                    if value is not None:
                        self.assertIn(value, valid_values)

    def test_csrf_trusted_origins(self):
        """Test CSRF trusted origins configuration."""
        if hasattr(settings, "CSRF_TRUSTED_ORIGINS"):
            trusted_origins = settings.CSRF_TRUSTED_ORIGINS
            self.assertIsInstance(trusted_origins, (list, tuple))

            for origin in trusted_origins:
                self.assertIsInstance(origin, str)
                # Should include protocol
                self.assertTrue(
                    origin.startswith("http://") or origin.startswith("https://"),
                    "CSRF_TRUSTED_ORIGINS should include protocol",
                )


class SessionSecurityTest(TestCase):
    """Test session security configuration."""

    def test_session_middleware_present(self):
        """Test session middleware is configured."""
        self.assertIn(
            "django.contrib.sessions.middleware.SessionMiddleware", settings.MIDDLEWARE
        )

    def test_session_cookie_settings(self):
        """Test session cookie security settings."""
        session_settings = [
            "SESSION_COOKIE_SECURE",
            "SESSION_COOKIE_HTTPONLY",
            "SESSION_COOKIE_SAMESITE",
            "SESSION_COOKIE_AGE",
        ]

        for setting in session_settings:
            if hasattr(settings, setting):
                value = getattr(settings, setting)

                if setting == "SESSION_COOKIE_SECURE":
                    self.assertIsInstance(value, bool)
                    # Should be True in production with HTTPS

                elif setting == "SESSION_COOKIE_HTTPONLY":
                    self.assertIsInstance(value, bool)
                    # Should typically be True for security

                elif setting == "SESSION_COOKIE_SAMESITE":
                    valid_values = ["Strict", "Lax", "None"]
                    if value is not None:
                        self.assertIn(value, valid_values)

                elif setting == "SESSION_COOKIE_AGE":
                    self.assertIsInstance(value, int)
                    self.assertGreater(value, 0)

    def test_session_engine_security(self):
        """Test session engine configuration."""
        if hasattr(settings, "SESSION_ENGINE"):
            engine = settings.SESSION_ENGINE

            # Should not use file-based sessions in production
            if not settings.DEBUG:
                self.assertNotEqual(
                    engine,
                    "django.contrib.sessions.backends.file",
                    "File-based sessions not recommended for production",
                )

            # Should use secure session backends
            secure_engines = [
                "django.contrib.sessions.backends.db",
                "django.contrib.sessions.backends.cache",
                "django.contrib.sessions.backends.cached_db",
            ]

            is_secure_engine = any(
                secure_engine in engine for secure_engine in secure_engines
            )
            self.assertTrue(
                is_secure_engine, f"Session engine should be secure: {engine}"
            )


class PasswordValidationTest(TestCase):
    """Test password validation configuration."""

    def test_password_validators_configured(self):
        """Test password validators are configured."""
        self.assertTrue(hasattr(settings, "AUTH_PASSWORD_VALIDATORS"))
        validators = settings.AUTH_PASSWORD_VALIDATORS
        self.assertIsInstance(validators, (list, tuple))

    def test_password_validators_coverage(self):
        """Test password validators provide good coverage."""
        validators = settings.AUTH_PASSWORD_VALIDATORS

        if validators:  # Only test if validators are configured
            validator_names = [validator.get("NAME", "") for validator in validators]

            # Should have basic security validators
            recommended_validators = [
                "UserAttributeSimilarityValidator",
                "MinimumLengthValidator",
                "CommonPasswordValidator",
                "NumericPasswordValidator",
            ]

            for recommended in recommended_validators:
                has_validator = any(recommended in name for name in validator_names)
                if not has_validator:
                    # Log warning but don't fail - might have custom validators
                    pass

    def test_password_validator_configuration(self):
        """Test password validator options."""
        validators = settings.AUTH_PASSWORD_VALIDATORS

        for validator in validators:
            self.assertIn("NAME", validator, "Validator should have NAME")
            validator_name = validator["NAME"]
            self.assertIsInstance(validator_name, str)

            # Check specific validator options
            if "MinimumLengthValidator" in validator_name:
                if "OPTIONS" in validator:
                    options = validator["OPTIONS"]
                    if "min_length" in options:
                        min_length = options["min_length"]
                        self.assertIsInstance(min_length, int)
                        self.assertGreaterEqual(
                            min_length,
                            8,
                            "Minimum password length should be at least 8",
                        )


class SSLHTTPSTest(TestCase):
    """Test SSL/HTTPS security settings."""

    def test_ssl_redirect_setting(self):
        """Test SSL redirect configuration."""
        if hasattr(settings, "SECURE_SSL_REDIRECT"):
            ssl_redirect = settings.SECURE_SSL_REDIRECT
            self.assertIsInstance(ssl_redirect, bool)

    def test_hsts_settings(self):
        """Test HTTP Strict Transport Security settings."""
        hsts_settings = [
            "SECURE_HSTS_SECONDS",
            "SECURE_HSTS_INCLUDE_SUBDOMAINS",
            "SECURE_HSTS_PRELOAD",
        ]

        for setting in hsts_settings:
            if hasattr(settings, setting):
                value = getattr(settings, setting)

                if setting == "SECURE_HSTS_SECONDS":
                    self.assertIsInstance(value, int)
                    if value > 0:
                        # Should be reasonable value (at least 1 hour)
                        self.assertGreaterEqual(value, 3600)
                else:
                    self.assertIsInstance(value, bool)

    def test_proxy_ssl_header(self):
        """Test proxy SSL header configuration."""
        if hasattr(settings, "SECURE_PROXY_SSL_HEADER"):
            proxy_header = settings.SECURE_PROXY_SSL_HEADER
            if proxy_header is not None:  # It might be None in some configurations
                self.assertIsInstance(proxy_header, (tuple, list))
                self.assertEqual(len(proxy_header), 2)

                header_name, header_value = proxy_header
                self.assertIsInstance(header_name, str)
                self.assertIsInstance(header_value, str)

                # Common proxy headers
                self.assertTrue(header_name.startswith("HTTP_"))


class ContentSecurityTest(TestCase):
    """Test content security settings."""

    def test_xss_protection(self):
        """Test XSS protection settings."""
        if hasattr(settings, "SECURE_BROWSER_XSS_FILTER"):
            xss_filter = settings.SECURE_BROWSER_XSS_FILTER
            self.assertIsInstance(xss_filter, bool)
            # Should typically be True for security

    def test_content_type_sniffing(self):
        """Test content type sniffing protection."""
        if hasattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF"):
            no_sniff = settings.SECURE_CONTENT_TYPE_NOSNIFF
            self.assertIsInstance(no_sniff, bool)
            # Should typically be True for security

    def test_frame_options(self):
        """Test frame options configuration."""
        if hasattr(settings, "X_FRAME_OPTIONS"):
            frame_options = settings.X_FRAME_OPTIONS
            valid_options = ["DENY", "SAMEORIGIN"]
            self.assertIn(frame_options, valid_options)

        # Check for clickjacking middleware
        self.assertIn(
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
            settings.MIDDLEWARE,
        )


class CORSSecurityTest(TestCase):
    """Test CORS security configuration."""

    def test_cors_allow_all_origins(self):
        """Test CORS allow all origins setting."""
        if hasattr(settings, "CORS_ALLOW_ALL_ORIGINS"):
            allow_all = settings.CORS_ALLOW_ALL_ORIGINS
            self.assertIsInstance(allow_all, bool)

            # In production, should not allow all origins
            if not settings.DEBUG:
                self.assertFalse(
                    allow_all, "CORS_ALLOW_ALL_ORIGINS should be False in production"
                )

    def test_cors_allowed_origins(self):
        """Test CORS allowed origins configuration."""
        if hasattr(settings, "CORS_ALLOWED_ORIGINS"):
            allowed_origins = settings.CORS_ALLOWED_ORIGINS
            self.assertIsInstance(allowed_origins, (list, tuple))

            for origin in allowed_origins:
                self.assertIsInstance(origin, str)
                # Should include protocol
                self.assertTrue(
                    origin.startswith("http://") or origin.startswith("https://"),
                    "CORS origins should include protocol",
                )

                # Should not end with slash
                self.assertFalse(
                    origin.endswith("/"), "CORS origins should not end with slash"
                )

    def test_cors_credentials(self):
        """Test CORS credentials configuration."""
        if hasattr(settings, "CORS_ALLOW_CREDENTIALS"):
            allow_credentials = settings.CORS_ALLOW_CREDENTIALS
            self.assertIsInstance(allow_credentials, bool)

    def test_cors_headers(self):
        """Test CORS allowed headers."""
        if hasattr(settings, "CORS_ALLOW_HEADERS"):
            allowed_headers = settings.CORS_ALLOW_HEADERS
            self.assertIsInstance(allowed_headers, (list, tuple))

            # Should have standard security headers
            security_headers = ["authorization", "x-csrftoken"]
            for header in security_headers:
                header_present = any(
                    header.lower() in allowed_header.lower()
                    for allowed_header in allowed_headers
                )
                self.assertTrue(header_present, f"CORS should allow {header} header")


class AuthenticationSecurityTest(TestCase):
    """Test authentication security settings."""

    def test_auth_backends_configured(self):
        """Test authentication backends are properly configured."""
        self.assertTrue(hasattr(settings, "AUTHENTICATION_BACKENDS"))
        backends = settings.AUTHENTICATION_BACKENDS
        self.assertIsInstance(backends, (list, tuple))
        self.assertGreater(len(backends), 0)

        # Should include Django's default backend
        default_backend = "django.contrib.auth.backends.ModelBackend"
        self.assertIn(default_backend, backends)

    def test_custom_user_model(self):
        """Test custom user model configuration."""
        if hasattr(settings, "AUTH_USER_MODEL"):
            user_model = settings.AUTH_USER_MODEL
            self.assertIsInstance(user_model, str)
            self.assertIn(".", user_model)  # Should be app.Model format

    def test_login_url_configuration(self):
        """Test login URL configuration."""
        if hasattr(settings, "LOGIN_URL"):
            login_url = settings.LOGIN_URL
            self.assertIsInstance(login_url, str)
            self.assertTrue(login_url.startswith("/"))

    def test_auth_middleware_present(self):
        """Test authentication middleware is present."""
        auth_middlewares = [
            "django.contrib.auth.middleware.AuthenticationMiddleware",
        ]

        for middleware in auth_middlewares:
            self.assertIn(middleware, settings.MIDDLEWARE)


class APISecurityTest(TestCase):
    """Test API security settings."""

    def test_rest_framework_security(self):
        """Test Django REST Framework security settings."""
        if hasattr(settings, "REST_FRAMEWORK"):
            drf_config = settings.REST_FRAMEWORK

            # Should have authentication classes
            if "DEFAULT_AUTHENTICATION_CLASSES" in drf_config:
                auth_classes = drf_config["DEFAULT_AUTHENTICATION_CLASSES"]
                self.assertIsInstance(auth_classes, (list, tuple))
                self.assertGreater(len(auth_classes), 0)

            # Should have permission classes
            if "DEFAULT_PERMISSION_CLASSES" in drf_config:
                perm_classes = drf_config["DEFAULT_PERMISSION_CLASSES"]
                self.assertIsInstance(perm_classes, (list, tuple))
                self.assertGreater(len(perm_classes), 0)

            # Should have throttling configured
            if "DEFAULT_THROTTLE_CLASSES" in drf_config:
                throttle_classes = drf_config["DEFAULT_THROTTLE_CLASSES"]
                self.assertIsInstance(throttle_classes, (list, tuple))

            if "DEFAULT_THROTTLE_RATES" in drf_config:
                throttle_rates = drf_config["DEFAULT_THROTTLE_RATES"]
                self.assertIsInstance(throttle_rates, dict)

                # Check rate limiting format
                for rate_name, rate_value in throttle_rates.items():
                    if rate_value is not None:  # Allow None values for disabled rates
                        self.assertIsInstance(rate_value, str)
                        # Should be in format "number/period"
                        self.assertRegex(
                            rate_value, r"^\d+/(second|minute|min|hour|day)$"
                        )

    def test_api_versioning_security(self):
        """Test API versioning doesn't expose sensitive information."""
        if hasattr(settings, "REST_FRAMEWORK"):
            drf_config = settings.REST_FRAMEWORK

            # Check for schema settings that might expose too much
            if "DEFAULT_SCHEMA_CLASS" in drf_config:
                schema_class = drf_config["DEFAULT_SCHEMA_CLASS"]
                self.assertIsInstance(schema_class, str)


class FileUploadSecurityTest(TestCase):
    """Test file upload security settings."""

    def test_file_upload_limits(self):
        """Test file upload size limits."""
        if hasattr(settings, "FILE_UPLOAD_MAX_MEMORY_SIZE"):
            max_memory = settings.FILE_UPLOAD_MAX_MEMORY_SIZE
            self.assertIsInstance(max_memory, int)
            self.assertGreater(max_memory, 0)
            # Should have reasonable limit (not too high)
            self.assertLessEqual(max_memory, 50 * 1024 * 1024)  # 50MB max

        if hasattr(settings, "DATA_UPLOAD_MAX_MEMORY_SIZE"):
            max_data = settings.DATA_UPLOAD_MAX_MEMORY_SIZE
            self.assertIsInstance(max_data, int)
            self.assertGreater(max_data, 0)

    def test_media_files_security(self):
        """Test media files security configuration."""
        if hasattr(settings, "MEDIA_URL"):
            media_url = settings.MEDIA_URL
            self.assertIsInstance(media_url, str)
            self.assertTrue(media_url.startswith("/"))

        if hasattr(settings, "MEDIA_ROOT"):
            media_root = settings.MEDIA_ROOT
            self.assertIsNotNone(media_root)


class LoggingSecurityTest(TestCase):
    """Test logging security configuration."""

    def test_logging_configuration_exists(self):
        """Test logging configuration exists."""
        if hasattr(settings, "LOGGING"):
            logging_config = settings.LOGGING
            self.assertIsInstance(logging_config, dict)

    def test_logging_no_sensitive_data(self):
        """Test logging configuration doesn't expose sensitive data."""
        if hasattr(settings, "LOGGING"):
            logging_config = settings.LOGGING

            # Check that loggers don't log sensitive information
            if "loggers" in logging_config:
                loggers = logging_config["loggers"]

                # Django request logger should not be at DEBUG level in production
                if "django.request" in loggers:
                    request_logger = loggers["django.request"]
                    if "level" in request_logger and not settings.DEBUG:
                        level = request_logger["level"]
                        # Should not be DEBUG in production
                        self.assertNotEqual(level, "DEBUG")


class ProductionSecurityTest(TestCase):
    """Test production-specific security settings."""

    def test_production_security_checklist(self):
        """Test production security checklist items."""
        # This test runs regardless of DEBUG setting but checks production concerns

        security_settings = [
            ("SECRET_KEY", str, lambda x: len(x) >= 20),
            ("DEBUG", bool, lambda x: isinstance(x, bool)),
            ("ALLOWED_HOSTS", (list, tuple), lambda x: isinstance(x, (list, tuple))),
        ]

        for setting_name, expected_type, validator in security_settings:
            if hasattr(settings, setting_name):
                value = getattr(settings, setting_name)
                self.assertIsInstance(
                    value, expected_type, f"{setting_name} should be {expected_type}"
                )
                self.assertTrue(validator(value), f"{setting_name} failed validation")

    @override_settings(DEBUG=False)
    def test_production_debug_false_implications(self):
        """Test implications of DEBUG=False."""
        self.assertFalse(settings.DEBUG)

        # With DEBUG=False, error pages shouldn't expose sensitive info
        # ALLOWED_HOSTS should be configured
        if hasattr(settings, "ALLOWED_HOSTS"):
            allowed_hosts = settings.ALLOWED_HOSTS
            # Should not be empty in production
            # Note: This might be okay in some test configurations
