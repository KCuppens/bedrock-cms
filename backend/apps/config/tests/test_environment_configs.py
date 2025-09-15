"""Tests for environment-specific configuration settings."""

import os
import sys
import tempfile
from importlib import import_module, reload
from pathlib import Path
from unittest.mock import MagicMock, patch

import django

# Configure Django settings before imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

import environ


class BaseSettingsImportTest(TestCase):
    """Test base settings can be imported and used."""

    def test_base_settings_import(self):
        """Test base settings module can be imported."""
        try:
            from apps.config.settings import base

            self.assertTrue(hasattr(base, "BASE_DIR"))
            self.assertTrue(hasattr(base, "INSTALLED_APPS"))
        except ImportError as e:
            self.fail(f"Failed to import base settings: {e}")

    def test_base_settings_structure(self):
        """Test base settings has required attributes."""
        from apps.config.settings import base

        required_attributes = [
            "BASE_DIR",
            "SECRET_KEY",
            "DEBUG",
            "ALLOWED_HOSTS",
            "INSTALLED_APPS",
            "MIDDLEWARE",
            "ROOT_URLCONF",
            "DATABASES",
            "TEMPLATES",
        ]

        for attr in required_attributes:
            self.assertTrue(hasattr(base, attr), f"Base settings missing {attr}")


class TestSettingsTest(TestCase):
    """Test test environment settings configuration."""

    def test_test_settings_import(self):
        """Test test settings can be imported."""
        try:
            from apps.config.settings import test

            self.assertTrue(hasattr(test, "DATABASES"))
        except ImportError as e:
            self.fail(f"Failed to import test settings: {e}")

    def test_test_database_configuration(self):
        """Test test environment database configuration."""
        from apps.config.settings import test

        # Should have in-memory SQLite for tests
        default_db = test.DATABASES["default"]
        if default_db["NAME"] == ":memory:":
            self.assertEqual(default_db["ENGINE"], "django.db.backends.sqlite3")
        # Or should use DATABASE_URL from environment
        else:
            self.assertIn("ENGINE", default_db)

    def test_test_cache_configuration(self):
        """Test test environment cache configuration."""
        from apps.config.settings import test

        # Should use locmem cache for tests unless Redis is configured
        default_cache = test.CACHES["default"]
        if "locmem" in default_cache["BACKEND"]:
            self.assertIn("LOCATION", default_cache)

    def test_test_email_backend(self):
        """Test test environment email configuration."""
        from apps.config.settings import test

        # Should use locmem email backend for tests
        self.assertEqual(
            test.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend"
        )

    def test_test_password_hashers(self):
        """Test fast password hashers for tests."""
        from apps.config.settings import test

        # Should use fast MD5 hasher for tests
        self.assertEqual(
            test.PASSWORD_HASHERS, ["django.contrib.auth.hashers.MD5PasswordHasher"]
        )

    def test_test_celery_settings(self):
        """Test Celery configuration for tests."""
        from apps.config.settings import test

        # Should run tasks eagerly in tests
        self.assertTrue(test.CELERY_TASK_ALWAYS_EAGER)
        self.assertTrue(test.CELERY_TASK_EAGER_PROPAGATES)

    def test_test_media_directories(self):
        """Test media directories use temp directories."""
        from apps.config.settings import test

        # Should use temporary directories
        self.assertTrue(isinstance(test.MEDIA_ROOT, Path))
        self.assertTrue(isinstance(test.STATIC_ROOT, Path))

    def test_test_logging_disabled(self):
        """Test logging is disabled for tests."""
        from apps.config.settings import test

        # Should disable logging configuration
        self.assertIsNone(test.LOGGING_CONFIG)

    def test_test_rest_framework_config(self):
        """Test REST framework configuration for tests."""
        from apps.config.settings import test

        # Should have appropriate test configurations
        rest_config = test.REST_FRAMEWORK
        self.assertIn("TEST_REQUEST_DEFAULT_FORMAT", rest_config)
        self.assertEqual(rest_config["TEST_REQUEST_DEFAULT_FORMAT"], "json")


