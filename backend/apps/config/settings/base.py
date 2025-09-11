from pathlib import Path

import environ

env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Read .env file
env_file = BASE_DIR / '.env'
if env_file.exists():
    env.read_env(env_file)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Application definition
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
    "corsheaders",
    "drf_spectacular",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "waffle",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.analytics",
    "apps.api",
    "apps.blog",
    "apps.cms",
    "apps.core",
    "apps.emails",
    "apps.featureflags",
    "apps.files",
    "apps.i18n",
    "apps.media",  # Legacy compatibility for old migrations
    "apps.ops",
    "apps.registry",
    "apps.reports",
    "apps.search",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    # Performance monitoring (first to track everything)
    "apps.core.middleware_performance.PerformanceMonitoringMiddleware",
    
    # Compression and optimization (early for efficiency)
    "django.middleware.gzip.GZipMiddleware",
    # "apps.core.middleware_performance.CompressionMiddleware",  # Disabled - requires brotli
    
    # Early exit middleware (prevent unnecessary processing)
    "apps.core.middleware.AdminIPAllowlistMiddleware",
    
    # Security headers (cached for performance)
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.SecurityHeadersMiddleware",
    
    # Static file serving
    "whitenoise.middleware.WhiteNoiseMiddleware",
    
    # CORS handling
    "corsheaders.middleware.CorsMiddleware",
    
    # Cache and conditional responses (early for cache hits)
    "django.middleware.http.ConditionalGetMiddleware",
    "apps.core.middleware_performance.CacheHitRateMiddleware",
    
    # Session management
    "django.contrib.sessions.middleware.SessionMiddleware",
    
    # Dynamic language loading
    "apps.i18n.middleware.DynamicLanguageMiddleware",
    
    # Common middleware
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    
    # Redirect middleware
    "apps.cms.middleware.RedirectMiddleware",
    
    # Authentication (MUST come before any middleware that uses request.user)
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    
    # Messages
    "django.contrib.messages.middleware.MessageMiddleware",
    
    # Throttling (AFTER authentication so it can check user status)
    "apps.core.middleware_performance.RequestThrottlingMiddleware",
    
    # Additional security
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    # Feature flags
    "waffle.middleware.WaffleMiddleware",
    
    # Database optimization
    "apps.core.middleware_performance.DatabaseConnectionPoolMiddleware",
    # "apps.core.middleware_performance.QueryCountLimitMiddleware",  # Disabled in dev
    
    # Heavy middleware at the end
    "apps.accounts.middleware.LastSeenMiddleware",
    "apps.core.middleware.DemoModeMiddleware",
]

ROOT_URLCONF = "apps.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "apps.config.wsgi.application"

# Database
# Default to SQLite for easy development, configurable via DATABASE_URL
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR}/db.sqlite3")
}

# Database connection pooling
DATABASES['default']['CONN_MAX_AGE'] = env.int('DB_CONN_MAX_AGE', 600)  # 10 minutes default

# PostgreSQL-specific optimizations
if 'postgresql' in DATABASES['default']['ENGINE'] or 'postgis' in DATABASES['default']['ENGINE']:
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000',  # 30 seconds
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
    }

# Enable persistent connections
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Cache Configuration
CACHES = {
    "default": env.cache("REDIS_URL", default="redis://localhost:6379/0"),
}

# Cache key settings
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 600  # 10 minutes
CACHE_MIDDLEWARE_KEY_PREFIX = 'bedrock'

# Session cache
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# Default locale settings - will be dynamically updated from database after Django initializes
# These are fallback values used during initial setup and migrations
LANGUAGE_CODE = "en"
LANGUAGES = [
    ("en", "English"),
    # Additional languages will be loaded dynamically from the database
    # via the I18nConfig.ready() method and DynamicLanguageMiddleware
]
RTL_LANGUAGES: list[str] = []

# The i18n app will load actual languages from the database once Django is ready
# This avoids circular dependency issues while still providing dynamic language support

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Additional i18n settings
LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# Custom setting to track if we're using dynamic locales
USE_DYNAMIC_LOCALES = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Media files
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Authentication backends (include RBAC backend)
AUTHENTICATION_BACKENDS = [
    'apps.accounts.auth_backends.ScopedPermissionBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "apps.core.throttling.SecurityScanThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "auth": "5/min",  # For authentication endpoints
        "login": "5/min",  # Strict login throttle
        "write": "200/hour",  # Write operations (POST/PUT/PATCH/DELETE)
        "burst_write": "20/min",  # Burst protection for rapid writes
        "publish": "50/hour",  # Publish/unpublish operations
        "media_upload": "30/hour",  # Media upload operations
        "admin": "500/hour",  # Admin operations (higher limit)
        "security_scan": "10/hour",  # Suspicious pattern detection
    },
}

