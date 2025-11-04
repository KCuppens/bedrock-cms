#!/usr/bin/env python3
"""
Apply security fixes to Django settings
"""

import re

SETTINGS_FILE = "backend/apps/config/settings/base.py"

def apply_fixes():
    with open(SETTINGS_FILE, 'r') as f:
        content = f.read()

    # 1. Add session security settings after SESSION_CACHE_ALIAS
    session_security = '''
# Session Security Settings
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = False  # Don't update session on every request

# CSRF Security
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)  # HTTPS only in production
CSRF_COOKIE_HTTPONLY = True  # No JavaScript access
CSRF_COOKIE_SAMESITE = 'Strict'

'''

    if "SESSION_COOKIE_SECURE" not in content:
        content = content.replace(
            'SESSION_CACHE_ALIAS = "default"',
            'SESSION_CACHE_ALIAS = "default"\n' + session_security
        )

    # 2. Add security headers after X_FRAME_OPTIONS
    security_headers = '''
# Additional Security Headers
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_REFERRER_POLICY = 'same-origin'

'''

    if "SECURE_HSTS_SECONDS" not in content:
        content = content.replace(
            'X_FRAME_OPTIONS = "DENY"',
            'X_FRAME_OPTIONS = "DENY"\n' + security_headers
        )

    # 3. Add Celery security settings
    celery_security = '''
# Celery Security Settings
CELERY_TASK_ACKS_LATE = True  # Acknowledge tasks after completion
CELERY_TASK_REJECT_ON_WORKER_LOST = True  # Reject lost tasks
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Reduce prefetch for better distribution
CELERY_TASK_TIME_LIMIT = 300  # 5 minutes max per task
CELERY_TASK_SOFT_TIME_LIMIT = 270  # 4.5 minutes soft limit

'''

    if "CELERY_TASK_ACKS_LATE" not in content:
        content = content.replace(
            'CELERY_ENABLE_UTC = True',
            'CELERY_ENABLE_UTC = True\n' + celery_security
        )

    # 4. Fix cache key prefix to be environment-specific
    content = re.sub(
        r'CACHE_MIDDLEWARE_KEY_PREFIX = "bedrock"',
        'CACHE_MIDDLEWARE_KEY_PREFIX = env("CACHE_KEY_PREFIX", default="bedrock_dev")',
        content
    )

    # 5. Update password validators for stronger passwords
    content = re.sub(
        r'"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",',
        '"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",\n        "OPTIONS": {\n            "min_length": 10,\n        },',
        content,
        count=1
    )

    # 6. Add file permissions
    if "FILE_UPLOAD_PERMISSIONS" not in content:
        file_perms = '''
# File Upload Security
FILE_UPLOAD_PERMISSIONS = 0o644  # Restrict file permissions
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755  # Restrict directory permissions
'''
        content = content.replace(
            'DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE',
            'DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE\n' + file_perms
        )

    # Write back
    with open(SETTINGS_FILE, 'w') as f:
        f.write(content)

    print("✓ Applied security fixes to base.py")
    print("  - Added session security settings")
    print("  - Added security headers (HSTS, referrer policy)")
    print("  - Added Celery security settings")
    print("  - Fixed cache key prefix")
    print("  - Strengthened password validation (min length: 10)")
    print("  - Added file permission restrictions")

if __name__ == "__main__":
    apply_fixes()
