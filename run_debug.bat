@echo off
cd /d "%~dp0"
echo Starting Stremio RPC in DEBUG MODE...
echo Logs will be saved to strmio_rpc.log
python start_gui.py
if %errorlevel% neq 0 (
    echo.
    echo CRITICAL ERROR: Application Crashed!
    echo Check the error message above or the log file.
    pause
)
pause
