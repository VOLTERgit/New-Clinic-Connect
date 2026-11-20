"""Clinic Connect DESKTOP ALERTS - full-screen pop-up on top of ANY program, even if the browser is minimized.
Run on every clinic PC:  pythonw popup_client.py   (first run asks for server address, name, password)"""
import tkinter as tk
from tkinter import ttk
import json, os, sys, threading, queue, time, random, urllib.request, webbrowser, wave, struct, math, io
try: import winsound
except ImportError: winsound = None

APP = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
OLD = os.path.join(APP, "popup_config.json")
CFG = os.path.join(os.environ.get("APPDATA", APP), "ClinicConnect", "popup_config.json")  # fixed place: survives moving/replacing the folder
os.makedirs(os.path.dirname(CFG), exist_ok=True)

def load_cfg():
    for p in (CFG, OLD):
        try: return json.load(open(p))
        except Exception: pass

def call(server, path, body=None, tok="", timeout=10):
    r = urllib.request.Request(server + path, data=json.dumps(body).encode() if body is not None else None,
                               headers={"X-Token": tok, "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read() or b"{}")

_WC = {}
def wavdata(urgent, vol, rate=22050):  # our own volume: the sound itself is made quieter/louder (not the Windows volume)
    k = (urgent, vol)
    if k in _WC: return _WC[k]
    amp = 32767 * 0.9 * (vol / 100) ** 1.6
    segs = [(1300, .2), (0, .08)] * 3 if urgent else [(880, .4)]
    fr = bytearray()
    for f, d in segs:
        n = int(rate * d)
        for i in range(n):
            env = min(1, i / 250, (n - i) / 250)
            fr += struct.pack("<h", int(amp * env * math.sin(2 * math.pi * f * i / rate)) if f else 0)
    b = io.BytesIO(); w = wave.open(b, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(fr)); w.close()
    _WC[k] = b.getvalue(); return _WC[k]

def setup():
    cfg = {}; users = {}
    w = tk.Tk(); w.title("Clinic Alerts - setup"); w.geometry("380x340")
    tk.Label(w, text="Server address (shown on the server PC)").pack(pady=(14, 2))
    e = tk.Entry(w, width=34); e.insert(0, _default_server()); e.pack()
    msg = tk.Label(w, text="")
    cb = ttk.Combobox(w, state="readonly", width=32)
    def load():
        try:
            u = call(e.get().strip().rstrip("/"), "/api/users")
            users.clear(); users.update({x["name"]: x["id"] for x in u}); cb["values"] = list(users)
            msg.config(text="Now select your name", fg="green")
        except Exception: msg.config(text="Cannot reach the server", fg="red")
    tk.Button(w, text="Load names", command=load).pack(pady=6); cb.pack()
    tk.Label(w, text="Password").pack(pady=(10, 2)); p = tk.Entry(w, show="*", width=34); p.pack(); msg.pack(pady=8)
    def ok():
        s = e.get().strip().rstrip("/")
        try:
            call(s, "/api/login", {"id": users[cb.get()], "pw": p.get()})
            cfg.update(server=s, user=users[cb.get()], password=p.get()); json.dump(cfg, open(CFG, "w")); w.destroy()
        except Exception: msg.config(text="Wrong name/password or server not reachable", fg="red")
    tk.Button(w, text="Save & start", bg="#0A84FF", fg="white", command=ok).pack(ipadx=20, ipady=4)
    w.mainloop(); return cfg

class Alerts:
    def __init__(s, cfg):
        try:
            import ctypes; ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception: pass
        s.cfg = cfg; s.vol = cfg.get("vol", 60); s.dnd = False; s.tok = ""; s.q = queue.Queue(); s.items = []; s.win = None; s.snd = False
        s.root = tk.Tk(); s.root.withdraw(); s.icon = None; s.vol = 70; s.tray()
        threading.Thread(target=s.listen, daemon=True).start()
        s.root.after(300, s.poll); s.root.mainloop()

    def listen(s):  # reconnects forever; logs in again after a server restart
        c = s.cfg
        while True:
            try:
                s.tok = call(c["server"], "/api/login", {"id": c["user"], "pw": c["password"]})["token"]
                r = urllib.request.urlopen(urllib.request.Request(c["server"] + "/api/stream?t=" + s.tok), timeout=45)
                s.status(True); s.sync()
                for line in r:
                    line = line.decode("utf-8", "ignore").strip()
                    if line.startswith("data:"): s.q.put(json.loads(line[5:]))
            except Exception: s.status(False)
            time.sleep(3)

    def mk(s, color):  # tray icon: coloured square with a white cross
        img = s.PI.new("RGB", (64, 64), color); d = s.PD.Draw(img)
        d.rectangle((27, 12, 37, 52), fill="white"); d.rectangle((12, 27, 52, 37), fill="white"); return img

    def sync(s):  # read my Do-Not-Disturb state from the server
        try: s.dnd = bool(call(s.cfg["server"], "/api/state", tok=s.tok)["me"]["dnd"])
        except Exception: pass

    def set_vol(s, v):
        s.vol = v; s.cfg["vol"] = v
        try: json.dump(s.cfg, open(CFG, "w"))
        except Exception: pass
        threading.Thread(target=lambda: s.beep({}), daemon=True).start()

    def toggle_dnd(s):
        s.dnd = not s.dnd
        threading.Thread(target=lambda: call(s.cfg["server"], "/api/dnd", {"on": s.dnd}, s.tok), daemon=True).start()

    def tray(s):  # icon next to the clock: green = connected, red = offline. Right-click for menu.
        try:
            import pystray; from PIL import Image, ImageDraw
        except Exception: return
        s.PI, s.PD = Image, ImageDraw
        def test(): s.q.put({"t": "msg", "id": "test%d" % time.time(), "frm": "", "from_name": "Test alert", "kind": "action", "icon": "+",
                            "color": "#0f766e", "label": "Test", "text": "Alerts are working on this PC.", "urgent": False, "claim": False, "ts": time.strftime("%I:%M %p")})
        def quit_(): s.icon.stop(); s.root.after(0, s.root.destroy)
        def mkv(v): return lambda: s.set_vol(v)
        vols = pystray.Menu(*[pystray.MenuItem(n, mkv(v), checked=lambda item, v=v: s.vol == v, radio=True)
                              for n, v in (("Mute", 0), ("Low", 25), ("Medium", 50), ("High", 75), ("Maximum", 100))])
        menu = pystray.Menu(pystray.MenuItem("Clinic Alerts (running)", None, enabled=False),
                            pystray.MenuItem("Do not disturb", lambda: s.toggle_dnd(), checked=lambda item: s.dnd),
                            pystray.MenuItem("Volume", vols),
                            pystray.MenuItem("Open Clinic Connect", lambda: webbrowser.open(s.cfg["server"])),
                            pystray.MenuItem("Send test alert", test), pystray.MenuItem("Quit", quit_))
        s.icon = pystray.Icon("ClinicAlerts", s.mk("#d97706"), "Clinic Alerts - connecting...", menu)
        threading.Thread(target=s.icon.run, daemon=True).start()

    def status(s, ok):
        if s.icon:
            try: s.icon.icon = s.mk("#00a884" if ok else "#FF453A"); s.icon.title = "Clinic Alerts - " + ("connected" if ok else "offline, reconnecting...")
            except Exception: pass

    def poll(s):
        try:
            while True:
                e = s.q.get_nowait(); t = e.get("t")
                if t == "msg":
                    if not any(i["id"] == e["id"] for i in s.items): s.items.append(e); s.render(); s.start_sound()
                elif t == "close":
                    s.items = [i for i in s.items if i["id"] != e["id"]]; s.render()
                    if e.get("note"): s.toast(e["note"])
                elif t == "esc":
                    for i in s.items:
                        if i["id"] == e["id"]: i["esc"] = 1
                    s.render()
                elif t == "vol": s.vol = int(e["v"])
                elif t == "toast": s.toast(e["text"])
                elif t == "st": threading.Thread(target=s.sync, daemon=True).start()
                elif t == "info":
                    s.items.append({"id": "i%d" % time.time(), "info": True, "icon": "!", "color": "#d97706", "label": "No reply", "from_name": "No reply yet",
                                    "text": e["text"], "kind": "info", "ts": time.strftime("%I:%M %p"), "frm": ""}); s.render(); s.start_sound()
        except queue.Empty: pass
        if s.win and s.items:
            try: s.win.lift(); s.win.attributes("-topmost", True)
            except Exception: pass
        s.root.after(400, s.poll)

    def corner(s):  # bottom-right of the usable screen (above the taskbar)
        try:
            import ctypes; from ctypes import wintypes
            r = wintypes.RECT(); ctypes.windll.user32.SystemParametersInfoW(48, 0, ctypes.byref(r), 0); return r.right, r.bottom
        except Exception: return s.root.winfo_screenwidth(), s.root.winfo_screenheight() - 48

    def render(s):
        if s.win: s.win.destroy(); s.win = None
        if not s.items: return
        m = s.items[0]; info = m.get("info"); col = "#dc2626" if m.get("urgent") else m.get("color", "#0f766e"); F = "Segoe UI"
        w = tk.Toplevel(s.root); s.win = w; w.overrideredirect(True); w.attributes("-topmost", True); w.configure(bg=col)
        card = tk.Frame(w, bg="white"); card.pack(padx=(6, 0)); tk.Frame(card, width=390, height=1, bg="white").pack()
        if m.get("esc"): tk.Label(card, text="No response for 2 minutes", bg="#dc2626", fg="white", font=(F, 10, "bold")).pack(fill="x")
        head = tk.Frame(card, bg="white"); head.pack(fill="x", padx=18, pady=(16, 0))
        tk.Label(head, text=m["icon"], bg="#f3f4f6", fg=col, width=3, font=("Segoe UI Emoji", 18, "bold")).pack(side="left")
        c2 = tk.Frame(head, bg="white"); c2.pack(side="left", padx=12)
        tk.Label(c2, text=("URGENT · " if m.get("urgent") else "") + m["label"].upper(), fg=col, bg="white", font=(F, 8, "bold")).pack(anchor="w")
        tk.Label(c2, text=m["from_name"], bg="white", fg="#111827", font=(F, 15, "bold")).pack(anchor="w")
        tk.Label(card, text=m["text"] or " ", bg="white", fg="#374151", font=(F, 12), wraplength=350, justify="left").pack(anchor="w", padx=18, pady=(10, 2))
        tk.Label(card, text=m["ts"] + (f"    +{len(s.items) - 1} more waiting" if len(s.items) > 1 else ""), bg="white", fg="#9ca3af", font=(F, 9)).pack(anchor="w", padx=18)
        if not info:
            row = tk.Frame(card, bg="white"); row.pack(fill="x", padx=18, pady=(14, 0))
            for q in ("OK", "Coming in 5 min", "Wait please"):
                tk.Button(row, text=q, font=(F, 10), bg="#f3f4f6", activebackground="#e5e7eb", bd=0, padx=12, pady=9, cursor="hand2", command=lambda q=q: s.reply(m, q)).pack(side="left", padx=(0, 6), fill="x", expand=True)
            rr = tk.Frame(card, bg="white"); rr.pack(fill="x", padx=18, pady=(10, 0))
            e = tk.Entry(rr, font=(F, 12), relief="solid", bd=1); e.pack(side="left", fill="x", expand=True, ipady=8)
            e.bind("<Button-1>", lambda ev: (w.focus_force(), e.focus_set())); e.bind("<Return>", lambda ev: s.reply(m, e.get()))
            tk.Button(rr, text="Send", font=(F, 10, "bold"), bg=col, fg="white", activebackground=col, activeforeground="white", bd=0, padx=16, cursor="hand2", command=lambda: s.reply(m, e.get())).pack(side="left", padx=(6, 0), ipady=6)
        if m.get("claim"):
            tk.Button(card, text="I'll take it", bg="#f59e0b", fg="white", activebackground="#d97706", activeforeground="white", font=(F, 12, "bold"), bd=0, cursor="hand2",
                      command=lambda: s.done(m, "/api/claim")).pack(fill="x", padx=18, pady=(12, 0), ipady=8)
        tk.Button(card, text="OK" if info else "Understood", bg="#16a34a", fg="white", activebackground="#15803d", activeforeground="white", font=(F, 15, "bold"), bd=0,
                  cursor="hand2", command=lambda: s.done(m, "/api/ack")).pack(fill="x", padx=18, pady=18, ipady=11)
        w.update_idletasks(); R, B = s.corner()
        w.geometry(f"+{R - w.winfo_reqwidth() - 16}+{B - w.winfo_reqheight() - 16}")

    def done(s, m, path):
        s.items = [i for i in s.items if i["id"] != m["id"]]; s.render()
        if not m.get("info"): threading.Thread(target=lambda: call(s.cfg["server"], path, {"id": m["id"]}, s.tok), daemon=True).start()

    def reply(s, m, text):
        if not text.strip(): return
        threading.Thread(target=lambda: call(s.cfg["server"], "/api/send", {"to": m["frm"], "text": text.strip()}, s.tok), daemon=True).start()
        s.done(m, "/api/ack")

    def start_sound(s):
        if not s.snd: s.snd = True; s.beeper()
    def beeper(s):  # repeats every 3-5 seconds until Understood is clicked
        if not s.items: s.snd = False; return
        m = s.items[0]; threading.Thread(target=s.beep, args=(m,), daemon=True).start()
        s.root.after(2000 if m.get("esc") else random.randint(3000, 5000), s.beeper)
    def wav(s, f, ms):  # tone at the chosen volume (relative to the Windows volume)
        import wave, io, math, struct
        r = 22050; n = int(r * ms / 1000); b = io.BytesIO(); w = wave.open(b, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(r)
        w.writeframes(b"".join(struct.pack("<h", int(32000 * s.vol / 100 * math.sin(2 * math.pi * f * i / r) * min(1, i / 300))) for i in range(n))); w.close()
        return b.getvalue()

    def beep(s, m):
        if not winsound or s.vol <= 0: return
        if m.get("info") and m.get("beeped"): return
        m["beeped"] = 1; u = m.get("urgent")
        try:
            for _ in range(3 if u else 1): winsound.PlaySound(s.wav(1300 if u else 880, 250 if u else 450), winsound.SND_MEMORY)
        except Exception: pass

    def toast(s, text):
        t = tk.Toplevel(s.root); t.overrideredirect(True); t.attributes("-topmost", True); t.configure(bg="#1D1D1F")
        tk.Label(t, text=text, bg="#1D1D1F", fg="white", font=("Segoe UI", 13), padx=18, pady=12).pack()
        t.update_idletasks(); t.geometry(f"+{t.winfo_screenwidth() - t.winfo_reqwidth() - 20}+20"); t.after(4000, t.destroy)

def _default_server():  # StaffPC\server.txt (made by `build`) pre-fills the address
    try: return open(os.path.join(APP, "server.txt")).read().strip()
    except Exception: return "http://192.168.1.15:8765"

def _me(): return sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)

def build():  # run ONCE on the server PC: makes StaffPC\ClinicAlerts.exe (staff PCs then need NO Python)
    import subprocess, shutil, socket
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "pystray", "pillow"], check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--onefile", "--noconsole", "--hidden-import", "pystray._win32", "--name", "ClinicAlerts", os.path.abspath(__file__)], check=True, cwd=APP)
    out = os.path.join(APP, "StaffPC"); os.makedirs(out, exist_ok=True)
    shutil.copy(os.path.join(APP, "dist", "ClinicAlerts.exe"), out)
    for f in ("popup_client.py", "tools.py"): shutil.copy(os.path.join(APP, f), out)  # Python fallback if the .exe is blocked
    try: port = int(json.load(open(os.path.join(APP, "config.json")))["port"])
    except Exception: port = 8765
    k = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: k.connect(("8.8.8.8", 80)); ip = k.getsockname()[0]
    except Exception: ip = "192.168.1.15"
    open(os.path.join(out, "server.txt"), "w").write(f"http://{ip}:{port}")
    print("\nDONE. Copy the folder  StaffPC  to each staff PC (put it in C:\\ClinicAlerts). Double-click ClinicAlerts.exe,\nor if Windows blocks it: install Python there and run   python popup_client.py")

if __name__ == "__main__":
    if len(sys.argv) > 1:  # no .bat needed:  python popup_client.py install | uninstall
        if sys.argv[1] == "build": build(); sys.exit()
        import tools; me = _me()
        if sys.argv[1] == "install": tools.autostart("ClinicAlerts", me); tools.hidden(me)
        else:
            tools.autostart("ClinicAlerts", me, True); tools.stop("popup_client")
            for p in (CFG, OLD):
                try: os.remove(p)
                except OSError: pass
        sys.exit()
    import socket
    _lock = socket.socket(); 
    try: _lock.bind(("127.0.0.1", 47653))  # only one copy per PC
    except OSError: sys.exit()
    cfg = load_cfg()
    if not cfg:
        cfg = setup()
        if cfg:  # first run: also start automatically with Windows (+ watchdog)
            import tools; tools.autostart("ClinicAlerts", _me())
    if cfg: Alerts(cfg)
