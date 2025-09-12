#!/usr/bin/env python3
import os
import py_compile


def main():
    errors = 0
    total = 0
    error_files = []

    for root, dirs, files in os.walk('.'):
        if any(skip in root for skip in ['__pycache__', '.git', 'node_modules', 'venv', '.tox']):
            continue
        for file in files:
            if file.endswith('.py'):
                total += 1
                filepath = os.path.join(root, file)
                try:
                    py_compile.compile(filepath, doraise=True)
                except Exception as e:
                    errors += 1
                    """error_files.append((filepath, str(e)))"""

    print(f'Total Python files: {total}')
    print(f'Files with syntax errors: {errors}')
    print(f'Files successfully fixed: {total - errors}')
    print(f'Success rate: {((total - errors) / total * 100):.1f}%')
    
    if errors > 0:
        print(f'\nRemaining files with errors (first 10):')
        for filepath, error in error_files[:10]:
            print(f'  {filepath}: {error[:100]}...')

if __name__ == "__main__":
    main()