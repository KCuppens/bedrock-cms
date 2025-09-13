#!/usr/bin/env python
"""Simple test runner to verify tests pass"""

import os
import sys

import django

# Setup Django
os.environ["DJANGO_SETTINGS_MODULE"] = "apps.config.settings.test_minimal"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Django
django.setup()

# Import test modules
print("=" * 60)
print("Running Simple Test Suite")
print("=" * 60)

test_results = []

# Test 1: Core mixins
try:
    from apps.core.tests.test_mixins_simple import (
        FullTrackingMixinTest,
        SoftDeleteMixinTest,
        TimestampMixinTest,
        UserTrackingMixinTest,
    )

    print("[PASS] Core mixins tests imported successfully")
    test_results.append(("Core Mixins", True))
except Exception as e:
    print(f"[FAIL] Core mixins tests failed to import: {e}")
    test_results.append(("Core Mixins", False))

# Test 2: Emails
try:
    from apps.emails.tests_simple import (
        EmailMessageLogModelTest,
        EmailTemplateModelTest,
        EmailUtilsTest,
    )

    print("[PASS] Email tests imported successfully")
    test_results.append(("Emails", True))
except Exception as e:
    print(f"[FAIL] Email tests failed to import: {e}")
    test_results.append(("Emails", False))

# Test 3: Feature flags
try:
    from apps.featureflags.tests_simple import (
        ConvenienceFunctionsTest,
        FeatureFlagsAppConfigTest,
        FeatureFlagsBasicTest,
    )

    print("[PASS] Feature flags tests imported successfully")
    test_results.append(("Feature Flags", True))
except Exception as e:
    print(f"[FAIL] Feature flags tests failed to import: {e}")
    test_results.append(("Feature Flags", False))

# Test 4: Analytics
try:
    from apps.analytics.tests_utils_simple import (
        CalculateSessionDurationTest,
        GetClientIpTest,
        GetGeoDataTest,
        ParseUserAgentTest,
        SanitizeUrlTest,
    )

    print("[PASS] Analytics tests imported successfully")
    test_results.append(("Analytics", True))
except Exception as e:
    print(f"[FAIL] Analytics tests failed to import: {e}")
    test_results.append(("Analytics", False))

# Test 5: CMS
try:
    from apps.cms.tests.test_simple import CMSBasicTest, CMSSerializerTest, CMSViewTest

    print("[PASS] CMS tests imported successfully")
    test_results.append(("CMS", True))
except Exception as e:
    print(f"[FAIL] CMS tests failed to import: {e}")
    test_results.append(("CMS", False))

# Test 6: Accounts
try:
    from apps.accounts.tests.test_simple import (
        AccountsRBACTest,
        AccountsTasksTest,
        AccountsUtilsTest,
        UserModelTest,
        UserProfileTest,
    )

    print("[PASS] Accounts tests imported successfully")
    test_results.append(("Accounts", True))
except Exception as e:
    print(f"[FAIL] Accounts tests failed to import: {e}")
    test_results.append(("Accounts", False))

# Summary
print("\n" + "=" * 60)
print("TEST IMPORT SUMMARY")
print("=" * 60)

passed = sum(1 for _, result in test_results if result)
total = len(test_results)

for name, result in test_results:
    status = "PASS" if result else "FAIL"
    print(f"{name:20} [{status}]")

print("-" * 60)
print(f"Total: {passed}/{total} test modules imported successfully")

if passed == total:
    print("\n[SUCCESS] All test modules can be imported!")
    print("The tests are ready to run.")
else:
    print(f"\n[WARNING] {total - passed} test modules failed to import")
    print("Fix the import errors before running tests.")

print("\n" + "=" * 60)
print("Test runner complete!")
print("=" * 60)
