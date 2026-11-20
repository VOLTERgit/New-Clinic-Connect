@echo off
cd /d "%~dp0"
for /f "delims=" %%i in ('where pythonw') do set PW=%%i
if not defined PW (echo pythonw not found - install Python from python.org with Add to PATH & pause & exit /b)
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:APPDATA+'\Microsoft\Windows\Start Menu\Programs\Startup\ClinicAlerts.lnk');$s.TargetPath='%PW%';$s.Arguments='\"%~dp0popup_client.py\"';$s.WorkingDirectory='%~dp0';$s.Save()"
echo Done! Desktop alerts will start by themselves when this PC starts.
echo Starting them now (first time it asks for server address, name and password)...
start "" pythonw popup_client.py
pause
