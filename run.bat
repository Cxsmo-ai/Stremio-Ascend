@echo off
setlocal
title Ascend Media RPC v2.0 - Launcher

echo ==================================================
echo         Ascend Media RPC v2.0 (Public)
echo ==================================================

:: Check if configuration exists, if not, offer to create from example
if not exist config.json (
    if exist config.example.json (
        echo [INFO] No config.json found. Creating from example...
        copy config.example.json config.json
    )
)

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ to run Ascend Media RPC.
    pause
    exit /b
)

:: Check if dependencies are installed (simple check for customtkinter)
python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Dependencies missing. Monitoring first-run setup...
    call install.bat
)

echo [LAUNCH] Starting Ascend Media RPC...
python start_gui.py

if %errorlevel% neq 0 (
    echo.
    echo [CRASH] Application exited with error code %errorlevel%.
    echo Check stremio_debug.log for details.
    pause
)
