@echo off
title PTC Message & Security Discord Bot
echo ========================================================
echo   Prop Traders Community (PTC) - Discord Bot Runner
echo ========================================================
echo.

IF NOT EXIST ".env" (
    echo [WARNING] .env file not found!
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo Please edit .env with your DISCORD_TOKEN before starting.
    notepad .env
    pause
    exit /b
)

echo Checking dependencies...
python -m pip install -r requirements.txt --quiet

echo.
echo Starting PTC Message Bot...
python bot.py
pause

