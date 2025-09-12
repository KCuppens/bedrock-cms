import sentry_sdk
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.django import DjangoInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import DATABASES  # noqa: F405
from .base import LOGGING  # noqa: F405
from .base import env  # noqa: F403; noqa: F405

# SECURITY WARNING: don't run with debug turned on in production!

DEBUG = False


# Security

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405

SECURE_HSTS_SECONDS = env.int(
    "SECURE_HSTS_SECONDS", default=31536000
)  # 1 year  # noqa: F405

SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SECURE_HSTS_PRELOAD = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Session security

SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = True


# Database

DATABASES = {"default": env.db("DATABASE_URL")}  # noqa: F405, F811

# Optimal connection pooling for production

DATABASES["default"]["CONN_MAX_AGE"] = env.int(
    "DB_CONN_MAX_AGE", 600
)  # 10 minutes  # noqa: F405

DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

DATABASES["default"]["OPTIONS"] = {
    "connect_timeout": 10,
    "options": "-c statement_timeout=30000",  # 30 seconds
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
    "sslmode": "require",  # Force SSL in production
}


# Email

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)  # noqa: F405

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")  # noqa: F405


# Static files

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# Media files (use S3/MinIO in production)

if env.bool("USE_S3", default=True):  # noqa: F405

    DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")  # noqa: F405

    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")  # noqa: F405

    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")  # noqa: F405

    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")  # noqa: F405

    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)  # noqa: F405

    AWS_DEFAULT_ACL = None

    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }


# Celery

CELERY_BROKER_URL = env("CELERY_BROKER_URL")  # noqa: F405

CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")  # noqa: F405


# Sentry

SENTRY_DSN = env("SENTRY_DSN", default=None)  # noqa: F405

if SENTRY_DSN:

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            """DjangoIntegration("""
                transaction_style="url",
                middleware_spans=True,
                signals_spans=True,
            ),
            """CeleryIntegration("""
                monitor_beat_tasks=True,
                propagate_traces=True,
            ),
            """RedisIntegration(),"""
        ],
        traces_sample_rate=env.float(
            "SENTRY_TRACES_SAMPLE_RATE", default=0.1
        ),  # noqa: F405
        send_default_pii=False,
        debug=False,
    )


# Logging

LOGGING = {  # noqa: F811
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        """"apps": {"""
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# CORS

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])  # noqa: F405

CORS_ALLOW_CREDENTIALS = True

CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours cache for preflight requests


# Custom headers for API requests (inherit from base, can be overridden via env)

CORS_ALLOW_HEADERS = [
    # Standard headers
    "authorization",
    "content-type",
    "x-csrftoken",
    "x-requested-with",
    # Custom headers for permission context
    "x-locale",
    "x-user-scopes",
    "x-user-role",
]


# Admin security

ADMIN_URL_PATH = env("ADMIN_URL_PATH", default="admin/")  # noqa: F405

ADMIN_IP_ALLOWLIST = env.list("ADMIN_IP_ALLOWLIST", default=[])  # noqa: F405


# Rate limiting

RATELIMIT_ENABLE = True

RATELIMIT_USE_CACHE = "default"


# OpenTelemetry

OTEL_EXPORTER_OTLP_ENDPOINT = env(
    "OTEL_EXPORTER_OTLP_ENDPOINT", default=None
)  # noqa: F405

if OTEL_EXPORTER_OTLP_ENDPOINT:

    trace.set_tracer_provider(TracerProvider())

    tracer = trace.get_tracer(__name__)

    otlp_exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)

    span_processor = BatchSpanProcessor(otlp_exporter)

    trace.get_tracer_provider().add_span_processor(span_processor)

    DjangoInstrumentor().instrument()

    Psycopg2Instrumentor().instrument()

    RedisInstrumentor().instrument()
