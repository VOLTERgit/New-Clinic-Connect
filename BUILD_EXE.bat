@echo off
cd /d "%~dp0"
pip install pyinstaller
pyinstaller --onefile --name ClinicConnect --add-data "static;static" server.py
copy /y dist\ClinicConnect.exe . >nul
echo.
echo Built ClinicConnect.exe - START_CLINIC.bat will use it automatically.
pause