# Spectacular settings
SPECTACULAR_SETTINGS = {
    "TITLE": "Bedrock CMS API",
    "DESCRIPTION": "A comprehensive Content Management System with multi-locale support, search, caching, and more",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SERVE_AUTHENTICATION": ["rest_framework.authentication.SessionAuthentication"],
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "displayRequestDuration": True,
    },
    "SECURITY": [
        {
            "name": "sessionAuth",
            "type": "apiKey",
            "in": "cookie",
            "description": "Django session-based authentication"
        },
        {
            "name": "csrfToken", 
            "type": "apiKey",
            "in": "header",
            "description": "CSRF token for write operations"
        }
    ],
    "TAGS": [
        {"name": "Pages", "description": "CMS page management and hierarchies"},
        {"name": "Content", "description": "Dynamic content via registry system"},
        {"name": "Blog", "description": "Blog posts, categories, and tags"},
        {"name": "Media", "description": "Asset management and file uploads"},
        {"name": "Search", "description": "Full-text search and filtering"},
        {"name": "SEO", "description": "Search engine optimization tools"},
        {"name": "Locales", "description": "Multi-language and internationalization"},
        {"name": "Translations", "description": "Content translation management"},
        {"name": "Auth", "description": "Authentication and user management"},
        {"name": "Analytics", "description": "Site analytics, metrics, and tracking"},
        {"name": "Security", "description": "Security assessments, risks, and threats"},
    ],
    "EXAMPLES": {
        "PageListResponse": {
            "value": {
                "count": 25,
                "next": "http://localhost:8000/api/v1/cms/pages/?page=2",
                "previous": None,
                "results": [
                    {
                        "id": 1,
                        "title": "Home Page",
                        "slug": "home",
                        "path": "/",
                        "status": "published",
                        "locale": "en",
                        "created_at": "2024-01-15T10:30:00Z",
                        "updated_at": "2024-01-20T14:45:00Z",
                        "seo": {
                            "meta_title": "Welcome to Our Site",
                            "meta_description": "The best CMS platform"
                        }
                    }
                ]
            }
        },
        "SearchResponse": {
            "value": {
                "results": [
                    {
                        "title": "Django Tutorial",
                        "content_snippet": "Learn Django basics...",
                        "content_type": "blog.blogpost",
                        "url": "/blog/django-tutorial/",
                        "score": 0.95
                    }
                ],
                "total": 42,
                "page": 1,
                "suggestions": ["django", "python", "tutorial"]
            }
        }
    }
}

# Django Allauth
# Django Allauth configuration
ACCOUNT_EMAIL_VERIFICATION = "none"  # Email verification is not required
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"

# Email settings
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=1025)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="Django SaaS <noreply@example.com>"
)

# Site Configuration
SITE_NAME = env("SITE_NAME", default="Bedrock CMS")
SITE_URL = env("SITE_URL", default="http://localhost:3000")
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Celery Beat Schedule (Periodic Tasks)
CELERY_BEAT_SCHEDULE = {
    'publish-scheduled-content': {
        'task': 'apps.cms.tasks.publish_scheduled_content',
        'schedule': 60.0,  # Every minute
        'options': {'queue': 'publishing'}
    },
    'nightly-link-check': {
        'task': 'apps.cms.tasks.nightly_link_check',
        'schedule': 60.0 * 60.0 * 24.0,  # Daily at midnight
        'options': {'queue': 'reports'}
    },
    'cleanup-orphaned-translation-units': {
        'task': 'apps.i18n.tasks.cleanup_orphaned_translation_units',
        'schedule': 60.0 * 60.0 * 24.0 * 7.0,  # Weekly
        'options': {'queue': 'maintenance'}
    },
}

# Celery Task Routes
CELERY_TASK_ROUTES = {
    'apps.cms.tasks.publish_scheduled_content': {'queue': 'publishing'},
    'apps.cms.tasks.unpublish_expired_content': {'queue': 'publishing'},
    'apps.cms.tasks.*': {'queue': 'reports'},
    'apps.i18n.tasks.*': {'queue': 'translations'},
}

# Logging
LOGGING = {
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
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

# Security
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# CORS
CORS_ALLOW_ALL_ORIGINS = env.bool("CORS_ALLOW_ALL_ORIGINS", default=False)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# Default CORS allowed headers - can be overridden in environment-specific settings
CORS_ALLOW_HEADERS = [
    # Standard headers
    'authorization',
    'content-type', 
    'x-csrftoken',
    'x-requested-with',
    # Custom headers for permission context
    'x-locale',
    'x-user-scopes',
    'x-user-role',
]

# File Upload
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE

# Demo mode
DEMO_MODE = env.bool("DEMO_MODE", default=False)

# DeepL Translation API
DEEPL_API_KEY = env("DEEPL_API_KEY", default="")

# Admin settings
ADMIN_URL_PATH = env("ADMIN_URL_PATH", default="admin/")
ADMIN_IP_ALLOWLIST = env.list("ADMIN_IP_ALLOWLIST", default=[])

# CMS settings
CMS_SITEMAP_BASE_URL = env("CMS_SITEMAP_BASE_URL", default="http://localhost:8000")

# HTML Sanitization settings
HTML_SANITIZER_ALLOWED_TAGS = [
    'p', 'div', 'span', 'br', 'hr',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'strong', 'b', 'em', 'i', 'u', 's', 'sub', 'sup',
    'ul', 'ol', 'li',
    'a', 'img',
    'blockquote', 'pre', 'code',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'figure', 'figcaption',
]

HTML_SANITIZER_ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'blockquote': ['cite'],
    'table': ['cellpadding', 'cellspacing', 'border'],
    'th': ['scope', 'rowspan', 'colspan'],
    'td': ['rowspan', 'colspan'],
}

HTML_SANITIZER_ALLOWED_PROTOCOLS = ['http', 'https', 'mailto', 'tel']

# Media storage settings
USE_S3_STORAGE = env.bool("USE_S3_STORAGE", default=False)

if USE_S3_STORAGE:
    # AWS S3 settings
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="us-east-1")
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default="public-read")
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    
    # Use different storage for static vs media files
    DEFAULT_FILE_STORAGE = "apps.core.storage.S3MediaStorage"
    STATICFILES_STORAGE = "apps.core.storage.S3StaticStorage"
else:
    # Local file storage (default)
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
