#!/usr/bin/env python
"""Run pytest with proper configuration."""

import os
import subprocess
import sys

# Set test settings
os.environ["DJANGO_SETTINGS_MODULE"] = "apps.config.settings.test_minimal"

# Run pytest with a timeout
result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "test_simple.py",
        "-v",
        "--tb=short",
        "--timeout=5",
    ],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    capture_output=True,
    text=True,
    timeout=30,
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

sys.exit(result.returncode)
