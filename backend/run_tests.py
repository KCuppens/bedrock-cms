#!/usr/bin/env python
"""Test runner script with proper environment setup."""

import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module
os.environ["DJANGO_SETTINGS_MODULE"] = "apps.config.settings.test"

# Setup Django
django.setup()

# Run tests
if __name__ == "__main__":
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["apps.accounts", "apps.cms", "apps.blog"])

    if failures:
        sys.exit(1)
    else:
        print("\nAll tests passed successfully!")
        sys.exit(0)
