#!/usr/bin/env python
"""Absolute minimal Django test."""

import django
from django.conf import settings

# Configure Django with absolute minimum settings
settings.configure(
    DEBUG=True,
    SECRET_KEY="test-key",
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    INSTALLED_APPS=[
        "django.contrib.contenttypes",
        "django.contrib.auth",
    ],
    USE_TZ=True,
)

print("Settings configured")

# Setup Django
django.setup()
print("Django setup complete!")

# Run a simple test
from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic(self):
        assert 1 + 1 == 2
        print("Test passed!")


if __name__ == "__main__":
    from django.test.utils import get_runner

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=2)

    # Create and run the test
    suite = test_runner.test_loader.loadTestsFromTestCase(SimpleTest)
    result = test_runner.run_suite(suite)

    if result.failures or result.errors:
        print("Test failed")
    else:
        print("Test succeeded")
