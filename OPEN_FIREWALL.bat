@echo off
net session >nul 2>&1 || (echo Right-click this file and choose "Run as administrator" & pause & exit /b)
netsh advfirewall firewall delete rule name="Clinic Connect" >nul 2>&1
netsh advfirewall firewall add rule name="Clinic Connect" dir=in action=allow protocol=TCP localport=8765 profile=any
echo Firewall opened for port 8765. Other PCs on the WiFi can now connect.
pause
