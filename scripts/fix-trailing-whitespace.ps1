# Fix trailing whitespace in all source files
Write-Host "🧹 Fixing trailing whitespace in source files..." -ForegroundColor Cyan

$fileTypes = @("*.py", "*.js", "*.ts", "*.tsx", "*.jsx", "*.css", "*.scss", "*.html", "*.md", "*.yaml", "*.yml", "*.json")
$directories = @("backend", "frontend")
$modifiedFiles = @()

foreach ($dir in $directories) {
    if (Test-Path $dir) {
        foreach ($fileType in $fileTypes) {
            $files = Get-ChildItem -Path $dir -Recurse -Include $fileType -File
            foreach ($file in $files) {
                $content = Get-Content $file.FullName -Raw
                if ($content -match '\s+$') {
                    $newContent = $content -replace '\s+$', ''
                    Set-Content $file.FullName $newContent -NoNewline
                    $modifiedFiles += $file.Name
                    Write-Host "Fixed: $($file.Name)" -ForegroundColor Yellow
                }
            }
        }
    }
}

Write-Host "✅ Trailing whitespace fixed!" -ForegroundColor Green

if ($modifiedFiles.Count -gt 0) {
    Write-Host "📝 Modified $($modifiedFiles.Count) files" -ForegroundColor Cyan
    Write-Host "💡 Run 'git add .' and 'git commit' to save the changes." -ForegroundColor Blue
} else {
    Write-Host "✨ No files needed modification." -ForegroundColor Green
}
