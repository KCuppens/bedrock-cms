"""
Pytest configuration for integration tests.

This configuration provides shared fixtures and settings for all integration tests.
"""

from django.test import override_settings

import pytest


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Grant database access to all tests in this module.
    """
    pass


@pytest.fixture
def integration_settings():
    """
    Override settings for integration tests.
    """
    return override_settings(
        # Use faster password hashing for tests
        PASSWORD_HASHERS=[
            "django.contrib.auth.hashers.MD5PasswordHasher",
        ],
        # Disable migrations for faster test runs
        MIGRATION_MODULES={
            "accounts": None,
            "analytics": None,
            "cms": None,
            "i18n": None,
            "search": None,
        },
        # Use in-memory cache for tests
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "unique-snowflake",
            }
        },
        # Disable Celery for tests
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    )


@pytest.fixture
def no_migrations_settings():
    """
    Settings to disable migrations for faster test execution.
    """
    return override_settings(
        MIGRATION_MODULES={
            app: None
            for app in [
                "accounts",
                "analytics",
                "cms",
                "i18n",
                "search",
                "core",
                "files",
                "media",
                "blog",
                "emails",
            ]
        }
    )


@pytest.mark.django_db
class IntegrationTestCase:
    """Base class for integration tests with common setup."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Setup method run before each test."""
        # Clear any cached data
        from django.core.cache import cache

        cache.clear()

        # Reset any global state if needed
        pass

    def teardown_method(self):
        """Cleanup method run after each test."""
        # Clean up any test data if needed
        pass
