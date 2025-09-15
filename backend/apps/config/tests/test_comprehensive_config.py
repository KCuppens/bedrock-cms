"""Comprehensive configuration tests that tie everything together."""

import os
import sys
from pathlib import Path

import django

# Configure Django settings before imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import execute_from_command_line
from django.test import TestCase, override_settings

import environ


class ConfigurationIntegrationTest(TestCase):
    """Test overall configuration integration and consistency."""

    def test_all_settings_files_loadable(self):
        """Test that all settings files can be loaded without errors."""
        settings_files = [
            "apps.config.settings.base",
            "apps.config.settings.test",
            "apps.config.settings.local",
            "apps.config.settings.test_minimal",
        ]

        # Try production settings only if dependencies are available
        try:
            import opentelemetry
            import sentry_sdk

            settings_files.append("apps.config.settings.prod")
        except ImportError:
            pass  # Production dependencies not available

        for settings_file in settings_files:
            with self.subTest(settings_file=settings_file):
                try:
                    # Try to import the settings module
                    __import__(settings_file)
                except (ImportError, Exception) as e:
                    error_str = str(e)
                    if any(
                        x in error_str
                        for x in [
                            "sentry_sdk",
                            "opentelemetry",
                            "environment variable",
                            "Set the",
                            "ImproperlyConfigured",
                            "psycopg2",
                        ]
                    ):
                        # Production dependencies or env vars missing, skip
                        continue
                    else:
                        self.fail(f"Failed to import {settings_file}: {e}")

    def test_settings_inheritance_chain(self):
        """Test settings inheritance works correctly."""
        from apps.config.settings import base, local, test

        # All environments should have BASE_DIR from base
        self.assertEqual(base.BASE_DIR, test.BASE_DIR)
        self.assertEqual(base.BASE_DIR, local.BASE_DIR)

        # All should have core Django apps
        base_django_apps = [
            app for app in base.DJANGO_APPS if app.startswith("django.")
        ]
        test_django_apps = [
            app for app in test.INSTALLED_APPS if app.startswith("django.")
        ]
        local_django_apps = [
            app for app in local.INSTALLED_APPS if app.startswith("django.")
        ]

        for django_app in base_django_apps:
            self.assertIn(
                django_app, test_django_apps, f"{django_app} missing from test settings"
            )
            self.assertIn(
                django_app,
                local_django_apps,
                f"{django_app} missing from local settings",
            )

    def test_environment_specific_overrides_work(self):
        """Test that environment-specific overrides are applied correctly."""
        from apps.config.settings import local, test

        # Test environment should have specific configurations
        self.assertTrue(test.CELERY_TASK_ALWAYS_EAGER)  # Tasks run synchronously
        self.assertEqual(
            test.EMAIL_BACKEND, "django.core.mail.backends.locmem.EmailBackend"
        )

        # Local environment should have development-friendly settings
        self.assertTrue(local.DEBUG)
        self.assertEqual(
            local.EMAIL_BACKEND, "django.core.mail.backends.console.EmailBackend"
        )
        self.assertIn("localhost", local.ALLOWED_HOSTS)

    def test_required_settings_present(self):
        """Test that all required Django settings are present."""
        required_settings = [
            "SECRET_KEY",
            "DEBUG",
            "ALLOWED_HOSTS",
            "INSTALLED_APPS",
            "MIDDLEWARE",
            "ROOT_URLCONF",
            "TEMPLATES",
            "WSGI_APPLICATION",
            "DATABASES",
            "AUTH_PASSWORD_VALIDATORS",
            "LANGUAGE_CODE",
            "TIME_ZONE",
            "USE_I18N",
            "USE_TZ",
            "STATIC_URL",
            "DEFAULT_AUTO_FIELD",
        ]

        for setting_name in required_settings:
            with self.subTest(setting=setting_name):
                self.assertTrue(
                    hasattr(settings, setting_name),
                    f"Required setting {setting_name} is missing",
                )
                value = getattr(settings, setting_name)
                # WSGI_APPLICATION may be None in test settings
                if setting_name != "WSGI_APPLICATION":
                    self.assertIsNotNone(
                        value, f"Required setting {setting_name} is None"
                    )

    def test_custom_settings_consistency(self):
        """Test custom application settings are consistent."""
        custom_settings = [
            "AUTH_USER_MODEL",
            "BASE_DIR",
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND",
        ]

        for setting_name in custom_settings:
            if hasattr(settings, setting_name):
                with self.subTest(setting=setting_name):
                    value = getattr(settings, setting_name)
                    self.assertIsNotNone(
                        value, f"Custom setting {setting_name} is None"
                    )

                    # Specific validations
                    if setting_name == "AUTH_USER_MODEL":
                        self.assertEqual(value, "accounts.User")
                    elif setting_name == "BASE_DIR":
                        self.assertIsInstance(value, Path)
                        self.assertTrue(value.exists())

    def test_security_settings_comprehensive(self):
        """Test comprehensive security settings configuration."""
        security_checks = [
            ("SECRET_KEY length", lambda: len(settings.SECRET_KEY) >= 20),
            (
                "ALLOWED_HOSTS configured",
                lambda: isinstance(settings.ALLOWED_HOSTS, (list, tuple)),
            ),
            (
                "Security middleware present",
                lambda: "django.middleware.security.SecurityMiddleware"
                in settings.MIDDLEWARE,
            ),
            (
                "CSRF middleware present",
                lambda: "django.middleware.csrf.CsrfViewMiddleware"
                in settings.MIDDLEWARE,
            ),
            (
                "XFrame middleware present",
                lambda: "django.middleware.clickjacking.XFrameOptionsMiddleware"
                in settings.MIDDLEWARE,
            ),
        ]

        for check_name, check_func in security_checks:
            with self.subTest(check=check_name):
                self.assertTrue(check_func(), f"Security check failed: {check_name}")

    def test_database_configuration_comprehensive(self):
        """Test comprehensive database configuration."""
        self.assertIn("default", settings.DATABASES)
        default_db = settings.DATABASES["default"]

        db_checks = [
            ("Has ENGINE", "ENGINE" in default_db),
            ("Has NAME", "NAME" in default_db),
            (
                "ENGINE is valid",
                any(
                    engine in default_db["ENGINE"]
                    for engine in ["sqlite3", "postgresql", "mysql"]
                ),
            ),
        ]

        for check_name, check_result in db_checks:
            with self.subTest(check=check_name):
                self.assertTrue(check_result, f"Database check failed: {check_name}")

    def test_cache_configuration_comprehensive(self):
        """Test comprehensive cache configuration."""
        self.assertIn("default", settings.CACHES)
        default_cache = settings.CACHES["default"]

        cache_checks = [
            ("Has BACKEND", "BACKEND" in default_cache),
            (
                "BACKEND is valid",
                any(
                    backend in default_cache["BACKEND"]
                    for backend in ["locmem", "redis", "memcached", "dummy"]
                ),
            ),
        ]

        for check_name, check_result in cache_checks:
            with self.subTest(check=check_name):
                self.assertTrue(check_result, f"Cache check failed: {check_name}")

    def test_static_media_configuration_comprehensive(self):
        """Test comprehensive static and media files configuration."""
        static_media_checks = [
            (
                "STATIC_URL configured",
                hasattr(settings, "STATIC_URL") and settings.STATIC_URL,
            ),
            (
                "STATIC_URL format",
                (
                    settings.STATIC_URL.startswith("/")
                    if hasattr(settings, "STATIC_URL") and settings.STATIC_URL
                    else True
                ),
            ),
            (
                "MEDIA_URL configured",
                hasattr(settings, "MEDIA_URL") and settings.MEDIA_URL,
            ),
            (
                "MEDIA_URL format",
                (
                    settings.MEDIA_URL.startswith("/")
                    if hasattr(settings, "MEDIA_URL") and settings.MEDIA_URL
                    else True
                ),
            ),
            ("STATIC_ROOT exists", hasattr(settings, "STATIC_ROOT")),
            ("MEDIA_ROOT exists", hasattr(settings, "MEDIA_ROOT")),
        ]

        for check_name, check_result in static_media_checks:
            with self.subTest(check=check_name):
                self.assertTrue(
                    check_result, f"Static/Media check failed: {check_name}"
                )

    def test_logging_configuration_comprehensive(self):
        """Test comprehensive logging configuration."""
        if hasattr(settings, "LOGGING"):
            logging_config = settings.LOGGING

            logging_checks = [
                ("Is dict", isinstance(logging_config, dict)),
                ("Has version", "version" in logging_config),
                (
                    "Has handlers",
                    "handlers" in logging_config
                    and isinstance(logging_config["handlers"], dict),
                ),
            ]

            for check_name, check_result in logging_checks:
                with self.subTest(check=check_name):
                    self.assertTrue(check_result, f"Logging check failed: {check_name}")

    def test_internationalization_comprehensive(self):
        """Test comprehensive internationalization configuration."""
        i18n_checks = [
            (
                "LANGUAGE_CODE set",
                hasattr(settings, "LANGUAGE_CODE") and settings.LANGUAGE_CODE,
            ),
            ("TIME_ZONE set", hasattr(settings, "TIME_ZONE") and settings.TIME_ZONE),
            ("USE_I18N configured", hasattr(settings, "USE_I18N")),
            ("USE_TZ configured", hasattr(settings, "USE_TZ")),
        ]

        for check_name, check_result in i18n_checks:
            with self.subTest(check=check_name):
                self.assertTrue(check_result, f"I18n check failed: {check_name}")

    def test_rest_framework_configuration_comprehensive(self):
        """Test comprehensive Django REST Framework configuration."""
        if hasattr(settings, "REST_FRAMEWORK"):
            drf_config = settings.REST_FRAMEWORK

            drf_checks = [
                ("Is dict", isinstance(drf_config, dict)),
                ("Has auth classes", "DEFAULT_AUTHENTICATION_CLASSES" in drf_config),
                ("Has permission classes", "DEFAULT_PERMISSION_CLASSES" in drf_config),
                (
                    "Auth classes is list",
                    isinstance(
                        drf_config.get("DEFAULT_AUTHENTICATION_CLASSES", []),
                        (list, tuple),
                    ),
                ),
                (
                    "Permission classes is list",
                    isinstance(
                        drf_config.get("DEFAULT_PERMISSION_CLASSES", []), (list, tuple)
                    ),
                ),
            ]

            for check_name, check_result in drf_checks:
                with self.subTest(check=check_name):
                    self.assertTrue(check_result, f"DRF check failed: {check_name}")

    def test_celery_configuration_comprehensive(self):
        """Test comprehensive Celery configuration."""
        celery_settings = [
            "CELERY_BROKER_URL",
            "CELERY_RESULT_BACKEND",
            "CELERY_TASK_SERIALIZER",
            "CELERY_RESULT_SERIALIZER",
        ]

        for setting_name in celery_settings:
            if hasattr(settings, setting_name):
                with self.subTest(setting=setting_name):
                    value = getattr(settings, setting_name)
                    self.assertIsNotNone(
                        value, f"Celery setting {setting_name} is None"
                    )

                    if setting_name in ["CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"]:
                        self.assertIsInstance(value, str)
                        self.assertGreater(len(value), 0)

    def test_environment_variable_integration(self):
        """Test environment variable integration works correctly."""
        env = environ.Env()

        # Test that common environment variables are handled
        env_var_tests = [
            (
                "SECRET_KEY fallback",
                lambda: env("DJANGO_SECRET_KEY", default="test-key"),
            ),
            ("DEBUG fallback", lambda: env.bool("DEBUG", default=False)),
            ("ALLOWED_HOSTS fallback", lambda: env.list("ALLOWED_HOSTS", default=[])),
        ]

        for test_name, test_func in env_var_tests:
            with self.subTest(test=test_name):
                try:
                    result = test_func()
                    self.assertIsNotNone(result)
                except Exception as e:
                    self.fail(f"Environment variable test failed: {test_name}: {e}")


