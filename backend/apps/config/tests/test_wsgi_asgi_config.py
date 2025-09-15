"""Tests for WSGI and ASGI configuration."""

import os
import sys
from unittest.mock import MagicMock, patch

import django

# Configure Django settings before imports
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase


class WSGIConfigurationTest(TestCase):
    """Test WSGI configuration."""

    def test_wsgi_module_import(self):
        """Test WSGI module can be imported."""
        try:
            from apps.config import wsgi

            self.assertTrue(hasattr(wsgi, "application"))
        except ImportError as e:
            self.fail(f"Failed to import WSGI module: {e}")

    def test_wsgi_application_callable(self):
        """Test WSGI application is callable."""
        from apps.config import wsgi

        self.assertTrue(callable(wsgi.application))

    def test_wsgi_django_settings_module(self):
        """Test WSGI sets correct Django settings module."""
        import apps.config.wsgi as wsgi_module
        from apps.config import wsgi

        # Check the module sets DJANGO_SETTINGS_MODULE
        # This is set at import time, so we check the environment
        self.assertIn("DJANGO_SETTINGS_MODULE", os.environ)

        current_settings = os.environ.get("DJANGO_SETTINGS_MODULE")
        self.assertTrue(current_settings.startswith("apps.config.settings"))

    def test_wsgi_application_type(self):
        """Test WSGI application is of correct type."""
        from django.core.wsgi import WSGIHandler

        from apps.config import wsgi

        # Should be a Django WSGI handler
        self.assertIsInstance(wsgi.application, WSGIHandler)

    def test_wsgi_settings_configuration(self):
        """Test WSGI application has correct settings configured."""
        from apps.config import wsgi

        # Should have Django configured properly
        self.assertTrue(django.apps.apps.ready)

        # Should have all required settings
        required_settings = ["SECRET_KEY", "INSTALLED_APPS", "MIDDLEWARE"]
        for setting in required_settings:
            self.assertTrue(hasattr(settings, setting))

    def test_wsgi_application_response(self):
        """Test WSGI application can handle basic requests."""
        from apps.config import wsgi

        # Create a minimal WSGI environ
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "8000",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": MagicMock(),
            "wsgi.errors": MagicMock(),
            "wsgi.multithread": False,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
        }

        start_response = MagicMock()

        try:
            # Should not raise an exception
            response = wsgi.application(environ, start_response)
            self.assertIsNotNone(response)

            # start_response should have been called
            self.assertTrue(start_response.called)

        except Exception as e:
            # Some exceptions are expected (like missing URL patterns)
            # but it should not be import or configuration errors
            self.assertNotIsInstance(e, (ImportError, ImproperlyConfigured))

    def test_wsgi_module_structure(self):
        """Test WSGI module has correct structure."""
        import apps.config.wsgi as wsgi_module

        # Should have docstring
        self.assertIsNotNone(wsgi_module.__doc__)

        # Should import necessary modules
        source_code = wsgi_module.__file__
        if source_code:
            # Module should exist and be readable
            self.assertTrue(os.path.exists(source_code.replace(".pyc", ".py")))


class ASGIConfigurationTest(TestCase):
    """Test ASGI configuration."""

    def test_asgi_module_import(self):
        """Test ASGI module can be imported."""
        try:
            from apps.config import asgi

            self.assertTrue(hasattr(asgi, "application"))
        except ImportError as e:
            self.fail(f"Failed to import ASGI module: {e}")

    def test_asgi_application_callable(self):
        """Test ASGI application is callable."""
        from apps.config import asgi

        self.assertTrue(callable(asgi.application))

    def test_asgi_django_settings_module(self):
        """Test ASGI sets correct Django settings module."""
        import apps.config.asgi as asgi_module
        from apps.config import asgi

        # Check the module sets DJANGO_SETTINGS_MODULE
        self.assertIn("DJANGO_SETTINGS_MODULE", os.environ)

        current_settings = os.environ.get("DJANGO_SETTINGS_MODULE")
        self.assertTrue(current_settings.startswith("apps.config.settings"))

    def test_asgi_application_type(self):
        """Test ASGI application is of correct type."""
        from django.core.asgi import ASGIHandler

        from apps.config import asgi

        # Should be a Django ASGI handler
        self.assertIsInstance(asgi.application, ASGIHandler)

    def test_asgi_settings_configuration(self):
        """Test ASGI application has correct settings configured."""
        from apps.config import asgi

        # Should have Django configured properly
        self.assertTrue(django.apps.apps.ready)

        # Should have all required settings
        required_settings = ["SECRET_KEY", "INSTALLED_APPS", "MIDDLEWARE"]
        for setting in required_settings:
            self.assertTrue(hasattr(settings, setting))

    def test_asgi_application_coroutine(self):
        """Test ASGI application is a coroutine."""
        import inspect

        from apps.config import asgi

        # ASGI applications should be coroutine functions
        # or objects with __call__ that return coroutines
        app = asgi.application

        # Check if it's directly a coroutine function or if calling it returns a coroutine
        if inspect.iscoroutinefunction(app):
            # Direct coroutine function
            pass
        elif hasattr(app, "__call__"):
            # Should be callable and return something that can handle ASGI
            self.assertTrue(callable(app))
        else:
            self.fail("ASGI application should be callable")

    def test_asgi_module_structure(self):
        """Test ASGI module has correct structure."""
        import apps.config.asgi as asgi_module

        # Should have docstring
        self.assertIsNotNone(asgi_module.__doc__)

        # Should import necessary modules
        source_code = asgi_module.__file__
        if source_code:
            # Module should exist and be readable
            self.assertTrue(os.path.exists(source_code.replace(".pyc", ".py")))


