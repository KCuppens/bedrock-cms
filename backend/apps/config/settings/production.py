
Production settings with CDN and performance optimizations.

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import (
    DATABASES,  # noqa: F405
    LOGGING,  # noqa: F405
    env,  # noqa: F403; noqa: F405
)

# Security
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])  # noqa: F405

# CDN Configuration
CDN_ENABLED = True
CDN_URL = env("CDN_URL", default="https://cdn.example.com")  # noqa: F405
CDN_PULL_ZONE = env("CDN_PULL_ZONE", default="")  # noqa: F405

# CloudFlare settings (if using CloudFlare)
CLOUDFLARE_ZONE_ID = env("CLOUDFLARE_ZONE_ID", default="")  # noqa: F405
CLOUDFLARE_API_TOKEN = env("CLOUDFLARE_API_TOKEN", default="")  # noqa: F405

# Static files with CDN
if CDN_ENABLED:
    STATIC_URL = f"{CDN_URL}/static/"
    MEDIA_URL = f"{CDN_URL}/media/"
else:
    STATIC_URL = "/static/"
    MEDIA_URL = "/media/"

# Cache configuration for production
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),  # noqa: F405
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "bedrock",
        "TIMEOUT": 300,
    },
    "page_cache": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/1"),  # noqa: F405
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "page",
        "TIMEOUT": 600,
    },
    "api_cache": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/2"),  # noqa: F405
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
        "KEY_PREFIX": "api",
        "TIMEOUT": 300,
    },
}

# Database optimizations
DATABASES["default"]["CONN_MAX_AGE"] = 600  # noqa: F405
DATABASES["default"]["OPTIONS"].update(  # noqa: F405
    {
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000",
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
        "server_side_cursors": True,
    }
)

# WhiteNoise configuration for static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
WHITENOISE_COMPRESS_OFFLINE = True
WHITENOISE_USE_FINDERS = False
WHITENOISE_AUTOREFRESH = False

# Security headers for CDN
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# CORS for CDN
CORS_ALLOWED_ORIGINS = env.list(  # noqa: F405
    "CORS_ALLOWED_ORIGINS",
    default=[
        "https://cdn.example.com",
        "https://example.com",
    ],
)

# Performance optimizations
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Email backend for production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", 587)  # noqa: F405
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")  # noqa: F405

# Celery optimizations
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Logging configuration
LOGGING = {  # noqa: F811
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/bedrock/error.log",
            "maxBytes": 1024 * 1024 * 50,  # 50MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "performance": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/bedrock/performance.log",
            "maxBytes": 1024 * 1024 * 100,  # 100MB
            "backupCount": 3,
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "performance": {
            "handlers": ["performance"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# Sentry integration (optional)
if env("SENTRY_DSN", default=""):  # noqa: F405
    sentry_sdk.init(
        dsn=env("SENTRY_DSN"),  # noqa: F405
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment="production",
    )
