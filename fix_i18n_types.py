#!/usr/bin/env python3
"""Script to fix type annotations in i18n/models.py"""

import re

def fix_model_fields():
    """Fix Django model field type annotations"""

    file_path = "backend/apps/i18n/models.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define field patterns and their type annotations
    field_patterns = [
        (r'(\s+)(\w+)\s*=\s*models\.CharField\(', r'\1\2: CharField = models.CharField('),
        (r'(\s+)(\w+)\s*=\s*models\.TextField\(', r'\1\2: TextField = models.TextField('),
        (r'(\s+)(\w+)\s*=\s*models\.BooleanField\(', r'\1\2: BooleanField = models.BooleanField('),
        (r'(\s+)(\w+)\s*=\s*models\.PositiveIntegerField\(', r'\1\2: PositiveIntegerField = models.PositiveIntegerField('),
        (r'(\s+)(\w+)\s*=\s*models\.DateTimeField\(', r'\1\2: DateTimeField = models.DateTimeField('),
        (r'(\s+)(\w+)\s*=\s*models\.ForeignKey\(', r'\1\2: ForeignKey = models.ForeignKey('),
        (r'(\s+)(\w+)\s*=\s*models\.OneToOneField\(', r'\1\2: OneToOneField = models.OneToOneField('),
        (r'(\s+)(\w+)\s*=\s*models\.DecimalField\(', r'\1\2: DecimalField = models.DecimalField('),
    ]

    # Apply all patterns
    for pattern, replacement in field_patterns:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Write back the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print("Fixed Django model field type annotations in i18n/models.py")

if __name__ == "__main__":
    fix_model_fields()