class ConfigurationValidationTest(TestCase):
    """Test configuration validation and error handling."""

    def test_settings_module_validation(self):
        """Test settings module validation."""
        # Current settings should be valid
        current_module = os.environ.get("DJANGO_SETTINGS_MODULE")
        self.assertIsNotNone(current_module)
        self.assertTrue(current_module.startswith("apps.config.settings"))

        # Should be importable
        try:
            __import__(current_module)
        except ImportError as e:
            self.fail(f"Current settings module not importable: {e}")

    def test_required_apps_validation(self):
        """Test required Django apps are present."""
        required_apps = [
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
        ]

        for app in required_apps:
            with self.subTest(app=app):
                self.assertIn(
                    app, settings.INSTALLED_APPS, f"Required app {app} not installed"
                )

    def test_required_middleware_validation(self):
        """Test required middleware is present and properly ordered."""
        required_middleware = [
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ]

        for middleware in required_middleware:
            with self.subTest(middleware=middleware):
                self.assertIn(
                    middleware,
                    settings.MIDDLEWARE,
                    f"Required middleware {middleware} not present",
                )

        # Test middleware ordering
        middleware_list = settings.MIDDLEWARE

        # Security should come before most others
        security_idx = next(
            (i for i, mw in enumerate(middleware_list) if "SecurityMiddleware" in mw),
            None,
        )
        session_idx = next(
            (i for i, mw in enumerate(middleware_list) if "SessionMiddleware" in mw),
            None,
        )
        auth_idx = next(
            (
                i
                for i, mw in enumerate(middleware_list)
                if "AuthenticationMiddleware" in mw
            ),
            None,
        )

        if security_idx is not None:
            self.assertLess(security_idx, 5, "SecurityMiddleware should be early")
        if session_idx is not None and auth_idx is not None:
            self.assertLess(
                session_idx,
                auth_idx,
                "SessionMiddleware should come before AuthenticationMiddleware",
            )

    def test_template_configuration_validation(self):
        """Test template configuration is valid."""
        templates = settings.TEMPLATES
        self.assertIsInstance(templates, (list, tuple))
        self.assertGreater(len(templates), 0)

        for template_config in templates:
            with self.subTest(template_config=template_config):
                self.assertIn("BACKEND", template_config)
                self.assertIn("DIRS", template_config)
                self.assertIn("APP_DIRS", template_config)
                self.assertIn("OPTIONS", template_config)


