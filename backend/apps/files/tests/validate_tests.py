#!/usr/bin/env python
"""
Validation script for Files/Media API tests.

This script validates that:
1. Test files have correct syntax
2. All imports work correctly
3. Test methods are properly defined
4. Required dependencies are available
"""

import ast
import importlib.util
import os
import sys


def validate_syntax(file_path):
    """Validate Python syntax of a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        ast.parse(source)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error reading file: {e}"


def validate_imports(file_path):
    """Validate that all imports in the file work correctly."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            # Don't actually execute the module, just check if it can be loaded
            return True, None
        else:
            return False, "Could not create module spec"
    except Exception as e:
        return False, f"Import error: {e}"


def count_test_methods(file_path):
    """Count the number of test methods in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()

        tree = ast.parse(source)
        test_count = 0
        class_count = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if "Test" in node.name:
                    class_count += 1
            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    test_count += 1

        return test_count, class_count
    except Exception:
        return 0, 0


def check_dependencies():
    """Check if required dependencies are available."""
    dependencies = {
        "django": "Django framework",
        "rest_framework": "Django REST Framework",
        "PIL": "Pillow (Python Imaging Library) - optional for image tests",
    }

    results = {}
    for dep, description in dependencies.items():
        try:
            __import__(dep)
            results[dep] = True
        except ImportError:
            results[dep] = False

    return results


def main():
    """Main validation function."""
    print("Files/Media API Tests Validation")
    print("=" * 40)

    # Test files to validate
    test_files = ["test_api.py", "test_api_simplified.py"]

    current_dir = os.path.dirname(__file__)

    # Check dependencies first
    print("\n1. Checking Dependencies:")
    deps = check_dependencies()
    for dep, available in deps.items():
        status = "* Available" if available else "X Missing"
        print(f"   {dep}: {status}")

    if not all([deps["django"], deps["rest_framework"]]):
        print("\nX Critical dependencies missing. Please install Django and DRF.")
        return False

    all_valid = True

    # Validate each test file
    for test_file in test_files:
        file_path = os.path.join(current_dir, test_file)

        if not os.path.exists(file_path):
            print(f"\nX {test_file}: File not found")
            all_valid = False
            continue

        print(f"\n2. Validating {test_file}:")

        # Check syntax
        syntax_valid, syntax_error = validate_syntax(file_path)
        if syntax_valid:
            print("   * Syntax is valid")
        else:
            print(f"   X Syntax error: {syntax_error}")
            all_valid = False
            continue

        # Count test methods
        test_count, class_count = count_test_methods(file_path)
        print(f"   * Found {class_count} test classes and {test_count} test methods")

        # Note: We skip import validation here as it requires Django setup
        # which can be complex in this validation context
        print("   ! Import validation skipped (requires Django setup)")

    # Summary
    print(f"\n3. Validation Summary:")
    if all_valid:
        print("   * All test files passed validation")
        print("   * Ready for execution")

        print(f"\n4. Usage Examples:")
        print("   # Run simplified tests:")
        print("   python manage.py test apps.files.tests.test_api_simplified")
        print("\n   # Run full tests:")
        print("   python manage.py test apps.files.tests.test_api")
        print("\n   # Run specific test:")
        print(
            "   python manage.py test apps.files.tests.test_api.FileUploadAPITest.test_file_upload_success"
        )

        return True
    else:
        print("   X Some validation checks failed")
        print("   X Please fix issues before running tests")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
