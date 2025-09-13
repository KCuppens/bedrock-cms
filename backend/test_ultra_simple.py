#!/usr/bin/env python
"""Ultra simple test runner with minimal dependencies."""

import os
import sys

import django

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set Django settings module to ultra minimal
os.environ["DJANGO_SETTINGS_MODULE"] = "apps.config.settings.test_ultra_minimal"

# Setup Django
print("Setting up Django...")
django.setup()
print("Django setup complete!")

# Run a simple test
from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic(self):
        self.assertEqual(1 + 1, 2)
        print("Test passed!")


# Run the test
if __name__ == "__main__":
    from django.conf import settings
    from django.test.utils import get_runner

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2)

    # Create a test suite with our simple test
    from django.test.runner import DiscoverRunner

    suite = test_runner.test_loader.loadTestsFromTestCase(SimpleTest)

    # Run the test
    result = test_runner.run_suite(suite)

    if result.failures or result.errors:
        sys.exit(1)
    else:
        print("\nTest completed successfully!")
        sys.exit(0)
