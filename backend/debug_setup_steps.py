#!/usr/bin/env python
"""Debug Django setup step by step."""

import os
import sys
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")

print("Starting step-by-step Django setup debug...")

import django
from django.apps import apps
from django.conf import settings

print(f"Django version: {django.__version__}")

# Step 1: Check settings
print("\nStep 1: Checking settings...")
print(f"Settings configured: {settings.configured}")
print(f"INSTALLED_APPS: {settings.INSTALLED_APPS}")

# Step 2: Try to populate apps manually
print("\nStep 2: Attempting to populate apps registry...")
print("Calling apps.populate()...")

# Add timeout mechanism
import signal


def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


# Set a 2-second timeout
if sys.platform != "win32":
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(2)

try:
    start_time = time.time()
    apps.populate(settings.INSTALLED_APPS)
    elapsed = time.time() - start_time
    print(f"apps.populate() completed in {elapsed:.2f} seconds")
except TimeoutError:
    print("ERROR: apps.populate() timed out after 2 seconds")
except Exception as e:
    print(f"ERROR during apps.populate(): {e}")
    import traceback

    traceback.print_exc()
finally:
    if sys.platform != "win32":
        signal.alarm(0)  # Cancel the alarm

print("\nDebug script finished")
