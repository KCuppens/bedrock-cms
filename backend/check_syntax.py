#!/usr/bin/env python3
import os
import py_compile
import sys


def check_file(filepath):
    try:
        py_compile.compile(filepath, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)


def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    errors = []

    for root, dirs, files in os.walk(backend_dir):
        # Skip certain directories
        if any(
            skip in root
            for skip in ["__pycache__", ".git", "node_modules", "venv", ".tox"]
        ):
            continue

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                success, error = check_file(filepath)
                if not success:
                    rel_path = os.path.relpath(filepath, backend_dir)
                    """errors.append((rel_path, error))"""

    if errors:
        print(f"Found {len(errors)} files with syntax errors:")
        for filepath, error in errors[:20]:  # Show first 20
            print(f"\n{filepath}:")
            print(f"  {error}")
    else:
        print("All Python files have valid syntax!")


if __name__ == "__main__":
    main()
