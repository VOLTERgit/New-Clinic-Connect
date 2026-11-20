# Clinic Connect  (WhatsApp-style clinic alerts)

Needs only Python 3.8+ (python.org, tick "Add Python to PATH"). **No .bat files needed** - Windows Smart App Control blocks downloaded .bat files, but Python files work.

## How to run commands
Open the ClinicConnect folder > click the address bar > type `cmd` > Enter. Then type:

## SERVER PC
| Command | What it does |
|---|---|
| `python server.py` | Start now (shows the address to open, keep window open) |
| `python server.py firewall` | Let other PCs connect (click Yes) - once |
| `python server.py install` | Start hidden now + automatically every time Windows starts |
| `python server.py stop` / `uninstall` | Stop / remove autostart |

## EVERY CLINIC PC (pop-up over any program, even if Chrome is minimized)
| Command | What it does |
|---|---|
| `python popup_client.py` | First time: enter server address, your name, password |
| `python popup_client.py install` | Start hidden + automatically with Windows |
| `python popup_client.py uninstall` | Remove (also delete popup_config.json to change login) |

Then use the browser at the server address for chats, status and admin.
Tip: reserve a fixed IP for the server PC in the router.

## BEST WAY for staff PCs (same popup as the server PC, works even if Chrome is closed, no Python on staff PCs)
1. On the SERVER PC, in the ClinicConnect folder (cmd): `python popup_client.py build`  (takes ~2 minutes, once)
2. Copy the new folder `StaffPC` to a USB stick, then to each staff PC.
3. On the staff PC double-click `ClinicAlerts.exe` > Load names > your name > password > Save & start. Done:
   it starts with Windows by itself and restarts if closed. If Windows blocks the .exe (Smart App Control) see the guide.

## Other ways to add a new PC (Python is needed ONLY on the server PC)
1. **Zero install (easiest):** on the new PC just open the server address in Chrome/Edge. On the login page tap
   "Pop-ups when Chrome is minimized" and follow the 4 steps (1 minute, once). Windows then shows the alert at the
   bottom-right even when Chrome is minimized. Tip: Chrome menu > Save and share > Create shortcut > Open as window.
2. **One small .exe for all PCs:** on ONE PC with Python run `pip install pyinstaller` then
   `pyinstaller --onefile --noconsole popup_client.py`. Copy `dist\popup_client.exe` by USB to other PCs, double-click it
   (asks server address/name/password once), then `popup_client.exe install` for autostart. No Python needed there.
   (If Smart App Control blocks the .exe, use way 1.)
3. Python on every PC (what we did before) - works but slowest.

## If staff close it / PC was off
`install` also adds a Windows watchdog: if the alert program is closed, it restarts within 5 minutes (a second copy quits by itself).
Messages are kept on the server, so a PC that was off shows them the moment it starts. The sender sees only ✓ (not ✓✓) until
the PC receives it, and after 2 minutes without "Understood" the admin gets a warning.

## Tray icon
ClinicAlerts shows an icon by the clock (green = connected, red = offline). If hidden, click the ^ arrow and drag it onto the taskbar.
Right-click: Open Clinic Connect, Send test alert, Quit. (Without the .exe: `pip install pystray pillow`.)

## Logins
Admin / admin123 (change it). Others: Anchal, Diwaker, Krishna, Mansi, Dhaval, Vaibhav.

## Files
`server.py`, `static/` (web app), `popup_client.py`, `tools.py`, `config.json` (port), `data/` (database + daily backups).
The .bat files are optional shortcuts - ignore them if Windows blocks them.

## New in this version
- Delete a message within 1 minute (trash icon next to your message); after that it stays.
- Volume slider + Test in the web app; in the tray icon: Volume (Mute/Low/Medium/High/Maximum).
- Do Not Disturb (switch in the web app, or tray menu): no pop-ups for you, others see you are away. Urgent still comes through.
- No reply after 2 minutes: the receiver is re-alerted louder and the SENDER is told. Admin is never escalated or warned.
- Pop-ups (browser and desktop) have quick replies + a text reply box.
