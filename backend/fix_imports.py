#!/usr/bin/env python3
import glob
import os
import re


def fix_malformed_imports(filepath):
    """Fix common malformed import patterns"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_content = content

    # Pattern 1: Fix broken from import with malformed strings and keywords
    # from apps.module.file import (  # comment
    #     "STRING",
    #     SomeClass,
    #     """,
    #     broken,
    #     from,
    #     import,
    # )
    pattern1 = re.compile(
        r"from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import\s+\(\s*#[^\n]*\n"
        r'((?:\s*(?:"[^"]*"|\'[^\']*\'|[a-zA-Z_][a-zA-Z0-9_.]*|[,-]|from|import|and|or|the|to|for|with|in|of|a|an|is|are|be|have|has|do|does|will|would|could|should|can|may|might|must|shall|this|that|these|those|there|here|where|when|what|who|which|how|why|if|then|else|elif|while|try|except|finally|class|def|return|yield|raise|assert|pass|break|continue|global|nonlocal|lambda|True|False|None)\s*,?\s*\n)*)'
        r"\s*\)",
        re.MULTILINE | re.DOTALL,
    )

    def replace_import(match):
        module = match.group(1)
        import_list = match.group(2)

        # Extract valid Python identifiers (not strings or keywords)
        valid_imports = []
        for line in import_list.split("\n"):
            line = line.strip().rstrip(",")
            if (
                line
                and not line.startswith('"')
                and not line.startswith("'")
                and line.isidentifier()
            ):
                valid_imports.append(line)

        if valid_imports:
            formatted_imports = ",\n    ".join(valid_imports)
            return f"from {module} import (\n    {formatted_imports},\n)"
        else:
            return f"# from {module} import ()"

    content = pattern1.sub(replace_import, content)

    # Pattern 2: Fix standalone broken import lists
    pattern2 = re.compile(r"^(\s+)([a-zA-Z_][a-zA-Z0-9_.]*)\.,\s*$", re.MULTILINE)
    content = pattern2.sub(r"\1# \2", content)

    # Pattern 3: Remove lines with just keywords
    keywords_pattern = re.compile(
        r"^\s*(from|import|and|or|the|to|for|with|in|of|a|an|is|are|be|have|has|do|does|will|would|could|should|can|may|might|must|shall|this|that|these|those|there|here|where|when|what|who|which|how|why|if|then|else|elif|while|try|except|finally|class|def|return|yield|raise|assert|pass|break|continue|global|nonlocal|lambda|True|False|None)\s*,?\s*$",
        re.MULTILINE,
    )
    content = keywords_pattern.sub("", content)

    # Pattern 4: Fix empty import parentheses blocks
    content = re.sub(
        r"from\s+[a-zA-Z_][a-zA-Z0-9_.]*\s+import\s+\(\s*\n\s*\)", "", content
    )

    # Pattern 5: Remove lines with just commas or dashes
    content = re.sub(r"^\s*[-,]\s*,?\s*$", "", content, flags=re.MULTILINE)

    # Pattern 6: Remove triple quotes on their own lines
    content = re.sub(r'^\s*""",?\s*$', "", content, flags=re.MULTILINE)

    # Clean up multiple empty lines
    content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)

    if content != original_content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False


def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    fixed_files = []

    # Find Python files to fix
    for root, dirs, files in os.walk(backend_dir):
        if any(
            skip in root for skip in ["__pycache__", ".git", "node_modules", "venv"]
        ):
            continue

        for file in files:
            if file.endswith(".py") and file != "fix_imports.py":
                filepath = os.path.join(root, file)
                if fix_malformed_imports(filepath):
                    rel_path = os.path.relpath(filepath, backend_dir)
                    """fixed_files.append(rel_path)"""

    print(f"Fixed {len(fixed_files)} files:")
    for file in fixed_files:
        print(f"  {file}")


if __name__ == "__main__":
    main()
