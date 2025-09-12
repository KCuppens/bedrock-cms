#!/usr/bin/env python3
"""Fix all E501 line too long issues comprehensively."""

import os

def split_long_line(line, max_length=79):
    """Split a line that's too long."""
    if len(line) <= max_length:
        return [line]

    indent = len(line) - len(line.lstrip())
    indent_str = " " * indent

    # Handle different types of lines
    if "self.assert" in line:
        # Split assertions
        if "(" in line:
            parts = line.split("(", 1)
            if len(parts) == 2:
                method = parts[0]
                args = parts[1].rstrip(")")

                # Split arguments
                if "," in args:
                    arg_list = []
                    current = ""
                    depth = 0
                    for char in args:
                        if char in "([{":
                            depth += 1
                        elif char in ")]}":
                            depth -= 1
                        current += char
                        if char == "," and depth == 0:
                            arg_list.append(current[:-1].strip())
                            current = ""
                    if current:
                        arg_list.append(current.strip())

                    result = [method + "("]
                    for i, arg in enumerate(arg_list):
                        if i < len(arg_list) - 1:
                            result.append(indent_str + "    " + arg + ",")
                        else:
                            result.append(indent_str + "    " + arg)
                    result.append(indent_str + ")")
                    return result

    elif (
        ".objects.create(" in line
        or ".objects.filter(" in line
        or ".objects.get(" in line
    ):
        # Split Django ORM calls
        if "(" in line:
            parts = line.split("(", 1)
            if len(parts) == 2:
                method = parts[0]
                args = parts[1].rstrip(")")

                if "," in args:
                    arg_list = []
                    current = ""
                    depth = 0
                    for char in args:
                        if char in "([{":
                            depth += 1
                        elif char in ")]}":
                            depth -= 1
                        current += char
                        if char == "," and depth == 0:
                            arg_list.append(current[:-1].strip())
                            current = ""
                    if current:
                        arg_list.append(current.strip())

                    result = [method + "("]
                    for i, arg in enumerate(arg_list):
                        if i < len(arg_list) - 1:
                            result.append(indent_str + "    " + arg + ",")
                        else:
                            result.append(indent_str + "    " + arg)
                    result.append(indent_str + ")")
                    return result

    elif "response = self.client." in line:
        # Split API client calls
        if "(" in line:
            parts = line.split("(", 1)
            if len(parts) == 2:
                method = parts[0]
                args = parts[1].rstrip(")")

                if "," in args:
                    arg_list = []
                    current = ""
                    depth = 0
                    for char in args:
                        if char in "([{":
                            depth += 1
                        elif char in ")]}":
                            depth -= 1
                        current += char
                        if char == "," and depth == 0:
                            arg_list.append(current[:-1].strip())
                            current = ""
                    if current:
                        arg_list.append(current.strip())

                    result = [method + "("]
                    for i, arg in enumerate(arg_list):
                        if i < len(arg_list) - 1:
                            result.append(indent_str + "    " + arg + ",")
                        else:
                            result.append(indent_str + "    " + arg)
                    result.append(indent_str + ")")
                    return result

    elif "= User.objects.create" in line or "= Group.objects.create" in line:
        # Split model creation with assignment
        if "=" in line and "(" in line:
            assignment_parts = line.split("=", 1)
            var_part = assignment_parts[0]
            create_part = assignment_parts[1].strip()

            if "(" in create_part:
                parts = create_part.split("(", 1)
                if len(parts) == 2:
                    method = parts[0]
                    args = parts[1].rstrip(")")

                    if "," in args:
                        arg_list = []
                        current = ""
                        depth = 0
                        for char in args:
                            if char in "([{":
                                depth += 1
                            elif char in ")]}":
                                depth -= 1
                            current += char
                            if char == "," and depth == 0:
                                arg_list.append(current[:-1].strip())
                                current = ""
                        if current:
                            arg_list.append(current.strip())

                        result = [var_part + "= " + method + "("]
                        for i, arg in enumerate(arg_list):
                            if i < len(arg_list) - 1:
                                result.append(indent_str + "    " + arg + ",")
                            else:
                                result.append(indent_str + "    " + arg)
                        result.append(indent_str + ")")
                        return result

    # Handle string literals that are too long
    if '"' in line or "'" in line:
        # Find string boundaries
        in_string = False
        string_char = None
        string_start = -1

        for i, char in enumerate(line):
            if not in_string and char in "\"'":
                in_string = True
                string_char = char
                string_start = i
            elif in_string and char == string_char and (i == 0 or line[i - 1] != "\\"):
                # Found end of string
                if i - string_start > 60:  # Long string
                    before = line[:string_start]
                    string_content = line[string_start + 1 : i]
                    after = line[i + 1 :]

                    if len(string_content) > 60:
                        # Split the string
                        mid = len(string_content) // 2
                        # Find a good split point (space, comma, etc.)
                        for offset in range(min(20, mid)):
                            if string_content[mid + offset] in " ,;:":
                                mid = mid + offset + 1

                            if string_content[mid - offset] in " ,;:":
                                mid = mid - offset + 1

                        part1 = string_content[:mid]
                        part2 = string_content[mid:]

                        return [
                            before + string_char + part1 + string_char,
                            indent_str
                            + "    "
                            + string_char
                            + part2
                            + string_char
                            + after,
                        ]
                in_string = False

    # Generic split at comma or operator
    if "," in line:
        # Find the best comma to split at
        depth = 0
        for i, char in enumerate(line):
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "," and depth == 0 and i > 40 and i < len(line) - 20:
                return [line[: i + 1], indent_str + "    " + line[i + 1 :].strip()]

    # If no good split point found, just break at 79 chars
    return [line[:79], indent_str + "    " + line[79:].strip()]

def fix_file_line_lengths(filepath):
    """Fix all E501 line length issues in a file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        fixed_lines = []
        changed = False

        for line in lines:
            # Preserve newline
            line_content = line.rstrip("\n")

            if len(line_content) > 79:
                # Split the long line
                split_lines = split_long_line(line_content)
                for split_line in split_lines:
                    fixed_lines.append(split_line + "\n")
                changed = True
            else:
                fixed_lines.append(line)

        if changed:
            with open(filepath, "w", encoding="utf-8") as f:
                f.writelines(fixed_lines)
            return True
        return False

    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main function to fix all line length issues."""
    files_to_fix = [
        "apps/accounts/tests/test_comprehensive.py",
        "apps/blog/tests/test_comprehensive.py",
        "apps/cms/tests/test_comprehensive.py",
        "apps/files/tests/test_comprehensive.py",
        "apps/i18n/translation.py",
        "apps/i18n/views.py",
        "tests/factories/__init__.py",
        "tests/factories/accounts.py",
        "apps/cms/serializers.py",
        "apps/cms/serializers/pages.py",
    ]

    fixed_count = 0
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            print(f"Processing: {filepath}")
            if fix_file_line_lengths(filepath):
                fixed_count += 1
                print(f"  Fixed: {filepath}")
            else:
                print(f"  No changes: {filepath}")
        else:
            print(f"File not found: {filepath}")

    print(f"\nFixed {fixed_count} files")

if __name__ == "__main__":
    main()
