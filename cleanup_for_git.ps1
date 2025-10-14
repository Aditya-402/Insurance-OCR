# Cleanup script for preparing project for GitHub
# Run this script to remove all temporary and generated files

Write-Host "Insurance OCR - GitHub Cleanup Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

# List of files/folders to remove
$itemsToRemove = @(
    "Insurance_ocr.zip",
    "conversations.zip",
    "conversations (2).zip",
    "Book2.xlsx",
    "example_req.txt",
    "docu_template.docx",
    "Reviewing Project Files for Analysis.docx",
    "claim_1234_report.html",
    "claim_674_report.html",
    "business_logic_flow.dot",
    "rule_flow.dot",
    "New folder",
    "conversations",
    "temp_db_updates",
    "web_ui"
)

# Count items
$totalItems = 0
$existingItems = @()

Write-Host "Checking items to remove..." -ForegroundColor Yellow
Write-Host ""

foreach ($item in $itemsToRemove) {
    $fullPath = Join-Path $projectRoot $item
    if (Test-Path $fullPath) {
        $existingItems += $item
        $totalItems++
        Write-Host "  [FOUND] $item" -ForegroundColor Red
    } else {
        Write-Host "  [SKIP]  $item (not found)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Found $totalItems items to remove" -ForegroundColor Yellow
Write-Host ""

if ($totalItems -eq 0) {
    Write-Host "Nothing to clean up! Project is ready for Git." -ForegroundColor Green
    exit 0
}

# Ask for confirmation
$confirmation = Read-Host "Do you want to remove these items? (y/n)"

if ($confirmation -ne 'y') {
    Write-Host "Cleanup cancelled." -ForegroundColor Yellow
    exit 0
}

# Remove items
Write-Host ""
Write-Host "Removing items..." -ForegroundColor Yellow

$removed = 0
$failed = 0

foreach ($item in $existingItems) {
    $fullPath = Join-Path $projectRoot $item
    try {
        Remove-Item -Path $fullPath -Recurse -Force -ErrorAction Stop
        Write-Host "  [OK] Removed: $item" -ForegroundColor Green
        $removed++
    } catch {
        Write-Host "  [FAIL] Could not remove: $item" -ForegroundColor Red
        $failed++
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Cleanup Summary:" -ForegroundColor Cyan
Write-Host "  Removed: $removed items" -ForegroundColor Green
Write-Host "  Failed:  $failed items" -ForegroundColor Red
Write-Host ""

if ($failed -eq 0) {
    Write-Host "[SUCCESS] Project is ready for GitHub!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Review changes: git status" -ForegroundColor White
    Write-Host "  2. Add files: git add ." -ForegroundColor White
    Write-Host "  3. Commit: git commit -m 'Initial commit'" -ForegroundColor White
    Write-Host "  4. Push: git push origin main" -ForegroundColor White
} else {
    Write-Host "[WARNING] Some items could not be removed." -ForegroundColor Yellow
}

Write-Host ""
