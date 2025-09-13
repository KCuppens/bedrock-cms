#!/usr/bin/env python
"""Debug Django setup to find where it's hanging."""

import sys
import traceback


def trace_calls(frame, event, arg):
    if event == "call":
        code = frame.f_code
        print(f"Calling: {code.co_filename}:{code.co_name}:{frame.f_lineno}")
    return trace_calls


# Set trace
sys.settrace(trace_calls)

try:
    from django.conf import settings

    print("\n=== Configuring settings ===")
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test",  # nosec B106 - Debug script only, not for production
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=["django.contrib.contenttypes"],
    )

    print("\n=== About to call django.setup() ===")
    import django

    django.setup()
    print("\n=== Django setup complete ===")

except Exception as e:
    print(f"\nError: {e}")
    traceback.print_exc()
finally:
    sys.settrace(None)
