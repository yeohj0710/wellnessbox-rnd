@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$files=@('kpi_replacement_review.csv','reviewer_identity_selection.json'); $missing=@($files|Where-Object{-not(Test-Path -LiteralPath $_)}); if($missing){Write-Error ('Missing: '+($missing -join ', '));exit 2}; Compress-Archive -LiteralPath $files -DestinationPath 'kpi_replacement_final_review_completed.zip' -Force"
if errorlevel 1 exit /b 1
echo kpi_replacement_final_review_completed.zip
