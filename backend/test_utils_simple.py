#!/usr/bin/env python
"""
Simple test script to test utility functions without Django migrations.
"""

import os
import sys

sys.path.append(".")

# Set up Django without migrations
os.environ["DJANGO_SETTINGS_MODULE"] = "apps.config.settings.test"

import django

django.setup()


# Test analytics utils
def test_analytics_utils():
    from apps.analytics.utils import clean_referrer, format_duration, is_bot_user_agent

    print("Testing analytics utility functions...")

    # Test format_duration
    assert format_duration(45) == "45s"
    assert format_duration(125) == "2m 5s"
    assert format_duration(3665) == "1h 1m"
    print("PASS: format_duration tests passed")

    # Test is_bot_user_agent
    assert is_bot_user_agent("Googlebot/2.1") == True
    assert is_bot_user_agent("Mozilla/5.0 Chrome") == False
    assert is_bot_user_agent("curl/7.64.1") == True
    print("PASS: is_bot_user_agent tests passed")

    # Test clean_referrer
    assert (
        clean_referrer("https://example.com/page?param=value#section")
        == "https://example.com/page"
    )
    assert clean_referrer("") == ""
    print("PASS: clean_referrer tests passed")

    print("All analytics utils tests passed!")


if __name__ == "__main__":
    test_analytics_utils()
    print("\nUtility functions work without database migrations! 🎉")
