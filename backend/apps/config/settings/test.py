import tempfile
from pathlib import Path

from .base import (
    DATABASES,  # noqa: F405
    REST_FRAMEWORK,  # noqa: F405
    env,  # noqa: F403; noqa: F405
)

# Database configuration - use DATABASE_URL if provided (for CI), otherwise SQLite
if env("DATABASE_URL", default=""):  # noqa: F405
    # CI environment - use the configured database and run migrations
    DATABASES = {"default": env.db("DATABASE_URL")}  # noqa: F405, F811
else:
    # Local test environment - use fast SQLite in-memory
    DATABASES = {  # noqa: F811
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }

    # Disable migrations for local tests only
    class DisableMigrations:
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None

    MIGRATION_MODULES = DisableMigrations()

# Use locmem cache backend for tests unless Redis is configured
if env("REDIS_URL", default=""):  # noqa: F405
    CACHES = {"default": env.cache("REDIS_URL")}  # noqa: F405
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }

# Password hashers for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Celery settings for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Disable logging during tests
LOGGING_CONFIG = None

# Media files - use temp directory safely
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="test_media_"))

# Static files - use temp directory safely
STATIC_ROOT = Path(tempfile.mkdtemp(prefix="test_static_"))

# Security settings (can be relaxed for tests)
SECRET_KEY = env(  # noqa: F405
    "SECRET_KEY", default="test-secret-key-not-for-production"
)  # nosec B105

# Disable CSRF for API tests
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# Waffle settings for tests
WAFFLE_FLAG_DEFAULT = False
WAFFLE_SWITCH_DEFAULT = False
WAFFLE_SAMPLE_DEFAULT = False
