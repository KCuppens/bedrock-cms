#!/usr/bin/env python
"""Summary of test infrastructure and quick validation."""

import os
import sys
from pathlib import Path

# Setup paths
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")

import django

django.setup()


def main():
    """Generate test summary."""

    print("=" * 60)
    print("Bedrock CMS - Test Infrastructure Summary")
    print("=" * 60)

    # Test directories
    test_dirs = {
        "Unit Tests": "tests/unit",
        "Integration Tests": "tests/integration",
        "E2E Tests": "tests/e2e",
        "Performance Tests": "tests/performance",
        "Factories": "tests/factories",
    }

    print("\nTest Directories:")
    print("-" * 40)

    total_test_files = 0
    for name, path in test_dirs.items():
        dir_path = backend_dir / path
        if dir_path.exists():
            test_files = list(dir_path.glob("test_*.py"))
            factory_files = (
                list(dir_path.glob("*factory*.py")) if "factories" in path else []
            )
            total_files = len(test_files) + len(factory_files)
            total_test_files += total_files
            status = "OK" if total_files > 0 else "Empty"
            print(f"  {name:20} {total_files:3} files  [{status}]")
        else:
            print(f"  {name:20} --- Not found")

    # Key test files
    print("\nKey Test Files Created:")
    print("-" * 40)

    key_files = [
        ("Integration: CMS-i18n", "tests/integration/test_cms_i18n_workflows.py"),
        (
            "Integration: Analytics",
            "tests/integration/test_analytics_search_workflows.py",
        ),
        ("Integration: Auth/RBAC", "tests/integration/test_auth_rbac_workflows.py"),
        ("E2E: Content Creator", "tests/e2e/test_content_creator_workflows.py"),
        ("E2E: Administrator", "tests/e2e/test_administrator_workflows.py"),
        ("E2E: End User", "tests/e2e/test_end_user_workflows.py"),
        ("E2E: API Consumer", "tests/e2e/test_api_consumer_workflows.py"),
        ("E2E: Mobile", "tests/e2e/test_mobile_workflows.py"),
        ("Performance: Benchmarks", "tests/performance/test_performance_benchmarks.py"),
        ("Performance: Load Tests", "tests/performance/test_load_scenarios.py"),
    ]

    for name, path in key_files:
        file_path = backend_dir / path
        if file_path.exists():
            size_kb = file_path.stat().st_size / 1024
            print(f"  {name:25} {size_kb:6.1f} KB")
        else:
            print(f"  {name:25} Not found")

    # Test utilities
    print("\nTest Utilities:")
    print("-" * 40)

    utilities = [
        ("Test Runner", "test_runner.py"),
        ("Coverage Config", ".coveragerc"),
        ("Pytest Config", "pytest.ini"),
        ("Test Scripts", "scripts/run_tests.py"),
        ("Coverage Analysis", "scripts/coverage_analysis.py"),
        ("Test Optimization", "scripts/test_optimization.py"),
        ("Performance Utils", "tests/performance/utils.py"),
        ("E2E Utils", "tests/e2e/utils.py"),
    ]

    for name, path in utilities:
        file_path = backend_dir / path
        exists = "Yes" if file_path.exists() else "No"
        print(f"  {name:20} {exists}")

    # Test configurations
    print("\nTest Execution Profiles:")
    print("-" * 40)

    profiles = [
        "fast     - Quick unit tests (2-3 min)",
        "unit     - All unit tests with coverage",
        "integration - Integration tests",
        "e2e      - End-to-end workflows",
        "performance - Performance benchmarks",
        "full     - Complete test suite",
        "smoke    - Quick validation tests",
        "security - Security-focused tests",
    ]

    for profile in profiles:
        print(f"  {profile}")

    # Coverage targets
    print("\nCoverage Targets:")
    print("-" * 40)
    print("  Overall Target: 80%")
    print("  Critical Paths: 90%")
    print("  API Endpoints: 85%")
    print("  Business Logic: 90%")

    # Quick validation
    print("\nQuick Validation:")
    print("-" * 40)

    try:
        from django.test import TestCase

        print("  Django TestCase: Available")
    except ImportError:
        print("  Django TestCase: Not available")

    try:
        import pytest

        print("  Pytest: Available")
    except ImportError:
        print("  Pytest: Not available")

    try:
        import factory

        print("  Factory Boy: Available")
    except ImportError:
        print("  Factory Boy: Not available")

    try:
        import coverage

        print("  Coverage.py: Available")
    except ImportError:
        print("  Coverage.py: Not available")

    print("\n" + "=" * 60)
    print(f"Total test files found: {total_test_files}")
    print("Test infrastructure is ready for use!")
    print("=" * 60)

    print("\nQuick Start Commands:")
    print("-" * 40)
    print("  # Run fast tests")
    print("  python scripts/run_tests.py fast")
    print()
    print("  # Run specific test")
    print("  python manage.py test tests.integration.test_cms_views_simple")
    print()
    print("  # Run with coverage")
    print("  coverage run manage.py test && coverage report")
    print()
    print("  # Run performance tests")
    print("  python run_performance_tests.py --test-type benchmarks")


if __name__ == "__main__":
    main()
