@echo off
cd /d "%~dp0"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:APPDATA+'\Microsoft\Windows\Start Menu\Programs\Startup\ClinicConnect.lnk');$s.TargetPath='wscript.exe';$s.Arguments='\"%~dp0run_hidden.vbs\"';$s.WorkingDirectory='%~dp0';$s.Save()"
echo.
echo Done! Clinic Connect will now start silently (hidden) every time this PC starts.
echo To start it right now, double-click run_hidden.vbs
pause
