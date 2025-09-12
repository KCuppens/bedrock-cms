#!/usr/bin/env python3
"""Fix malformed docstrings that are causing syntax errors."""

import os
import re

def fix_file_docstrings(file_path):
    """Fix malformed docstrings in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix lines that start with quotes but have no assignment or proper function context
        # Pattern: a line that starts with """ but is not part of a proper docstring
        lines = content.split('\n')
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # If line starts with """ and is not properly formatted
            if stripped.startswith('"""') and not stripped.endswith('"""') and len(stripped) > 3:
                # Check if it's at the beginning of file or after imports/class/def
                prev_line = lines[i-1].strip() if i > 0 else ''
                
                # If it's a standalone docstring line, make it a proper comment
                if (i == 0 or 
                    prev_line == '' or 
                    prev_line.startswith('import') or
                    prev_line.startswith('from') or
                    not (prev_line.endswith(':') or prev_line.startswith('def') or prev_line.startswith('class'))):
                    
                    # Convert to comment
                    content_part = stripped[3:]  # Remove the """
                    if content_part.endswith('"""'):
                        content_part = content_part[:-3]
                    
                    # Make it a comment
                    fixed_lines.append(line.replace(stripped, f'# {content_part}'))
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
            
            i += 1
        
        content = '\n'.join(fixed_lines)
        
        # Additional patterns to fix
        patterns = [
            # Fix annotation syntax errors
            (r'^\s*"""([^"]+):\s*$', r'# \1'),  # Convert malformed annotations
            (r'^\s*"""([^"]*?[^\.])$', r'# \1'),  # Convert incomplete docstrings to comments
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False
    
    return False

def main():
    """Fix docstring syntax errors in test files."""
    
    # Find all Python test files that might have syntax errors
    error_files = [
        'apps/accounts/tests/test_comprehensive.py',
        'apps/accounts/tests/test_rbac.py', 
        'apps/blog/tests/test_comprehensive.py',
        'apps/cms/test_additional_units.py',
        'apps/cms/test_views_basic.py',
        'apps/cms/tests/test_comprehensive.py',
        'apps/cms/tests/test_models.py',
        'apps/core/tests/test_management_commands.py',
        'apps/files/tests/test_comprehensive.py'
    ]
    
    fixed_count = 0
    
    for file_path in error_files:
        if os.path.exists(file_path):
            if fix_file_docstrings(file_path):
                print(f"Fixed: {file_path}")
                fixed_count += 1
            else:
                print(f"No changes needed: {file_path}")
        else:
            print(f"File not found: {file_path}")
    
    print(f"\nFixed {fixed_count} files")

if __name__ == '__main__':
    main()