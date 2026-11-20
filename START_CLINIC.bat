@echo off
title Clinic Connect Server
cd /d "%~dp0"
:loop
if exist ClinicConnect.exe (ClinicConnect.exe) else (
  where python >nul 2>nul || (echo Python not found. Install it from python.org ^(tick "Add to PATH"^) & pause & exit /b)
  python server.py
)
echo.
echo Server stopped. Restarting in 3 seconds... (close this window to quit)
timeout /t 3 >nul
goto loop
