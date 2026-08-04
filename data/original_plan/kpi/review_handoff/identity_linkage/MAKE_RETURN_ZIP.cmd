@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath 'kpi_original_review_identity_linkage.json' -DestinationPath 'kpi_original_review_identity_linkage_completed.zip' -Force"
