@echo off
cd /d "%~dp0"
python scripts\stop_local_research_session.py
ping 127.0.0.1 -n 3 >nul
