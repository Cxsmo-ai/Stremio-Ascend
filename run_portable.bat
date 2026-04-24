@echo off
cd /d "%~dp0"
echo Starting Stremio RPC (Portable Mode)...
"python\python.exe" start_gui.py
if %errorlevel% neq 0 (
    echo.
    echo Application crashed.
    pause
)
