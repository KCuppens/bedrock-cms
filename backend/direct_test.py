#!/usr/bin/env python
"""Direct test without Django test framework."""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")

print("Starting direct tests...")

# Import Django but don't call setup() yet
import django
from django.conf import settings

print(f"Django version: {django.__version__}")
print(f"Settings module: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
print(f"Settings configured: {settings.configured}")

# Try to access settings to see what happens
try:
    print(f"DEBUG setting: {settings.DEBUG}")
except Exception as e:
    print(f"Error accessing settings: {e}")

print("\nTest completed without Django setup()")

# Now let's test if we can import models without setup()
try:
    from apps.accounts.models import User

    print("Successfully imported User model (shouldn't work without setup)")
except Exception as e:
    print(f"Expected error importing User model without setup: {type(e).__name__}")

print("\nDirect test script finished successfully!")
