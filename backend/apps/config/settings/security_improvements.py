# Security Improvements for Django Settings
# This file contains security enhancements to be merged into base.py

from django.core.exceptions import ImproperlyConfigured

# ==================================================
# SECRET KEY SECURITY
# ==================================================
# Remove insecure default - force explicit configuration
#
# BEFORE:
# SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")
#
# AFTER:
# SECRET_KEY = env("DJANGO_SECRET_KEY")  # No default - must be set explicitly

#import os
# SECURE_SECRET_KEY_MINIMUM_LENGTH = 50
# if len(SECRET_KEY) < SECURE_SECRET_KEY_MINIMUM_LENGTH:
#     raise ImproperlyConfigured(
#         f"SECRET_KEY must be at least {SECURE_SECRET_KEY_MINIMUM_LENGTH} characters long"
#     )


# ==================================================
# ALLOWED_HOSTS VALIDATION
# ==================================================
# Require explicit configuration in production
#
# ADD AFTER ALLOWED_HOSTS definition:
# if not ALLOWED_HOSTS and not DEBUG:
#     raise ImproperlyConfigured(
#         "ALLOWED_HOSTS must be set in production (DEBUG=False). "
#         "Set ALLOWED_HOSTS environment variable with comma-separated domains."
#     )


# ==================================================
# SESSION SECURITY
# ==================================================
# Add these settings after SESSION_CACHE_ALIAS:

SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = False  # Don't update session on every request
CSRF_COOKIE_SECURE = True  # HTTPS only
CSRF_COOKIE_HTTPONLY = True  # No JavaScript access
CSRF_COOKIE_SAMESITE = 'Strict'


# ==================================================
# SECURITY HEADERS
# ==================================================
# Add after existing security settings:

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# SSL/HTTPS
SECURE_SSL_REDIRECT = False  # Set to True in production.py
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Additional Security Headers
SECURE_REFERRER_POLICY = 'same-origin'

# Content Security Policy (add via middleware or django-csp package)
# For now, add recommended CSP via SECURE_CONTENT_SECURITY_POLICY if using django-csp:
# SECURE_CONTENT_SECURITY_POLICY = {
#     "default-src": ["'self'"],
#     "script-src": ["'self'", "'unsafe-inline'"],  # Remove unsafe-inline after audit
#     "style-src": ["'self'", "'unsafe-inline'"],
#     "img-src": ["'self'", "data:", "https:"],
#     "font-src": ["'self'", "data:"],
#     "connect-src": ["'self'"],
#     "frame-ancestors": ["'none'"],
# }


# ==================================================
# S3 SECURITY
# ==================================================
# Change default ACL from public-read to private:
#
# BEFORE:
# AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default="public-read")
#
# AFTER:
# AWS_DEFAULT_ACL = env("AWS_DEFAULT_ACL", default="private")


# ==================================================
# CELERY SECURITY
# ==================================================
# Add after CELERY_ENABLE_UTC:

CELERY_TASK_ACKS_LATE = True  # Acknowledge tasks after completion
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Reject lost tasks
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Reduce prefetch for better distribution
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes max per task
CELERY_TASK_SOFT_TIME_LIMIT = 270  # 4.5 minutes soft limit
# Task signature verification would go here if using django-celery-beat


# ==================================================
# CACHE KEY PREFIX
# ==================================================
# Make cache key prefix unique per environment:
#
# BEFORE:
# CACHE_MIDDLEWARE_KEY_PREFIX = "bedrock"
#
# AFTER:
# ENVIRONMENT = env("ENVIRONMENT", default="dev")
# CACHE_MIDDLEWARE_KEY_PREFIX = f"bedrock_{ENVIRONMENT}"


# ==================================================
# DATABASE STATEMENT TIMEOUT
# ==================================================
# Reduce from 30s to 5s for web requests:
#
# BEFORE:
# "options": "-c statement_timeout=30000",  # 30 seconds
#
# AFTER:
# "options": "-c statement_timeout=5000",  # 5 seconds for web requests


# ==================================================
# CLEAN UP MIDDLEWARE
# ==================================================
# Remove all commented-out middleware entries with "Imports that were malformed"
# Either fix and enable them, or remove completely


# ==================================================
# PASSWORD VALIDATION
# ==================================================
# Add custom password validator for additional security:

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 10,  # Increase from default 8
        }
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ==================================================
# LOGGING IMPROVEMENTS
# ==================================================
# Add security event logging:

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
        "security": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/security.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django.security": {
            "handlers": ["console", "security"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}


# ==================================================
# FILE UPLOAD SECURITY
# ==================================================
# Tighten file upload restrictions:

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5MB (current)
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE
FILE_UPLOAD_PERMISSIONS = 0o644  # Restrict file permissions
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755  # Restrict directory permissions


# ==================================================
# CONTENT SECURITY
# ==================================================
# X-Content-Type-Options already set to nosniff ✓
# X-Frame-Options already set to DENY ✓
# SECURE_BROWSER_XSS_FILTER already set to True ✓
