#!/usr/bin/env python3
"""Script to fix duplicate type annotations in i18n/models.py"""

import re

def fix_duplicate_annotations():
    """Fix duplicate type annotations like 'field: Type: Type'"""

    file_path = "backend/apps/i18n/models.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix duplicate annotations pattern
    content = re.sub(
        r'(\w+):\s*(\w+):\s*(\w+)\s*=',
        r'\1: \2 =',
        content
    )

    # Write back the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Fixed duplicate type annotations in i18n/models.py")

if __name__ == "__main__":
    fix_duplicate_annotations()