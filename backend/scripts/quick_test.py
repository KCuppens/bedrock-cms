#!/usr/bin/env python
"""Quick test runner for Phase 8 tests."""

import os
import subprocess
import sys
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")


def run_test(test_path, timeout=30):
    """Run a specific test with timeout."""
    cmd = [
        sys.executable,
        "manage.py",
        "test",
        test_path,
        "--keepdb",
        "--verbosity",
        "0",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Test timed out after {timeout} seconds"
    except Exception as e:
        return False, "", str(e)


def main():
    """Run Phase 8 tests."""

    tests = [
        # Simple integration tests that should pass
        (
            "CMS-i18n Simple",
            "tests.integration.test_cms_i18n_simple.SimpleCMSi18nIntegrationTest.test_page_creation_with_locale",
        ),
        (
            "CMS-i18n Translation",
            "tests.integration.test_cms_i18n_simple.SimpleCMSi18nIntegrationTest.test_page_with_translation_unit",
        ),
        (
            "CMS-i18n Multilingual",
            "tests.integration.test_cms_i18n_simple.SimpleCMSi18nIntegrationTest.test_multilingual_page_creation",
        ),
        (
            "CMS-i18n Locale",
            "tests.integration.test_cms_i18n_simple.SimpleCMSi18nIntegrationTest.test_locale_fallback_chain",
        ),
        # Simple CMS view tests
        (
            "CMS Views Basic",
            "tests.integration.test_cms_views_simple.PagesViewSetBasicTestCase.test_get_queryset_optimization",
        ),
        (
            "CMS Views Path",
            "tests.integration.test_cms_views_simple.PagesViewSetBasicTestCase.test_get_by_path_success",
        ),
        (
            "CMS Views Tree",
            "tests.integration.test_cms_views_simple.PagesViewSetBasicTestCase.test_tree_endpoint",
        ),
    ]

    print("=" * 60)
    print("Phase 8 Test Verification")
    print("=" * 60)

    passed = 0
    failed = 0
    errors = []

    for name, test_path in tests:
        print(f"\nTesting {name}...")
        success, stdout, stderr = run_test(test_path, timeout=20)

        if success:
            print(f"  [PASSED]")
            passed += 1
        else:
            print(f"  [FAILED]")
            failed += 1
            if stderr:
                errors.append((name, stderr[:200]))

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if errors:
        print("\nErrors:")
        for name, error in errors:
            print(f"\n{name}:")
            print(f"  {error}")

    print("\n" + "=" * 60)

    if failed == 0:
        print("[SUCCESS] All Phase 8 tests are passing!")
        return 0
    else:
        print(f"[WARNING] {failed} tests need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
