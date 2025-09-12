#!/usr/bin/env python3
"""
Script to fix malformed docstrings in Python files.
Converts standalone docstrings to proper triple-quoted format.
"""

import os
import re
import sys


def fix_docstring_in_content(content):
    """Fix malformed docstrings in file content."""
    lines = content.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this line starts a malformed docstring pattern
        # Pattern 1: Module-level docstring (no indentation, description line)
        if (i == 0 or
            (i > 0 and lines[i-1].strip() == '' and
             not line.startswith(' ') and
             not line.startswith('#') and
             not line.startswith('from ') and
             not line.startswith('import ') and
             not line.startswith('class ') and
             not line.startswith('def ') and
             not line.startswith('@') and
             line.strip() != '' and
             line.endswith('.') and
             len(line.split()) > 2)):

            # Found potential module docstring
            docstring_lines = [line]
            i += 1

            # Collect following lines that are part of the docstring
            while i < len(lines):
                if lines[i].strip() == '':
                    docstring_lines.append(lines[i])
                    i += 1
                elif (lines[i].strip().endswith('.') or
                      lines[i].strip().endswith(':') or
                      not lines[i].startswith((' ', '\t')) and
                      not lines[i].startswith(('def ', 'class ', '@', 'from ', 'import '))):
                    docstring_lines.append(lines[i])
                    i += 1
                else:
                    break

            # Convert to proper docstring
            if docstring_lines:
                result_lines.append('"""')
                for doc_line in docstring_lines:
                    if doc_line.strip():
                        result_lines.append(doc_line)
                    else:
                        result_lines.append('')
                result_lines.append('"""')
            continue

        # Pattern 2: Function docstring (indented, after function def)
        elif (line.strip() != '' and
              not line.startswith('#') and
              i > 0 and
              (lines[i-1].strip() == '' or lines[i-1].strip().endswith(':')) and
              line.strip().endswith('.') and
              len(line.split()) > 2 and
              '    ' in line and not line.lstrip().startswith(('def ', 'class ', '@', 'return ', 'if ', 'for ', 'while ', 'try:', 'except'))):

            # Found potential function docstring
            base_indent = len(line) - len(line.lstrip())
            indent = ' ' * base_indent

            docstring_lines = [line.lstrip()]
            i += 1

            # Collect following lines
            while i < len(lines):
                if lines[i].strip() == '':
                    docstring_lines.append('')
                    i += 1
                elif (lines[i].startswith(indent) and
                      (lines[i].strip().endswith('.') or
                       lines[i].strip().endswith(':') or
                       lines[i].strip().startswith(('Args:', 'Returns:', 'Raises:')))):
                    docstring_lines.append(lines[i].lstrip())
                    i += 1
                else:
                    break

            # Convert to proper docstring
            if docstring_lines:
                result_lines.append(f'{indent}"""')
                for doc_line in docstring_lines:
                    if doc_line.strip():
                        result_lines.append(f'{indent}{doc_line}')
                    else:
                        result_lines.append('')
                result_lines.append(f'{indent}"""')
            continue

        result_lines.append(line)
        i += 1

    return '\n'.join(result_lines)


def fix_empty_except_blocks(content):
    """Fix empty except blocks by adding pass statements."""
    lines = content.split('\n')
    result_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        result_lines.append(line)

        # Check if this is an except line
        if line.strip().startswith('except') and line.strip().endswith(':'):
            # Look ahead for empty block
            j = i + 1
            found_empty = True
            indent_level = len(line) - len(line.lstrip()) + 4

            while j < len(lines):
                next_line = lines[j]
                if next_line.strip() == '':
                    j += 1
                    continue

                # If we find content at the expected indent level, not empty
                if len(next_line) - len(next_line.lstrip()) >= indent_level:
                    found_empty = False
                break

            # If empty except block, add pass
            if found_empty:
                result_lines.append(' ' * indent_level + 'pass')

        i += 1

    return '\n'.join(result_lines)


def fix_file(file_path):
    """Fix syntax errors in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        # Apply fixes
        content = original_content
        content = fix_docstring_in_content(content)
        content = fix_empty_except_blocks(content)

        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed: {file_path}")
            return True
        return False

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to process files."""
    if len(sys.argv) < 2:
        print("Usage: python fix_docstrings.py <directory_or_file>")
        sys.exit(1)

    path = sys.argv[1]

    if os.path.isfile(path):
        fix_file(path)
    elif os.path.isdir(path):
        fixed_count = 0
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    if fix_file(file_path):
                        fixed_count += 1
        print(f"Fixed {fixed_count} files")
    else:
        print(f"Path not found: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
