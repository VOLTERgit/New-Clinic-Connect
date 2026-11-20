@echo off
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*START_CLINIC*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*server.py*' -or $_.Name -eq 'ClinicConnect.exe' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Clinic Connect stopped.
pause