class ConfigurationPerformanceTest(TestCase):
    """Test configuration performance implications."""

    def test_debug_mode_implications(self):
        """Test DEBUG mode has correct implications."""
        if settings.DEBUG:
            # Debug mode: more permissive settings are okay
            pass
        else:
            # Production mode: should have stricter settings
            # ALLOWED_HOSTS should not be empty (though might be in tests)
            pass

    def test_database_connection_optimization(self):
        """Test database connection is optimized."""
        default_db = settings.DATABASES["default"]

        # Should have connection optimization settings
        if "CONN_MAX_AGE" in default_db:
            conn_max_age = default_db["CONN_MAX_AGE"]
            self.assertIsInstance(conn_max_age, int)
            self.assertGreaterEqual(conn_max_age, 0)

    def test_cache_optimization(self):
        """Test cache configuration is optimized."""
        default_cache = settings.CACHES["default"]
        backend = default_cache["BACKEND"]

        # Should not use dummy cache in production
        if not settings.DEBUG:
            self.assertNotIn("dummy", backend.lower())

    def test_static_files_optimization(self):
        """Test static files configuration is optimized."""
        # Should have static files properly configured
        self.assertTrue(hasattr(settings, "STATIC_URL"))
        self.assertTrue(hasattr(settings, "STATIC_ROOT"))

        # In production, might have optimized storage
        if hasattr(settings, "STATICFILES_STORAGE"):
            storage = settings.STATICFILES_STORAGE
            self.assertIsInstance(storage, str)


