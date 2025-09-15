#!/usr/bin/env python
"""Quick test verification script to ensure test infrastructure is working."""

import os
import sys
from pathlib import Path

import django

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.config.settings.test_minimal")
django.setup()


def verify_test_structure():
    """Verify test directories and files exist."""
    test_dirs = [
        "tests/integration",
        "tests/e2e",
        "tests/performance",
        "tests/factories",
    ]

    print("🔍 Verifying test structure...")
    all_good = True

    for test_dir in test_dirs:
        dir_path = backend_dir / test_dir
        if dir_path.exists():
            test_files = list(dir_path.glob("test_*.py"))
            print(f"✅ {test_dir}: {len(test_files)} test files")
        else:
            print(f"❌ {test_dir}: Directory not found")
            all_good = False

    return all_good


def verify_imports():
    """Verify key test dependencies can be imported."""
    print("\n🔍 Verifying test dependencies...")

    dependencies = [
        ("factory", "Factory Boy"),
        ("faker", "Faker"),
        ("pytest", "Pytest"),
        ("coverage", "Coverage"),
        ("django.test", "Django Test Framework"),
        ("rest_framework.test", "DRF Test Framework"),
    ]

    all_good = True
    for module, name in dependencies:
        try:
            __import__(module)
            print(f"✅ {name}: Available")
        except ImportError as e:
            print(f"❌ {name}: Not available - {e}")
            all_good = False

    return all_good


def verify_models():
    """Verify key models can be imported."""
    print("\n🔍 Verifying model imports...")

    models = [
        ("apps.cms.models", "Page"),
        ("apps.blog.models", "BlogPost"),
        ("apps.i18n.models", "Locale"),
        ("apps.analytics.models", "PageView"),
        ("apps.search.models", "SearchIndex"),
    ]

    all_good = True
    for module_path, model_name in models:
        try:
            module = __import__(module_path, fromlist=[model_name])
            getattr(module, model_name)
            print(f"✅ {module_path}.{model_name}: Available")
        except (ImportError, AttributeError) as e:
            print(f"❌ {module_path}.{model_name}: Not available - {e}")
            all_good = False

    return all_good


def run_sample_test():
    """Run a simple test to verify Django test framework works."""
    print("\n🔍 Running sample test...")

    try:
        from django.contrib.auth import get_user_model
        from django.test import TestCase

        User = get_user_model()

        class QuickTest(TestCase):
            def test_user_creation(self):
                user = User.objects.create_user(
                    email="test@example.com", password="testpass123"
                )
                self.assertEqual(user.email, "test@example.com")
                self.assertTrue(user.check_password("testpass123"))

        # Run the test
        from django.test.runner import DiscoverRunner

        runner = DiscoverRunner(verbosity=0, interactive=False)
        test_suite = runner.test_loader.loadTestsFromTestCase(QuickTest)
        result = runner.run_suite(test_suite)

        if result.wasSuccessful():
            print("✅ Sample test passed")
            return True
        else:
            print("❌ Sample test failed")
            return False

    except Exception as e:
        print(f"❌ Error running sample test: {e}")
        return False


def main():
    """Main verification routine."""
    print("=" * 60)
    print("🚀 Bedrock CMS Test Infrastructure Verification")
    print("=" * 60)

    results = []

    # Run verifications
    results.append(verify_test_structure())
    results.append(verify_imports())
    results.append(verify_models())
    results.append(run_sample_test())

    # Summary
    print("\n" + "=" * 60)
    if all(results):
        print("✅ All verifications passed! Test infrastructure is ready.")
        return 0
    else:
        print("⚠️ Some verifications failed. Please check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
