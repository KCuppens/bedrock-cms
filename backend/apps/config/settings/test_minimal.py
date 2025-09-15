"""Minimal Django settings for testing without problematic apps."""

import os
import tempfile
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Security settings
SECRET_KEY = "test-secret-key-not-for-production"  # nosec B105
DEBUG = True
ALLOWED_HOSTS = ["*"]

# Minimal app configuration
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "allauth",
    "allauth.account",
]

LOCAL_APPS = [
    "apps.core",
    "apps.i18n",  # Required by apps.accounts
    "apps.accounts",
    "apps.files",
    "apps.media",  # Required for legacy migration compatibility
    "apps.emails",  # Required for email tests
    "apps.analytics",  # Required for analytics tests
    "apps.featureflags",  # Required for feature flag tests
    "apps.cms",  # Required by blog
    "apps.blog",  # Required by signals
    "apps.registry",  # Required by signals
    "apps.api",  # Required by ops.metrics
    "apps.ops",  # For ops tests
    "apps.search",  # Required for search tests
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",  # Required by allauth
]

ROOT_URLCONF = "apps.config.urls"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Disable migrations for tests but keep essential ones
class DisableMigrations:
    def __contains__(self, item):
        # Keep migrations for critical apps needed for e2e tests
        if item in [
            "auth",
            "authtoken",
            "contenttypes",
            "blog",
            "cms",
            "i18n",
            "accounts",
            "media",
            "files",
            "search",
        ]:
            return False
        return True

    def __getitem__(self, item):
        # Keep migrations for critical apps needed for e2e tests
        if item in [
            "auth",
            "authtoken",
            "contenttypes",
            "blog",
            "cms",
            "i18n",
            "accounts",
            "media",
            "files",
            "search",
        ]:
            return None
        return None


MIGRATION_MODULES = DisableMigrations()

# Cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# Password hashers for faster tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "apps.accounts.auth_backends.ScopedPermissionBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Static/Media files
STATIC_URL = "/static/"
STATIC_ROOT = Path(tempfile.mkdtemp(prefix="test_static_"))
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="test_media_"))

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/hour",
        "user": "10000/hour",
        "auth": "1000/min",
        "login": "1000/min",
        "write": "10000/hour",
        "burst_write": "1000/min",
        "publish": "10000/hour",
        "media_upload": "10000/hour",
        "admin": "10000/hour",
        "security_scan": "10000/hour",
        "search": "10000/hour",
        "password_reset": "1000/hour",
    },
}

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User model
AUTH_USER_MODEL = "accounts.User"

# Disable logging during tests
LOGGING_CONFIG = None

# Add LOGGING configuration for tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
    },
}

# WSGI Application
WSGI_APPLICATION = "apps.config.wsgi.application"

# Cache middleware settings
CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = 600  # 10 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = "bedrock"

# Security settings for tests
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Celery configuration for tests - use eager mode to avoid external dependencies
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = "memory://"
CELERY_RESULT_BACKEND = "cache+memory://"
