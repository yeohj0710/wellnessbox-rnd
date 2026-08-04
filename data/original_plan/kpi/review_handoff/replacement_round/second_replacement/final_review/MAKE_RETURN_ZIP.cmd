@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath 'kpi1_second_replacement_review.csv','reviewer_identity_selection.json' -DestinationPath 'kpi1_second_replacement_final_review_completed.zip' -Force"
