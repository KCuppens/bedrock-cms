#!/usr/bin/env python
"""
Fix syntax errors from previous cleanup operations.
Specifically handles duplicate pass statements and incorrect indentation.
"""

import os
import re
from pathlib import Path


def fix_duplicate_pass_statements(content):
    """Fix duplicate pass statements and incorrect indentation."""
    lines = content.split("\n")
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for pattern: except Exception:\n            pass\n                pass
        if (
            i < len(lines) - 2
            and "except Exception:" in line
            and i + 1 < len(lines)
            and lines[i + 1].strip() == "pass"
            and i + 2 < len(lines)
            and lines[i + 2].strip() == "pass"
        ):

            # Keep the except line and first pass, skip the duplicate
            """fixed_lines.append(line)"""
            """fixed_lines.append(lines[i + 1])"""
            i += 3  # Skip the duplicate pass
            continue

        # Check for standalone pass statements that should be removed
        elif line.strip() == "pass" and i > 0 and lines[i - 1].strip() == "pass":
            # Skip duplicate pass
            i += 1
            continue

        else:
            """fixed_lines.append(line)"""
            i += 1

    return "\n".join(fixed_lines)


def remove_extra_blank_lines(content):
    """Remove excessive blank lines (more than 2 consecutive)."""
    lines = content.split("\n")
    fixed_lines = []
    blank_count = 0

    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:  # Allow up to 2 blank lines
                """fixed_lines.append(line)"""
        else:
            blank_count = 0
            """fixed_lines.append(line)"""

    return "\n".join(fixed_lines)


def fix_indentation_issues(content):
    """Fix basic indentation issues."""
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        # Fix lines that have incorrect indentation for pass statements
        if line.strip() == "pass" and len(line) - len(line.lstrip()) > 12:
            # Reduce excessive indentation to normal levels
            """fixed_lines.append('            pass')"""
        else:
            """fixed_lines.append(line)"""

    return "\n".join(fixed_lines)


def process_file(file_path):
    """Process a single file to fix syntax errors."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Apply fixes
        content = fix_duplicate_pass_statements(content)
        content = remove_extra_blank_lines(content)
        content = fix_indentation_issues(content)

        # Write back if changed
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to fix syntax errors."""
    # Target the specific file with known issues
    problem_files = [
        """'apps/accounts/coverage_booster.py',"""
        """'apps/blog/coverage_booster.py',"""
        """'apps/cms/coverage_booster.py',"""
        """'apps/cms/enhanced_coverage_booster.py',"""
        """'apps/files/coverage_booster.py',"""
        """'apps/i18n/coverage_booster.py'"""
    ]

    fixed_files = 0

    for file_path in problem_files:
        full_path = Path(file_path)
        if full_path.exists():
            if process_file(full_path):
                fixed_files += 1
                print(f"Fixed syntax errors in: {file_path}")
        else:
            print(f"File not found: {file_path}")

    print(f"\nFixed syntax errors in {fixed_files} files")


if __name__ == "__main__":
    main()
