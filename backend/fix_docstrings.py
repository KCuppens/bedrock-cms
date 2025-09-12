#!/usr/bin/env python3
import os
import re


def fix_docstring_issues(filepath):
    """Fix common docstring-related syntax errors"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: Fix unquoted docstrings at the beginning of lines
    # These often appear after imports as bare strings
    pattern1 = re.compile(
        r'^(\s*)([A-Z][A-Za-z0-9\s,\.\-\(\)]+[\.!])\s*$',
        re.MULTILINE
    )
    
    def replace_bare_docstring(match):
        indent = match.group(1)
        text = match.group(2).strip()
        # Only convert if it looks like a docstring (starts with capital, ends with punctuation)
        if len(text) > 10 and text[0].isupper() and text[-1] in '.!':
            return f'{indent}"""{text}"""'
        return match.group(0)
    
    content = pattern1.sub(replace_bare_docstring, content)
    
    # Pattern 2: Fix class/function definitions missing colons after docstrings
    pattern2 = re.compile(
        r'(class\s+\w+[^:]*?)\n\s*"""([^"]+)"""\s*\n\s*(\w+)',
        re.MULTILINE | re.DOTALL
    )
    
    def fix_class_def(match):
        class_def = match.group(1)
        docstring = match.group(2)
        next_item = match.group(3)
        
        if ':' not in class_def:
            class_def += ':'
        
        return f'{class_def}\n    """{docstring}"""\n\n    {next_item}'
    
    content = pattern2.sub(fix_class_def, content)
    
    # Pattern 3: Fix standalone string literals that should be comments
    pattern3 = re.compile(
        r'^\s*([A-Z][A-Za-z0-9\s]+)\s*$',
        re.MULTILINE
    )
    
    def replace_with_comment(match):
        text = match.group(1).strip()
        # Convert standalone phrases to comments
        if len(text.split()) > 1 and text[0].isupper():
            return f'# {text}'
        return match.group(0)
    
    # Only apply this to lines that don't look like imports or code
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Skip if it's an import, assignment, or other code construct
        if (line.strip() and 
            not line.strip().startswith('from ') and 
            not line.strip().startswith('import ') and
            not '=' in line and
            not line.strip().startswith('#') and
            not line.strip().startswith('"""') and
            not line.strip().startswith("'''") and
            not line.strip().endswith(':') and
            re.match(r'^\s*[A-Z][A-Za-z0-9\s\.,\-\(\)]+[\.!]?\s*$', line)):
            fixed_lines.append(f'# {line.strip()}')
        else:
            fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    fixed_files = []
    
    # List of files with docstring issues (from the error output)
    problem_files = [
        "fix_all_flake8_issues.py",
        "fix_f401_issues.py", 
        "apps/accounts/adapters.py",
        "apps/accounts/auth_backends.py",
        "apps/accounts/auth_views.py",
        "apps/accounts/coverage_booster.py",
        "apps/accounts/custom_adapter.py",
        "apps/accounts/middleware.py",
        "apps/analytics/aggregation.py",
        "apps/analytics/permissions.py",
    ]
    
    for file_path in problem_files:
        full_path = os.path.join(backend_dir, file_path.replace('/', os.sep))
        if os.path.exists(full_path):
            if fix_docstring_issues(full_path):
                fixed_files.append(file_path)
    
    print(f"Fixed docstring issues in {len(fixed_files)} files:")
    for file in fixed_files:
        print(f"  {file}")

if __name__ == "__main__":
    main()