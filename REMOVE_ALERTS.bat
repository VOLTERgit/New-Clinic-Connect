@echo off
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ClinicAlerts.lnk" 2>nul
del "%~dp0popup_config.json" 2>nul
echo Desktop alerts autostart removed and saved login cleared.
pause
