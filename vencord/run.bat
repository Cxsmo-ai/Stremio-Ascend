@echo off
setlocal enabledelayedexpansion

:: ==========================================
:: 1. GITHUB PLUGIN URLS
:: ==========================================

:: -- Original Hacker Setup --
set "plugins[0]=https://github.com/Juiceroyals/Vencord-Edit-Delete-Messages-Locally.git"
set "plugins[1]=https://github.com/Syncxv/vc-message-logger-enhanced.git"
set "plugins[2]=https://github.com/D3SOX/vc-voiceChatUtilities.git"
set "plugins[3]=https://github.com/D3SOX/vc-silentTypingEnhanced.git"
set "plugins[4]=https://github.com/itzinject/OpSec-Vencord.git"
set "plugins[5]=https://github.com/eightcon/FakeVoiceOptions.git"
set "plugins[6]=https://github.com/zaher-neon/vc-questComplete.git"
set "plugins[7]=https://github.com/ScattrdBlade/bigFileUpload.git"
set "plugins[8]=https://github.com/Sqaaakoi/vc-junkCleanup.git"
set "plugins[9]=https://github.com/TetraSsky/CleanCord.git"
set "plugins[10]=https://github.com/Talya1412/completeDiscordQuest.git"
set "plugins[11]=https://github.com/D3SOX/vc-followUser.git"
set "plugins[12]=https://github.com/isamain/Auto-voice-disconnecter.git"
set "plugins[13]=https://github.com/ih8js-git/messageScheduler.git"
set "plugins[14]=https://github.com/0x6d6179/vencord-antirickroll.git"
set "plugins[15]=https://github.com/D3SOX/vc-ignoreTerms.git"
set "plugins[16]=https://github.com/ScattrdBlade/customSounds.git"
set "plugins[17]=https://github.com/D3SOX/vc-betterActivities.git"

:: ==========================================
:: 2. SETUP DIRECTORIES & CLONE PATCHSET
:: ==========================================
set "BASE_DIR=%~dp0"
if "%BASE_DIR:~-1%"=="\" set "BASE_DIR=%BASE_DIR:~0,-1%"

set "REPO_URL=https://github.com/Davilarek/BetterVencordPatchset.git"
set "REPO_DIR=%BASE_DIR%\BetterVencordPatchset"

echo ==================================================
echo  BetterVencord Patchset (Equicord) Auto-Installer
echo ==================================================
echo.

echo [1/5] Cloning Core Repository and Submodules...
if not exist "%REPO_DIR%\.git" (
    echo Source code not found. Cloning repository...
    cd /d "%BASE_DIR%"
    git clone --recurse-submodules "%REPO_URL%"
) else (
    echo Source code found. Pulling latest updates...
    cd /d "%REPO_DIR%"
    git pull
    git submodule update --init --recursive
)

cd /d "%REPO_DIR%" || (
    echo [ERROR] Failed to enter repository directory!
    pause
    exit /b
)

echo.
echo [2/5] Running BetterVencord Patchset Build Pipeline...
call pnpm install || exit /b
call pnpm dlx tsx scripts/build.ts --equicord || exit /b

echo.
echo [3/5] Syncing User Plugins into Equicord...
set "PLUGIN_DIR=%REPO_DIR%\dist_production\Equicord\src\userplugins"
if not exist "%PLUGIN_DIR%" (
    mkdir "%PLUGIN_DIR%"
)

cd /d "%PLUGIN_DIR%" || (
    echo [ERROR] Failed to open the userplugins directory!
    pause
    exit /b
)

set i=0
:loop
if not defined plugins[%i%] goto :endloop

set "plugin_url=!plugins[%i%]!"
set "temp_url=!plugin_url:/=\!"
for %%A in ("!temp_url!") do set "folder_name=%%~nxA"
set "folder_name=!folder_name:.git=!"

echo.
echo -- Processing Plugin: !folder_name! --

if exist "!folder_name!\.git" (
    echo Updating !folder_name!...
    cd "!folder_name!"
    git pull
    cd ..
) else (
    echo Cloning !folder_name!...
    git clone "!plugin_url!" "!folder_name!"
)

set /a i+=1
goto :loop

:endloop

echo.
echo [4/5] Compiling Equicord with Custom Plugins...
:: Navigate into the generated Equicord folder to build the final plugin bundle
cd /d "%REPO_DIR%\dist_production\Equicord" || (
    echo [ERROR] Failed to enter the compiled Equicord directory!
    pause
    exit /b
)
call pnpm install || exit /b
call pnpm build || exit /b

echo.
echo [5/5] Injecting into Discord Canary...
:: Use the CLI directly with arguments to avoid interactive prompt
call pnpm inject --location "C:\Users\picky\AppData\Local\DiscordCanary"

echo.
echo ==================================================
echo All Done! Restart Discord Canary (Ctrl+R) to load.
echo ==================================================
pause
