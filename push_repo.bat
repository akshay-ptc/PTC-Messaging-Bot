@echo off
title Push to GitHub - PTC Messaging Bot
echo ========================================================
echo   Pushing PTC Messaging Bot to GitHub
echo   Repository: https://github.com/akshay-ptc/PTC-Messaging-Bot
echo ========================================================
echo.

set GIT_PATH="C:\Users\Dell\AppData\Local\GitHubDesktop\app-3.5.6\resources\app\git\cmd\git.exe"

IF NOT EXIST %GIT_PATH% (
    set GIT_PATH=git
)

echo [1/3] Adding all files to commit...
%GIT_PATH% add .

echo [2/3] Checking git status...
%GIT_PATH% status --short

echo.
echo [3/3] Attempting push to origin main...
%GIT_PATH% push -u origin main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================================
    echo [NOTE] If you saw "Permission denied to AkshayBakale":
    echo Option 1: Go to https://github.com/akshay-ptc/PTC-Messaging-Bot/settings/access
    echo           Click "Add people" and invite "AkshayBakale" as Collaborator.
    echo.
    echo Option 2: Open GitHub Desktop:
    echo           File -^> Add Local Repository -^> D:\Akshay\Antigravity AI\PTC Message Bot
    echo           Make sure you are signed in as akshay-ptc, then click "Push origin".
    echo ========================================================
)

echo.
pause

