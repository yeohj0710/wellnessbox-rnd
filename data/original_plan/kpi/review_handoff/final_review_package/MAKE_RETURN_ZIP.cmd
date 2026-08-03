@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$files=@('kpi1_review.csv','kpi3_review.csv','kpi4_review.csv','kpi5_review.csv','reviewer_details.json','seal_disposal_review.json'); $missing=@($files | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) }); if ($missing.Count -gt 0) { Write-Host ('Missing: ' + ($missing -join ', ')); exit 2 }; Compress-Archive -LiteralPath $files -DestinationPath 'kpi_completed_review.zip' -Force"
if errorlevel 1 (
  echo Failed to create kpi_completed_review.zip
  exit /b 1
)
echo Created: kpi_completed_review.zip
