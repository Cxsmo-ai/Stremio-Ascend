@echo off
cd /d "%~dp0"
echo Starting IntroDB Login Browser...
"python\python.exe" "src\intro_api\auth_browser.py"
pause
