"""Helper used by `python server.py install` etc. - replaces the .bat files (Windows Smart App Control blocks downloaded .bat files)."""
import os, sys, subprocess

def _ps(cmd): subprocess.run(["powershell", "-NoProfile", "-Command", cmd])
def _pythonw(): return os.path.join(os.path.dirname(sys.executable), "pythonw.exe")

def autostart(name, script, remove=False):
    lnk = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup", name + ".lnk")
    if remove:
        subprocess.run(["schtasks", "/delete", "/tn", name, "/f"], capture_output=True)
        try: os.remove(lnk); print("Autostart removed.")
        except OSError: print("Autostart was not installed.")
        return
    exe = script.lower().endswith(".exe")  # works for a built .exe too (no Python needed)
    _ps(f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');$s.TargetPath='{script if exe else _pythonw()}';"
        + ("" if exe else f"$s.Arguments=[char]34+'{script}'+[char]34;") + f"$s.WorkingDirectory='{os.path.dirname(script)}';$s.Save()")
    # watchdog: if someone closes/kills it, Windows starts it again within 5 minutes (a 2nd copy exits by itself)
    tr = f'"{script}"' if exe else f'"{_pythonw()}" "{script}"'
    subprocess.run(["schtasks", "/create", "/tn", name, "/tr", tr, "/sc", "minute", "/mo", "5", "/f"], capture_output=True)
    print("Autostart installed - it will start by itself when Windows starts.")

def hidden(script):  # run in background with no window
    subprocess.Popen([script] if script.lower().endswith(".exe") else [_pythonw(), script], cwd=os.path.dirname(script), creationflags=0x00000008 | 0x00000200)
    print("Started in the background.")

def stop(name):
    _ps("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*" + name + "*' -and $_.ProcessId -ne " + str(os.getpid()) + " } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }")
    print("Stopped.")

def firewall(port):  # asks Windows for administrator permission (click Yes)
    import ctypes
    ctypes.windll.shell32.ShellExecuteW(None, "runas", "netsh", f'advfirewall firewall add rule name="Clinic Connect" dir=in action=allow protocol=TCP localport={port} profile=any', None, 1)
    print("Click YES on the Windows permission box. Port opened.")
