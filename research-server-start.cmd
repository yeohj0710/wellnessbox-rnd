@echo off
cd /d "%~dp0"
title WellnessBox Local Research Server
python scripts\run_local_research_session.py --verify
if errorlevel 1 (
  echo.
  echo The local research server could not start. Check etc\local_research_runtime logs.
  pause
)
