import tempfile
from pathlib import Path

# Import base settings but override problematic apps
from .base import *  # noqa: F403, F401
from .base import env  # noqa: F401

# Temporarily disable problematic apps for basic Django setup test
INSTALLED_APPS = [
    # Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "corsheaders",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "waffle",
    # Only essential local apps
    "apps.accounts",
    "apps.core",
    "apps.i18n",  # Required by accounts.rbac
]

# Test database configuration
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable migrations for local tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Fast password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Celery settings for tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Logging disabled for tests
LOGGING_CONFIG = None

# Media files - use temp directory
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="test_media_"))

# Static files - use temp directory  
STATIC_ROOT = Path(tempfile.mkdtemp(prefix="test_static_"))

# Security settings
SECRET_KEY = "test-secret-key-not-for-production"  # nosec B105

# Cache settings
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# REST Framework test settings
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