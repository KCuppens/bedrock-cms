#!/usr/bin/env python3
"""Fix remaining syntax errors in test files."""

import os
import re


def fix_syntax_errors(file_path):
    """Fix syntax errors in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix missing colons in class/function definitions
        patterns = [
            # Fix class definitions without colons
            (r"^(\s*class\s+\w+(?:\([^)]*\))?)\s*$", r"\1:"),
            # Fix function definitions without colons
            (r"^(\s*def\s+\w+(?:\([^)]*\))?)\s*$", r"\1:"),
            # Fix if/for/while statements without colons
            (
                r"^(\s*(?:if|for|while|elif|else|with|try|except|finally)\s+[^:]+?)\s*$",
                r"\1:",
            ),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

    return False


def main():
    """Fix syntax errors in test files."""

    # Find all Python files that might have syntax errors
    test_files = []

    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py") and ("test" in file or "test" in root):
                test_files.append(os.path.join(root, file))

    fixed_count = 0

    for file_path in test_files:
        try:
            # Test if file has syntax errors
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Try to parse
            compile(content, file_path, "exec")

        except SyntaxError:
            # File has syntax error, try to fix
            if fix_syntax_errors(file_path):
                print(f"Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"Could not fix: {file_path}")
        except Exception:
            # Other errors, skip
            pass

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