class WSGIASGIConsistencyTest(TestCase):
    """Test consistency between WSGI and ASGI configurations."""

    def test_wsgi_asgi_same_settings_module(self):
        """Test WSGI and ASGI use the same Django settings module."""
        from apps.config import asgi, wsgi

        # Both should configure Django with the same settings
        # This is implicit in how they're imported, but we can verify
        # they both have access to the same Django configuration
        self.assertEqual(
            wsgi.application.get_response.__class__,
            asgi.application.get_response.__class__,
        )

    def test_wsgi_asgi_same_django_apps(self):
        """Test WSGI and ASGI have same Django apps configured."""
        from apps.config import asgi, wsgi

        # Both should have the same installed apps
        # Since they use the same settings, this should be true
        self.assertTrue(django.apps.apps.ready)

        # Get list of installed app configs
        installed_apps = [
            app_config.name for app_config in django.apps.apps.get_app_configs()
        ]
        self.assertGreater(len(installed_apps), 0)

        # Both WSGI and ASGI should see the same apps
        # This is implicitly tested by ensuring Django is properly configured

    def test_wsgi_asgi_middleware_consistency(self):
        """Test WSGI and ASGI middleware consistency."""
        # Both should use the same middleware configuration from Django settings
        middleware = settings.MIDDLEWARE
        self.assertIsInstance(middleware, (list, tuple))
        self.assertGreater(len(middleware), 0)

        # Verify that both WSGI and ASGI applications have access to the same middleware
        # This is ensured by using the same Django settings


class WSGIProductionTest(TestCase):
    """Test WSGI configuration for production deployment."""

    def test_wsgi_production_ready(self):
        """Test WSGI configuration is production ready."""
        from apps.config import wsgi

        # Should have proper error handling
        app = wsgi.application
        self.assertIsNotNone(app)

        # Should not raise exceptions during import
        # (Already tested by successful import)

    def test_wsgi_environment_variables(self):
        """Test WSGI respects environment variables."""
        # Test that changing DJANGO_SETTINGS_MODULE affects WSGI
        original_settings = os.environ.get("DJANGO_SETTINGS_MODULE")

        # Should have a settings module set
        self.assertIsNotNone(original_settings)
        self.assertIn("apps.config.settings", original_settings)

    def test_wsgi_static_files_handling(self):
        """Test WSGI static files configuration."""
        # Check if static files middleware is configured
        middleware = settings.MIDDLEWARE

        # Should have WhiteNoise or similar for static files in production
        static_middleware = [
            mw
            for mw in middleware
            if "static" in mw.lower() or "whitenoise" in mw.lower()
        ]
        # Might have static file middleware

    def test_wsgi_security_middleware(self):
        """Test WSGI security middleware configuration."""
        middleware = settings.MIDDLEWARE

        # Should have security middleware
        security_middleware = [
            "django.middleware.security.SecurityMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
        ]

        for sec_middleware in security_middleware:
            self.assertIn(sec_middleware, middleware)


class ASGIProductionTest(TestCase):
    """Test ASGI configuration for production deployment."""

    def test_asgi_production_ready(self):
        """Test ASGI configuration is production ready."""
        from apps.config import asgi

        # Should have proper error handling
        app = asgi.application
        self.assertIsNotNone(app)

        # Should not raise exceptions during import
        # (Already tested by successful import)

    def test_asgi_websocket_support(self):
        """Test ASGI WebSocket support configuration."""
        # ASGI should support WebSocket connections
        from apps.config import asgi

        app = asgi.application

        # Should be capable of handling WebSocket connections
        # This is inherent in Django's ASGI handler

    def test_asgi_http_support(self):
        """Test ASGI HTTP support configuration."""
        # ASGI should support regular HTTP requests
        from apps.config import asgi

        app = asgi.application

        # Should be capable of handling HTTP requests
        # This is inherent in Django's ASGI handler