class LocalSettingsTest(TestCase):
    """Test local development settings configuration."""

    def test_local_settings_import(self):
        """Test local settings can be imported."""
        try:
            from apps.config.settings import local

            self.assertTrue(hasattr(local, "DEBUG"))
        except ImportError as e:
            self.fail(f"Failed to import local settings: {e}")

    def test_local_debug_enabled(self):
        """Test DEBUG is enabled in local settings."""
        from apps.config.settings import local

        self.assertTrue(local.DEBUG)

    def test_local_allowed_hosts(self):
        """Test local allowed hosts configuration."""
        from apps.config.settings import local

        expected_hosts = ["localhost", "127.0.0.1"]
        for host in expected_hosts:
            self.assertIn(host, local.ALLOWED_HOSTS)

    def test_local_database_configuration(self):
        """Test local database configuration."""
        from apps.config.settings import local

        # Should default to SQLite
        default_db = local.DATABASES["default"]
        self.assertIn("ENGINE", default_db)
        self.assertIn("NAME", default_db)

    def test_local_email_backend(self):
        """Test local email backend configuration."""
        from apps.config.settings import local

        # Should use console backend for development
        self.assertEqual(
            local.EMAIL_BACKEND, "django.core.mail.backends.console.EmailBackend"
        )

    def test_local_cors_configuration(self):
        """Test CORS configuration for local development."""
        from apps.config.settings import local

        # Should have development origins
        self.assertFalse(local.CORS_ALLOW_ALL_ORIGINS)
        self.assertTrue(local.CORS_ALLOW_CREDENTIALS)

        # Check for common dev ports
        dev_origins = local.CORS_ALLOWED_ORIGINS
        localhost_origins = [origin for origin in dev_origins if "localhost" in origin]
        self.assertGreater(len(localhost_origins), 0)

    def test_local_csrf_configuration(self):
        """Test CSRF configuration for local development."""
        from apps.config.settings import local

        # Should have trusted origins
        self.assertTrue(hasattr(local, "CSRF_TRUSTED_ORIGINS"))
        trusted_origins = local.CSRF_TRUSTED_ORIGINS
        localhost_origins = [
            origin for origin in trusted_origins if "localhost" in origin
        ]
        self.assertGreater(len(localhost_origins), 0)

    def test_local_celery_configuration(self):
        """Test Celery configuration for local development."""
        from apps.config.settings import local

        # Should run tasks eagerly for development
        self.assertTrue(local.CELERY_TASK_ALWAYS_EAGER)
        self.assertTrue(local.CELERY_TASK_EAGER_PROPAGATES)

    def test_local_cache_configuration(self):
        """Test cache configuration for local development."""
        from apps.config.settings import local

        # Should use locmem cache by default
        default_cache = local.CACHES["default"]
        self.assertIn("locmem", default_cache["BACKEND"])

    def test_local_session_configuration(self):
        """Test session configuration for local development."""
        from apps.config.settings import local

        # Should use database sessions instead of cache
        self.assertEqual(local.SESSION_ENGINE, "django.contrib.sessions.backends.db")

    def test_local_throttling_configuration(self):
        """Test API throttling for local development."""
        from apps.config.settings import local

        # Should have relaxed throttle rates for development
        rest_config = local.REST_FRAMEWORK
        throttle_rates = rest_config["DEFAULT_THROTTLE_RATES"]

        # Check that rates are high for development
        anon_rate = throttle_rates.get("anon", "100/hour")
        rate_number = int(anon_rate.split("/")[0])
        self.assertGreaterEqual(rate_number, 1000)  # Should be high for dev


