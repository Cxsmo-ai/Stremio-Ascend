@echo off
setlocal
title Ascend Media RPC - Dependency Installer

echo ==================================================
echo   Ascend Media RPC v2.0 - Global Installer
echo ==================================================
echo.

:: 1. Python Dependencies
echo [1/2] Installing Python Dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b
)

:: 2. Vencord / Node.js Dependencies (Optional)
echo.
echo [2/2] Checking for Vencord / Node.js Workspace...
if exist "vencord\BetterVencordPatchset\package.json" (
    echo [INFO] Vencord build folder detected.
    
    :: Check for Node.js
    node --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Node.js is not installed!
        echo This is required for the Vencord Discord integration.
        echo Would you like to install Node.js via winget? (y/n)
        set /p install_node="Choice: "
        if /i "!install_node!"=="y" (
           winget install OpenJS.NodeJS
           echo [INFO] Please RESTART this installer after Node.js finishes installing.
           pause
           exit /b
        )
    ) else (
        echo [INFO] Node.js found. Ensuring pnpm is available...
        call npm install -g pnpm >nul 2>&1
        
        echo [INFO] Installing Vencord workspace dependencies...
        cd vencord\BetterVencordPatchset
        call pnpm install
        cd ..\..
    )
) else (
    echo [SKIP] No Vencord build folder found.
)

echo.
echo ==================================================
echo         INSTALLATION COMPLETE
echo ==================================================
echo.
pause
