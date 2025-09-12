#!/usr/bin/env python3
"""Script to fix type annotations in blog models and versioning"""

import re


def fix_blog_files():
    """Fix Django model field type annotations in blog app"""

    files = ["backend/apps/blog/models.py", "backend/apps/blog/versioning.py"]

    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Add necessary imports if not present
        if "from django.db.models import" not in content and "models.py" in file_path:
            # Find the import section and add our imports
            import_pattern = r"(from django\.db import models.*\n)"
            replacement = r"\1from django.db.models import (\n    CharField, TextField, BooleanField, DateTimeField, ForeignKey, \n    ManyToManyField, ImageField, PositiveIntegerField, UUIDField\n)\n"
            content = re.sub(import_pattern, replacement, content)

        if "versioning.py" in file_path:
            # Add imports for versioning.py
            if "from django.db.models import" not in content:
                import_pattern = r"(from django\.db import models.*\n)"
                replacement = r"\1from django.db.models import CharField, TextField, BooleanField, DateTimeField, ForeignKey, PositiveIntegerField, UUIDField\n"
                content = re.sub(import_pattern, replacement, content)

            # Fix User type alias issue in versioning.py
            if "User = get_user_model()" in content:
                content = re.sub(
                    r"User = get_user_model\(\)",
                    "# Define User type properly for mypy\nif TYPE_CHECKING:\n    from django.contrib.auth.models import AbstractUser as User\nelse:\n    User = get_user_model()",
                    content,
                )
                # Add TYPE_CHECKING import if not present
                if "TYPE_CHECKING" not in content:
                    content = re.sub(
                        r"(from typing import.*)", r"\1, TYPE_CHECKING", content
                    )

            # Fix timezone.datetime imports
            content = re.sub(r"timezone\.datetime", r"datetime.datetime", content)
            # Add datetime import if not present
            if "import datetime" not in content:
                content = re.sub(
                    r"(from django\.utils import timezone)",
                    r"\1\nimport datetime",
                    content,
                )

        # Define field patterns and their type annotations
        field_patterns = [
            (
                r"(\s+)(\w+)\s*=\s*models\.CharField\(",
                r"\1\2: CharField = models.CharField(",
            ),
            (
                r"(\s+)(\w+)\s*=\s*models\.TextField\(",
                r"\1\2: TextField = models.TextField(",
            ),
            (
                r"(\s+)(\w+)\s*=\s*models\.BooleanField\(",
                r"\1\2: BooleanField = models.BooleanField(",
            ),
            (
                r"(\s+)(\w+)\s*=\s*models\.DateTimeField\(",
                r"\1\2: DateTimeField = models.DateTimeField(",
            ),
            (
                r"(\s+)(\w+)\s*=\s*models\.ForeignKey\(",
                r"\1\2: ForeignKey = models.ForeignKey(",
            ),
            (
                r"(\s+)(\w+)\s*=\s*models\.ManyToManyField\(",
                r"\1\2: ManyToManyField = models.ManyToManyField(",
            ),
            (
                r"(\s+)(\w+)\s*=\s*models\.ImageField\(",
                r"\1\2: ImageField = models.ImageField(",
            ),
            (
                r"(\s+)(\w+)\s*=\s*models\.PositiveIntegerField\(",
                r"\1\2: PositiveIntegerField = models.PositiveIntegerField(",
            ),
            (
                r"(\s+)(\w+)\s*=\s*models\.UUIDField\(",
                r"\1\2: UUIDField = models.UUIDField(",
            ),
        ]

        # Apply all patterns
        for pattern, replacement in field_patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        # Write back the fixed content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"Fixed Django model field type annotations in {file_path}")


if __name__ == "__main__":
    fix_blog_files()