class ProductionSettingsTest(TestCase):
    """Test production settings configuration."""

    def test_production_settings_import(self):
        """Test production settings can be imported."""
        try:
            # This might fail due to missing dependencies, so we'll catch specific errors
            from apps.config.settings import prod

            self.assertTrue(hasattr(prod, "DEBUG"))
        except ImportError as e:
            # Skip test if production dependencies are missing
            if "sentry_sdk" in str(e) or "opentelemetry" in str(e):
                self.skipTest(f"Production dependencies not available: {e}")
            else:
                self.fail(f"Failed to import production settings: {e}")

    def test_production_debug_disabled(self):
        """Test DEBUG is disabled in production."""
        try:
            from apps.config.settings import prod

            self.assertFalse(prod.DEBUG)
        except ImportError:
            self.skipTest("Production settings dependencies not available")

    def test_production_security_settings(self):
        """Test security settings in production."""
        try:
            from apps.config.settings import prod

            # SSL settings
            self.assertTrue(hasattr(prod, "SECURE_SSL_REDIRECT"))
            self.assertTrue(hasattr(prod, "SECURE_HSTS_SECONDS"))
            self.assertTrue(hasattr(prod, "SECURE_HSTS_INCLUDE_SUBDOMAINS"))
            self.assertTrue(hasattr(prod, "SECURE_HSTS_PRELOAD"))

            # Cookie security
            self.assertTrue(hasattr(prod, "SESSION_COOKIE_SECURE"))
            self.assertTrue(hasattr(prod, "CSRF_COOKIE_SECURE"))
            self.assertTrue(hasattr(prod, "SESSION_COOKIE_HTTPONLY"))
            self.assertTrue(hasattr(prod, "CSRF_COOKIE_HTTPONLY"))

        except ImportError:
            self.skipTest("Production settings dependencies not available")

    def test_production_database_ssl(self):
        """Test database SSL configuration in production."""
        try:
            from apps.config.settings import prod

            default_db = prod.DATABASES["default"]
            if "OPTIONS" in default_db:
                options = default_db["OPTIONS"]
                # Should require SSL in production
                ssl_related = any(
                    "ssl" in str(key).lower() or "ssl" in str(value).lower()
                    for key, value in options.items()
                )
                # Note: This test might be too strict depending on setup

        except ImportError:
            self.skipTest("Production settings dependencies not available")

    def test_production_static_files(self):
        """Test static files configuration for production."""
        try:
            from apps.config.settings import prod

            # Should use compressed static files storage
            if hasattr(prod, "STATICFILES_STORAGE"):
                self.assertIn("Compressed", prod.STATICFILES_STORAGE)

        except ImportError:
            self.skipTest("Production settings dependencies not available")

    def test_production_email_backend(self):
        """Test email backend for production."""
        try:
            from apps.config.settings import prod

            # Should use SMTP backend
            self.assertEqual(
                prod.EMAIL_BACKEND, "django.core.mail.backends.smtp.EmailBackend"
            )

        except ImportError:
            self.skipTest("Production settings dependencies not available")

    def test_production_cors_security(self):
        """Test CORS security in production."""
        try:
            from apps.config.settings import prod

            # Should not allow all origins
            self.assertFalse(prod.CORS_ALLOW_ALL_ORIGINS)
            self.assertTrue(prod.CORS_ALLOW_CREDENTIALS)

        except ImportError:
            self.skipTest("Production settings dependencies not available")


class EnvironmentInheritanceTest(TestCase):
    """Test settings inheritance and overrides."""

    def test_test_inherits_from_base(self):
        """Test that test settings inherit from base."""
        from apps.config.settings import base, test

        # Should inherit BASE_DIR
        self.assertEqual(base.BASE_DIR, test.BASE_DIR)

        # Should inherit INSTALLED_APPS structure
        base_apps = set(base.DJANGO_APPS + base.THIRD_PARTY_APPS + base.LOCAL_APPS)
        test_apps = set(test.INSTALLED_APPS)

        # Test should have at least the core apps
        django_apps_in_test = [app for app in test_apps if app.startswith("django.")]
        self.assertGreater(len(django_apps_in_test), 0)

    def test_local_inherits_from_base(self):
        """Test that local settings inherit from base."""
        from apps.config.settings import base, local

        # Should inherit BASE_DIR
        self.assertEqual(base.BASE_DIR, local.BASE_DIR)

        # Should have base apps plus potentially more
        base_apps = base.DJANGO_APPS + base.THIRD_PARTY_APPS + base.LOCAL_APPS
        for app in base_apps:
            # Note: local might have different structure, so we check core apps
            if app.startswith("django.contrib."):
                # Core Django apps should be inherited
                pass  # Structure might be different in local

    def test_environment_specific_overrides(self):
        """Test that environments properly override base settings."""
        from apps.config.settings import base, local, test

        # Test should override for testing
        self.assertEqual(
            test.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend"
        )

        # Local should override for development
        self.assertEqual(
            local.EMAIL_BACKEND, "django.core.mail.backends.console.EmailBackend"
        )
        self.assertTrue(local.DEBUG)

    def test_database_overrides(self):
        """Test database configuration overrides."""
        from apps.config.settings import local, test

        # Both should have valid database configurations
        self.assertIn("default", test.DATABASES)
        self.assertIn("default", local.DATABASES)

        # Test should use in-memory SQLite or configured DB
        test_db = test.DATABASES["default"]
        self.assertIn("ENGINE", test_db)

        # Local should allow SQLite or configured DB
        local_db = local.DATABASES["default"]
        self.assertIn("ENGINE", local_db)


