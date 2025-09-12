#!/usr/bin/env python3
"""Script to fix type annotations in accounts models and rbac"""

import re

def fix_accounts_files():
    """Fix Django model field type annotations in accounts app"""

    files = [
        "backend/apps/accounts/models.py",
        "backend/apps/accounts/rbac.py"
    ]

    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Add necessary imports if not present
        if 'from django.db.models import' not in content:
            # Find the import section and add our imports
            import_pattern = r'(from django\.db import models.*\n)'
            replacement = r'\1from django.db.models import CharField, TextField, BooleanField, DateTimeField, ForeignKey, OneToOneField\n'
            content = re.sub(import_pattern, replacement, content)

        # Define field patterns and their type annotations
        field_patterns = [
            (r'(\s+)(\w+)\s*=\s*models\.CharField\(', r'\1\2: CharField = models.CharField('),
            (r'(\s+)(\w+)\s*=\s*models\.TextField\(', r'\1\2: TextField = models.TextField('),
            (r'(\s+)(\w+)\s*=\s*models\.BooleanField\(', r'\1\2: BooleanField = models.BooleanField('),
            (r'(\s+)(\w+)\s*=\s*models\.DateTimeField\(', r'\1\2: DateTimeField = models.DateTimeField('),
            (r'(\s+)(\w+)\s*=\s*models\.ForeignKey\(', r'\1\2: ForeignKey = models.ForeignKey('),
            (r'(\s+)(\w+)\s*=\s*models\.OneToOneField\(', r'\1\2: OneToOneField = models.OneToOneField('),
        ]

        # Apply all patterns
        for pattern, replacement in field_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # Write back the fixed content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"Fixed Django model field type annotations in {file_path}")

if __name__ == "__main__":
    fix_accounts_files()