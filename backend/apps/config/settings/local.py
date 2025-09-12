from typing import Any


from .base import BASE_DIR  # noqa: F405

from .base import DATABASES  # noqa: F405

from .base import INSTALLED_APPS  # noqa: F405

from .base import LOGGING  # noqa: F405

from .base import REST_FRAMEWORK  # noqa: F405

from .base import env  # noqa: F403; noqa: F405


# SECURITY WARNING: don't run with debug turned on in production!

DEBUG = True


ALLOWED_HOSTS = ["localhost", "127.0.0.1"]


# Database

# Use SQLite by default for local development

# Override with DATABASE_URL env var for PostgreSQL/MySQL:

# DATABASE_URL=postgres://user:pass@localhost:5432/dbname

# DATABASE_URL=mysql://user:pass@localhost:3306/dbname

DATABASES = {  # noqa: F811
    "default": env.db(
        "DATABASE_URL", default=f"sqlite:///{BASE_DIR}/db.sqlite3"
    )  # noqa: F405
}


# Email backend for development

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# CORS settings for development

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite development server
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # Alternative React dev server
    "http://127.0.0.1:3000",
    "http://localhost:8080",  # Custom Vite port
    "http://127.0.0.1:8080",
    "http://localhost:8081",  # Alternative custom Vite port
    "http://127.0.0.1:8081",
    "http://localhost:8082",  # Another alternative Vite port
    "http://127.0.0.1:8082",
    "http://localhost:8084",  # Alternative Vite port
    "http://127.0.0.1:8084",
    "http://localhost:8088",  # Current Vite port
    "http://127.0.0.1:8088",
]

CORS_ALLOW_CREDENTIALS = True


# Custom headers for API requests

CORS_ALLOW_HEADERS = [
    # Default headers
    "authorization",
    "content-type",
    "x-csrftoken",
    "x-requested-with",
    # Custom permission context headers
    "x-locale",
    "x-user-scopes",
    "x-user-role",
]


# CSRF settings for development

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:8082",
    "http://127.0.0.1:8082",
    "http://localhost:8084",
    "http://127.0.0.1:8084",
    "http://localhost:8088",
    "http://127.0.0.1:8088",
]

CSRF_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read the cookie


# Static files (CSS, JavaScript, Images)

STATICFILES_DIRS = [BASE_DIR / "static"]  # noqa: F405


# Celery settings for development - run tasks synchronously

CELERY_TASK_ALWAYS_EAGER = True  # Execute tasks locally instead of sending to queue

CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions from eager tasks


# Use in-memory broker for Celery (not actually used when ALWAYS_EAGER is True)

CELERY_BROKER_URL = "memory://localhost/"

CELERY_RESULT_BACKEND = "cache+memory://"


# Django Extensions (if you want to add it later)

if "django_extensions" in INSTALLED_APPS:  # noqa: F405

    INSTALLED_APPS += ["django_extensions"]  # noqa: F405


# Development logging

LOGGING_DICT: dict[str, Any] = LOGGING  # noqa: F405

LOGGING_DICT["handlers"]["console"]["formatter"] = "simple"

LOGGING_DICT["root"]["level"] = "DEBUG"


# Internal IPs for django-debug-toolbar (if added later)

INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]


# Cache Configuration for local development

# Use in-memory cache by default, no Redis required

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}


# Override session engine to use database instead of cache

SESSION_ENGINE = "django.contrib.sessions.backends.db"


# Frontend URL for redirects

FRONTEND_URL = env.str("FRONTEND_URL", default="http://localhost:8082")  # noqa: F405


# Override Allauth to send password reset emails to frontend

ACCOUNT_ADAPTER = "apps.accounts.custom_adapter.CustomAccountAdapter"


# Disable throttling for development to avoid rate limit issues

# Option 1: Keep throttle classes but set very high rates for development

REST_FRAMEWORK = REST_FRAMEWORK.copy()  # noqa: F405

REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {
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
}