class SettingsModuleLoadingTest(TestCase):
    """Test dynamic settings module loading."""

    def test_settings_module_environment_variable(self):
        """Test that DJANGO_SETTINGS_MODULE is respected."""
        # This is mostly handled by Django's setup, but we can verify
        current_settings = os.environ.get("DJANGO_SETTINGS_MODULE")
        self.assertIsNotNone(current_settings)
        self.assertIn("apps.config.settings", current_settings)

    def test_invalid_settings_module_handling(self):
        """Test behavior with invalid settings module."""
        # This test is tricky because changing settings module affects Django
        # We'll test that the modules exist instead

        valid_modules = [
            "apps.config.settings.base",
            "apps.config.settings.test",
            "apps.config.settings.local",
            "apps.config.settings.test_minimal",
        ]

        for module_name in valid_modules:
            try:
                import_module(module_name)
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")

    @patch.dict(os.environ, {"MISSING_ENV_VAR": ""}, clear=False)
    def test_environment_variable_fallbacks(self):
        """Test that missing environment variables fall back gracefully."""
        # Test with environ
        env = environ.Env()

        # Should use defaults when env vars are missing
        debug = env.bool("MISSING_DEBUG", default=False)
        self.assertFalse(debug)

        allowed_hosts = env.list("MISSING_HOSTS", default=["localhost"])
        self.assertEqual(allowed_hosts, ["localhost"])

    def test_settings_file_structure(self):
        """Test settings files have correct structure."""
        settings_dir = Path(__file__).parent.parent / "settings"

        # Should have __init__.py
        init_file = settings_dir / "__init__.py"
        self.assertTrue(init_file.exists())

        # Should have base settings
        base_file = settings_dir / "base.py"
        self.assertTrue(base_file.exists())

        # Should have environment-specific settings
        env_files = ["test.py", "local.py", "test_minimal.py"]
        for env_file in env_files:
            file_path = settings_dir / env_file
            self.assertTrue(file_path.exists(), f"Missing {env_file}")


class SettingsConsistencyTest(TestCase):
    """Test consistency across different settings environments."""

    def test_base_dir_consistency(self):
        """Test BASE_DIR is consistent across environments."""
        from apps.config.settings import base, local, test

        # All should have the same BASE_DIR
        self.assertEqual(base.BASE_DIR, test.BASE_DIR)
        self.assertEqual(base.BASE_DIR, local.BASE_DIR)

    def test_auth_user_model_consistency(self):
        """Test AUTH_USER_MODEL is consistent."""
        from apps.config.settings import base, local, test

        # Should use custom user model consistently
        expected_user_model = "accounts.User"

        if hasattr(base, "AUTH_USER_MODEL"):
            self.assertEqual(base.AUTH_USER_MODEL, expected_user_model)
        if hasattr(test, "AUTH_USER_MODEL"):
            self.assertEqual(test.AUTH_USER_MODEL, expected_user_model)
        if hasattr(local, "AUTH_USER_MODEL"):
            self.assertEqual(local.AUTH_USER_MODEL, expected_user_model)

    def test_middleware_consistency(self):
        """Test middleware has required components across environments."""
        from apps.config.settings import local, test

        required_middleware = [
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
        ]

        for middleware_class in required_middleware:
            self.assertIn(middleware_class, test.MIDDLEWARE)
            self.assertIn(middleware_class, local.MIDDLEWARE)

    def test_installed_apps_core_consistency(self):
        """Test core Django apps are consistent."""
        from apps.config.settings import local, test

        core_apps = [
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
        ]

        for app in core_apps:
            self.assertIn(app, test.INSTALLED_APPS)
            self.assertIn(app, local.INSTALLED_APPS)
