@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -Command "$files=@('reviewer_identity_selection.json','kpi1_response.json','kpi4_response.json','kpi5_response.json'); $missing=$files|Where-Object{-not(Test-Path -LiteralPath $_)}; if($missing){Write-Error ('Missing: '+($missing -join ', ')); exit 2}; Compress-Archive -LiteralPath $files -DestinationPath 'kpi_replacement_completed.zip' -Force"
if errorlevel 1 exit /b 1
echo kpi_replacement_completed.zip
