#!/usr/bin/env python3
"""Final comprehensive flake8 fixes."""

import os
import re


def fix_line_length(content):
    """Fix lines that are too long."""
    lines = content.split("\n")
    fixed_lines = []

    for line in lines:
        if len(line) > 79:
            # Handle different cases
            if (
                "self.assertEqual" in line
                or "self.assertIn" in line
                or "self.assertTrue" in line
            ):
                # Split assertions
                if "(" in line and ")" in line:
                    indent = len(line) - len(line.lstrip())
                    parts = line.split("(", 1)
                    if len(parts) == 2:
                        prefix = parts[0]
                        args = parts[1].rstrip(")")
                        if "," in args:
                            arg_parts = args.split(",", 1)
                            fixed_lines.append(prefix + "(")
                            fixed_lines.append(
                                " " * (indent + 4) + arg_parts[0].strip() + ","
                            )
                            fixed_lines.append(
                                " " * (indent + 4) + arg_parts[1].strip()
                            )
                            fixed_lines.append(" " * indent + ")")
                        else:
                            fixed_lines.append(line)
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            elif "response.data" in line and "[" in line:
                # Split response.data accesses
                indent = len(line) - len(line.lstrip())
                if "self.assert" in line:
                    parts = line.split("(", 1)
                    if len(parts) == 2:
                        prefix = parts[0]
                        args = parts[1].rstrip(")")
                        fixed_lines.append(prefix + "(")
                        fixed_lines.append(" " * (indent + 4) + args.strip())
                        fixed_lines.append(" " * indent + ")")
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)
            elif "# " in line and len(line.split("# ")[0]) < 70:
                # Split comments
                code_part = line.split("# ")[0]
                comment_part = "# " + "# ".join(line.split("# ")[1:])
                if len(comment_part) > 79 - len(code_part):
                    indent = len(code_part) - len(code_part.lstrip())
                    fixed_lines.append(code_part)
                    fixed_lines.append(" " * indent + comment_part[: 79 - indent])
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        else:
            fixed_lines.append(line)

    return "\n".join(fixed_lines)


def fix_undefined_names(content, filepath):
    """Fix undefined names based on file context."""

    if "cms/tests/test_comprehensive.py" in filepath:
        # Fix Group references
        if "from apps.cms.models import" in content and "Group" not in content:
            content = content.replace(
                "from apps.cms.models import Page",
                "from apps.cms.models import Page, Group",
            )

        # Fix ContentBlock references
        if "ContentBlock" in content and "from apps.cms.models import" in content:
            if ", ContentBlock" not in content and "ContentBlock," not in content:
                content = content.replace(
                    "from apps.cms.models import Page, Group",
                    "from apps.cms.models import Page, Group, ContentBlock",
                )

    elif "files/tests/test_comprehensive.py" in filepath:
        # Add imports for File models
        if "from apps.files.models import" not in content:
            import_line = "from apps.files.models import File, FileTag, FileVersion, MediaCategory"
            # Add after other imports
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("from apps.") or line.startswith("import "):
                    continue
                elif line.strip() == "":
                    lines.insert(i, import_line)
                    break
            content = "\n".join(lines)

    elif "blog/tests/test_comprehensive.py" in filepath:
        # Fix UserSerializer
        if (
            "UserSerializer" in content
            and "from apps.accounts.serializers import UserSerializer" not in content
        ):
            # Add import
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "from apps.blog.serializers import" in line:
                    lines.insert(
                        i + 1, "from apps.accounts.serializers import UserSerializer"
                    )
                    break
            content = "\n".join(lines)

    return content


def fix_specific_long_lines(content, filepath):
    """Fix specific long lines that are hard to handle generically."""
    lines = content.split("\n")
    fixed_lines = []

    for i, line in enumerate(lines):
        line_num = i + 1

        # Fix specific lines based on file and line number
        if "cms/serializers.py" in filepath:
            if line_num == 48 and 'if "component"' in line:
                fixed_lines.append("            # Add component field if not present")
                fixed_lines.append(
                    '            if ("component" not in processed_block and'
                )
                fixed_lines.append('                    "type" in processed_block):')
                continue
            elif line_num == 49:
                continue  # Skip the old line 49
            elif line_num == 50:
                continue  # Skip the old line 50
            elif line_num == 77 and "Return SEO links" in line:
                fixed_lines.append(
                    '        """Return SEO links (canonical + alternates)'
                )
                fixed_lines.append('        if with_seo=1 parameter is provided."""')
                continue
            elif line_num == 91 and 'print(f"DEBUG:' in line:
                fixed_lines.append(
                    '        # print(f"DEBUG: get_recent_revisions called for'
                )
                fixed_lines.append('        #        page {obj.id} in serializers.py")')
                continue
            elif line_num == 93 and "Return mock revision" in line:
                fixed_lines.append("        # Return mock revision data since database")
                fixed_lines.append("        # versioning isn't configured yet")
                continue
            elif line_num == 135 and "print(" in line:
                fixed_lines.append(
                    '        # print(f"DEBUG: Returning {len(mock_revisions)}'
                )
                fixed_lines.append(
                    '        #       mock revisions from serializers.py")'
                )
                continue
            elif line_num == 145 and '"id", "title"' in line:
                fixed_lines.append("        fields = [")
                fixed_lines.append(
                    '            "id", "title", "slug", "path", "position",'
                )
                fixed_lines.append('            "status", "children_count"')
                fixed_lines.append("        ]")
                continue
            elif line_num == 205 and "scheduled_unpublish_at" in line:
                fixed_lines.append('                    {"scheduled_unpublish_at":')
                fixed_lines.append(
                    '                     "Must be after scheduled publish time"}'
                )
                continue

        elif "cms/serializers/pages.py" in filepath:
            if line_num == 32 and "children_pages" in line:
                fixed_lines.append(
                    "            children_pages = serializer.Meta.model.objects.filter("
                )
                fixed_lines.append("                parent=obj")
                fixed_lines.append("            )")
                continue
            elif line_num == 243 and "create revision" in line:
                fixed_lines.append(
                    "                    # Would create revision here if versioning"
                )
                fixed_lines.append("                    # was implemented")
                continue
            elif line_num == 317 and "placeholder" in line:
                fixed_lines.append(
                    "                # Using placeholder tokens for now -"
                )
                fixed_lines.append(
                    "                # will be replaced with actual user info"
                )
                fixed_lines.append(
                    "                # when authentication is integrated"
                )
                continue
            elif line_num == 323 and "Return formatted" in line:
                fixed_lines.append(
                    '        """Return formatted response for revision restore'
                )
                fixed_lines.append('        success."""')
                continue

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


def process_file(filepath):
    """Process a single file to fix flake8 issues."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Fix undefined names first
        content = fix_undefined_names(content, filepath)

        # Fix specific long lines
        content = fix_specific_long_lines(content, filepath)

        # General line length fixes
        content = fix_line_length(content)

        if content != original_content:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Fixed: {filepath}")
            return True
        else:
            print(f"No changes needed: {filepath}")
            return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def main():
    """Main function to fix all flake8 issues."""
    files_to_fix = [
        "apps/accounts/tests/test_comprehensive.py",
        "apps/blog/tests/test_comprehensive.py",
        "apps/cms/tests/test_comprehensive.py",
        "apps/files/tests/test_comprehensive.py",
        "apps/cms/serializers.py",
        "apps/cms/serializers/pages.py",
    ]

    fixed_count = 0
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            if process_file(filepath):
                fixed_count += 1
        else:
            print(f"File not found: {filepath}")

    print(f"\nFixed {fixed_count} files")


if __name__ == "__main__":
    main()
