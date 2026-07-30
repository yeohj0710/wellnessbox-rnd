@echo off
setlocal
cd /d "%~dp0"
title 연구 마감 안내 실행기

if exist ".venv-interim\Scripts\python.exe" (
  set "WB_PY=.venv-interim\Scripts\python.exe"
) else (
  set "WB_PY=python"
)

"%WB_PY%" scripts\run_research_completion_wizard.py %*
set "WB_RC=%ERRORLEVEL%"

echo.
echo 창을 닫으려면 아무 키나 누르세요.
pause >nul
exit /b %WB_RC%
