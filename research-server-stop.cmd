@echo off
cd /d "%~dp0"
python scripts\stop_local_research_session.py
timeout /t 2 /nobreak >nul