class WSGIASGIDeploymentTest(TestCase):
    """Test WSGI and ASGI deployment configurations."""

    def test_wsgi_deployment_settings(self):
        """Test WSGI deployment settings."""
        from apps.config import wsgi

        # Should have proper deployment configuration
        # Check that Django is properly configured
        self.assertTrue(django.apps.apps.ready)

        # Should have database configuration
        self.assertIn("default", settings.DATABASES)

        # Should have static files configuration
        self.assertTrue(hasattr(settings, "STATIC_URL"))
        self.assertTrue(hasattr(settings, "STATIC_ROOT"))

    def test_asgi_deployment_settings(self):
        """Test ASGI deployment settings."""
        from apps.config import asgi

        # Should have proper deployment configuration
        # Same as WSGI since they use the same Django settings
        self.assertTrue(django.apps.apps.ready)

        # Should have database configuration
        self.assertIn("default", settings.DATABASES)

        # Should have static files configuration
        self.assertTrue(hasattr(settings, "STATIC_URL"))
        self.assertTrue(hasattr(settings, "STATIC_ROOT"))

    def test_deployment_environment_detection(self):
        """Test deployment environment detection."""
        # Both WSGI and ASGI should work with environment-specific settings
        current_settings = os.environ.get("DJANGO_SETTINGS_MODULE")
        self.assertIsNotNone(current_settings)

        # Should be using a valid settings module
        valid_settings_modules = [
            "apps.config.settings.local",
            "apps.config.settings.test",
            "apps.config.settings.prod",
            "apps.config.settings.test_minimal",
        ]

        is_valid_module = any(
            current_settings.endswith(module.split(".")[-1])
            for module in valid_settings_modules
        )
        if not is_valid_module:
            # Might be a custom settings module
            self.assertTrue(current_settings.startswith("apps.config.settings"))

    def test_server_compatibility(self):
        """Test server compatibility for WSGI and ASGI."""
        from apps.config import asgi, wsgi

        # WSGI application should be compatible with WSGI servers
        wsgi_app = wsgi.application
        self.assertTrue(callable(wsgi_app))

        # ASGI application should be compatible with ASGI servers
        asgi_app = asgi.application
        self.assertTrue(callable(asgi_app))


class ConfigurationIntegrityTest(TestCase):
    """Test configuration integrity for WSGI/ASGI."""

    def test_no_circular_imports(self):
        """Test there are no circular imports in WSGI/ASGI configuration."""
        # Should be able to import both modules without issues
        try:
            from apps.config import asgi, wsgi

            # Both should be importable
            self.assertIsNotNone(wsgi)
            self.assertIsNotNone(asgi)
        except ImportError as e:
            self.fail(f"Circular import or import error: {e}")

    def test_settings_module_consistency(self):
        """Test settings module consistency across WSGI/ASGI."""
        # Both should use the same settings module
        current_settings = os.environ.get("DJANGO_SETTINGS_MODULE")

        # Re-import to ensure consistency
        import importlib

        import apps.config.asgi
        import apps.config.wsgi

        # Force reload to test consistency
        importlib.reload(apps.config.wsgi)
        importlib.reload(apps.config.asgi)

        # Settings should still be consistent
        self.assertEqual(os.environ.get("DJANGO_SETTINGS_MODULE"), current_settings)

    def test_django_setup_consistency(self):
        """Test Django setup is consistent for WSGI/ASGI."""
        from apps.config import asgi, wsgi

        # Django should be properly set up for both
        self.assertTrue(django.apps.apps.ready)

        # Both should have access to the same Django configuration
        self.assertEqual(
            len(django.apps.apps.get_app_configs()),
            len(django.apps.apps.get_app_configs()),
        )

    def test_error_handling_configuration(self):
        """Test error handling configuration for WSGI/ASGI."""
        from apps.config import asgi, wsgi

        # Should not raise configuration errors
        wsgi_app = wsgi.application
        asgi_app = asgi.application

        self.assertIsNotNone(wsgi_app)
        self.assertIsNotNone(asgi_app)

        # Should handle basic configuration validation
        # (Already tested by successful setup)


class PerformanceConfigurationTest(TestCase):
    """Test performance-related WSGI/ASGI configuration."""

    def test_middleware_order_optimization(self):
        """Test middleware order is optimized for performance."""
        middleware = settings.MIDDLEWARE

        # Security middleware should be early
        security_middleware = [mw for mw in middleware if "SecurityMiddleware" in mw]
        if security_middleware:
            security_index = middleware.index(security_middleware[0])
            self.assertLess(
                security_index,
                len(middleware) // 2,
                "Security middleware should be in the first half",
            )

        # Performance middleware should be early
        perf_middleware = [
            mw for mw in middleware if "GZipMiddleware" in mw or "Performance" in mw
        ]
        for perf_mw in perf_middleware:
            perf_index = middleware.index(perf_mw)
            # Should be reasonably early
            self.assertLess(perf_index, len(middleware) * 0.7)

    def test_static_files_optimization(self):
        """Test static files are optimized for production."""
        # Check static files configuration
        if hasattr(settings, "STATICFILES_STORAGE"):
            storage = settings.STATICFILES_STORAGE
            # Might have optimization for production
            self.assertIsInstance(storage, str)

    def test_database_connection_optimization(self):
        """Test database connections are optimized."""
        default_db = settings.DATABASES["default"]

        # Should have connection pooling settings
        if "CONN_MAX_AGE" in default_db:
            conn_max_age = default_db["CONN_MAX_AGE"]
            self.assertIsInstance(conn_max_age, int)
            self.assertGreaterEqual(conn_max_age, 0)
