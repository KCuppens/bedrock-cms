#!/usr/bin/env python
"""
Script to run Files/Media API tests with various options.

Usage:
    python run_api_tests.py [options]

Options:
    --full      Run the full comprehensive test suite
    --simple    Run the simplified test suite (default)
    --class     Run a specific test class
    --method    Run a specific test method
    --coverage  Run with coverage reporting
    --verbose   Run with verbose output
"""

import argparse
import os
import subprocess
import sys

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test")


def run_tests(test_path, verbosity=1, keepdb=False, coverage=False):
    """Run Django tests with specified options."""

    # Base command
    cmd = ["python", "manage.py", "test"]

    # Add test path
    if test_path:
        cmd.append(test_path)

    # Add verbosity
    cmd.extend(["--verbosity", str(verbosity)])

    # Keep database between runs for faster execution
    if keepdb:
        cmd.append("--keepdb")

    # Coverage command wrapper
    if coverage:
        cmd = ["coverage", "run", "--source=apps.files", "--append"] + cmd[1:]

    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(__file__)))
        return result.returncode
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user.")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def main():
    """Main test runner function."""

    parser = argparse.ArgumentParser(description="Run Files/Media API tests")
    parser.add_argument(
        "--full", action="store_true", help="Run full comprehensive test suite"
    )
    parser.add_argument(
        "--simple", action="store_true", help="Run simplified test suite (default)"
    )
    parser.add_argument(
        "--class",
        dest="test_class",
        help="Run specific test class (e.g., FileUploadAPITest)",
    )
    parser.add_argument(
        "--method",
        dest="test_method",
        help="Run specific test method (e.g., test_file_upload_success)",
    )
    parser.add_argument(
        "--coverage", action="store_true", help="Run with coverage reporting"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Run with verbose output"
    )
    parser.add_argument(
        "--keepdb", action="store_true", help="Keep test database between runs"
    )

    args = parser.parse_args()

    # Determine verbosity
    verbosity = 2 if args.verbose else 1

    # Determine test path
    test_path = None

    if args.method:
        # Specific test method
        if "." not in args.method:
            print(
                "Error: Method must include class (e.g., FileUploadAPITest.test_file_upload_success)"
            )
            return 1
        test_path = f"apps.files.tests.test_api.{args.method}"
    elif args.test_class:
        # Specific test class
        test_path = f"apps.files.tests.test_api.{args.test_class}"
    elif args.full:
        # Full test suite
        test_path = "apps.files.tests.test_api"
    else:
        # Default to simplified suite
        test_path = "apps.files.tests.test_api_simplified"

    # Run the tests
    return run_tests(test_path, verbosity, args.keepdb, args.coverage)


if __name__ == "__main__":
    sys.exit(main())
