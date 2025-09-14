#!/bin/bash
# Fix trailing whitespace in all source files

echo "🧹 Fixing trailing whitespace in source files..."

# Find and fix trailing whitespace in common source file types
find backend/ frontend/ -type f \( \
    -name "*.py" -o \
    -name "*.js" -o \
    -name "*.ts" -o \
    -name "*.tsx" -o \
    -name "*.jsx" -o \
    -name "*.css" -o \
    -name "*.scss" -o \
    -name "*.html" -o \
    -name "*.md" -o \
    -name "*.yaml" -o \
    -name "*.yml" -o \
    -name "*.json" \
\) -exec sed -i 's/[[:space:]]*$//' {} \;

echo "✅ Trailing whitespace fixed!"

# Check if any files were modified
modified_files=$(git diff --name-only)
if [ -n "$modified_files" ]; then
    echo "📝 Modified files:"
    echo "$modified_files"
    echo ""
    echo "💡 Run 'git add .' and 'git commit' to save the changes."
else
    echo "✨ No files needed modification."
fi