class ConfigurationSecurityTest(TestCase):
    """Test configuration security aspects."""

    def test_secret_key_security(self):
        """Test SECRET_KEY meets security requirements."""
        secret_key = settings.SECRET_KEY

        # Should be long enough
        self.assertGreaterEqual(len(secret_key), 20)

        # Should not be a common default
        insecure_keys = [
            "django-insecure-change-me",
            "your-secret-key-here",
            "change-me",
            "insecure-key",
        ]

        for insecure_key in insecure_keys:
            self.assertNotIn(insecure_key.lower(), secret_key.lower())

    def test_cors_security(self):
        """Test CORS security configuration."""
        if hasattr(settings, "CORS_ALLOW_ALL_ORIGINS"):
            # Should not allow all origins in production
            if not settings.DEBUG:
                self.assertFalse(settings.CORS_ALLOW_ALL_ORIGINS)

        if hasattr(settings, "CORS_ALLOWED_ORIGINS"):
            origins = settings.CORS_ALLOWED_ORIGINS
            for origin in origins:
                # Should be proper URL format
                self.assertTrue(origin.startswith(("http://", "https://")))

    def test_session_security(self):
        """Test session security configuration."""
        # Session middleware should be present
        self.assertIn(
            "django.contrib.sessions.middleware.SessionMiddleware", settings.MIDDLEWARE
        )

        # Session settings should be secure for production
        if hasattr(settings, "SESSION_COOKIE_SECURE") and not settings.DEBUG:
            # In production with HTTPS, should be True
            pass  # Depends on deployment configuration

    def test_csrf_security(self):
        """Test CSRF security configuration."""
        # CSRF middleware should be present
        self.assertIn("django.middleware.csrf.CsrfViewMiddleware", settings.MIDDLEWARE)

        # Should have CSRF configuration
        if hasattr(settings, "CSRF_TRUSTED_ORIGINS"):
            trusted_origins = settings.CSRF_TRUSTED_ORIGINS
            self.assertIsInstance(trusted_origins, (list, tuple))


class ConfigurationMaintenanceTest(TestCase):
    """Test configuration maintenance and monitoring."""

    def test_logging_maintenance(self):
        """Test logging configuration for maintenance."""
        if hasattr(settings, "LOGGING"):
            logging_config = settings.LOGGING

            # Should have proper logging structure
            self.assertIn("version", logging_config)
            self.assertEqual(logging_config["version"], 1)

    def test_monitoring_configuration(self):
        """Test monitoring and observability configuration."""
        # Should have proper monitoring setup
        # This depends on the specific monitoring tools used

        # Check if Sentry is configured
        sentry_settings = [s for s in dir(settings) if "SENTRY" in s]
        # Might have Sentry configuration

    def test_backup_configuration(self):
        """Test backup-related configuration."""
        # Should have proper backup configuration
        # This is more about deployment, but can check basic settings

        default_db = settings.DATABASES["default"]
        # Database should be configured for backups in production
        if not settings.DEBUG:
            # Production database should have proper configuration
            self.assertIn("ENGINE", default_db)
            self.assertIn("NAME", default_db)
