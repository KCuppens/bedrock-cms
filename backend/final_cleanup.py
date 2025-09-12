#!/usr/bin/env python
"""
Final cleanup script to fix remaining issues.
"""

import os
import re
from pathlib import Path


def fix_missing_pass_statements(content):
    """Fix missing pass statements in except blocks."""
    lines = content.split('\n')
    fixed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Look for except blocks without proper pass statements
        if 'except Exception:' in line:
            # Check if next line is properly indented and has pass
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.strip() == '' and i + 2 < len(lines):
                    # Check the line after empty line
                    line_after_empty = lines[i + 2]
                    if (line_after_empty.strip() != 'pass' and 
                        not line_after_empty.strip().startswith('#') and
                        line_after_empty.strip() != ''):
                        # Add pass statement with proper indentation
                        indent = ' ' * (len(line) - len(line.lstrip()) + 4)
                        fixed_lines.append(line)
                        fixed_lines.append(next_line)  # Keep empty line
                        fixed_lines.append(indent + 'pass')
                        i += 2
                        continue
                elif (next_line.strip() != 'pass' and 
                      not next_line.strip().startswith('#') and
                      next_line.strip() != '' and
                      not next_line.strip().startswith('except')):
                    # Add pass statement
                    indent = ' ' * (len(line) - len(line.lstrip()) + 4)
                    fixed_lines.append(line)
                    fixed_lines.append(indent + 'pass')
                    i += 1
                    continue
        
        fixed_lines.append(line)
        i += 1
    
    return '\n'.join(fixed_lines)


def fix_missing_docstrings(content):
    """Fix missing docstring quotes."""
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Look for lines that look like they should be docstrings
        if ('Files app coverage booster' in line or
            'Enhanced coverage booster' in line) and not line.strip().startswith('"""'):
            # Add docstring quotes
            indent = ' ' * (len(line) - len(line.lstrip()))
            fixed_lines.append(indent + '"""' + line.strip() + '"""')
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def fix_import_statements(content):
    """Fix any remaining import issues."""
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Fix specific import issues
        if 'from apps.i18n.models import (' in line:
            # Make sure we have proper import syntax
            fixed_lines.append('        from apps.i18n.models import (')
        elif 'from apps.i18n.serializers import (' in line:
            fixed_lines.append('        from apps.i18n.serializers import (')
        else:
            fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def process_file(file_path):
    """Process a single file to fix remaining issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply fixes
        content = fix_missing_pass_statements(content)
        content = fix_missing_docstrings(content)
        content = fix_import_statements(content)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def main():
    """Main function to apply final cleanup."""
    # Target specific files that had issues
    problem_files = [
        'apps/accounts/coverage_booster.py',
        'apps/blog/coverage_booster.py',
        'apps/cms/coverage_booster.py',
        'apps/cms/enhanced_coverage_booster.py',
        'apps/files/coverage_booster.py',
        'apps/i18n/coverage_booster.py'
    ]
    
    fixed_files = 0
    
    for file_path in problem_files:
        full_path = Path(file_path)
        if full_path.exists():
            if process_file(full_path):
                fixed_files += 1
                print(f"Applied final cleanup to: {file_path}")
    
    print(f"\nApplied final cleanup to {fixed_files} files")


if __name__ == '__main__':
    main()