"""Clinic Connect server (Python stdlib only). Run START_CLINIC.bat or: python server.py"""
import json, os, sys, hashlib, threading, queue, socket, uuid, re, time, csv, io, glob, shutil
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

APP = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(getattr(sys, "_MEIPASS", APP), "static")
try: PORT = int(json.load(open(os.path.join(APP, "config.json")))["port"])
except Exception: PORT = 8765
BK = os.path.join(APP, "data", "backups"); os.makedirs(BK, exist_ok=True)
DB = os.path.join(APP, "data", "clinic_data.json"); SF = os.path.join(APP, "data", "sessions.json")
LOCK = threading.RLock(); LIVE = {}   # uid -> open connections

def H(p): return hashlib.sha256(("zc|" + p).encode()).hexdigest()
def now(): return datetime.now().strftime("%I:%M %p")
def slug(s): return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or uuid.uuid4().hex[:6]
def fmt(t): return datetime.fromtimestamp(t).strftime("%H:%M:%S") if t else ""
STAT = ("avail", "consult", "rest")

def atomic(path, obj):  # write to temp file first, so a power cut can't damage the real file
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def seed():
    A = lambda i, l, t, to, c, cl=False: {"icon": i, "label": l, "text": t, "to": to, "color": c, "claim": cl}
    U = lambda n, r, p: {"name": n, "role": r, "pw": H(p)}
    return {"roles": {
        "admin": {"label": "Admin", "actions": []},
        "doctor": {"label": "Doctor", "status": True, "actions": [
            A("😴", "Resting", "is Resting", "reception", "#FF453A"), A("🏥", "Patient Ready", "- Patient Ready", "reception", "#30D158")]},
        "reception": {"label": "Reception", "actions": [A("📸", "Photo Required", "Photo Required", "photo", "#0A84FF", True)]},
        "photo": {"label": "Photo Staff", "actions": []}},
        "users": {"admin": U("Admin", "admin", "admin123"), "dr_anchal": U("Dr. Anchal Shah", "doctor", "Anchal"),
                  "dr_diwaker": U("Dr. Diwaker Sharma", "doctor", "Diwaker"), "reception1": U("Reception 1", "reception", "Krishna"),
                  "reception2": U("Reception 2", "reception", "Mansi"), "dhaval": U("Dhaval", "photo", "Dhaval"), "vaibhav": U("Vaibhav", "photo", "Vaibhav")},
        "msgs": [], "status": {}, "dnd": {}}

def mig(d):  # upgrade data from older versions
    d.setdefault("status", {}); d.setdefault("dnd", {}); r = d["roles"]
    if "doctor" in r: r["doctor"].setdefault("status", True)
    for a in r.get("reception", {}).get("actions", []):
        if a.get("label") == "Photo Required": a.setdefault("claim", True)
    for m in d["msgs"]:
        m.setdefault("st", "read" if m.get("read") else "sent"); m.setdefault("gid", m["id"])
        for k, v in (("urgent", False), ("claim", False), ("t0", 0), ("dt", 0), ("rt", 0), ("esc", 0), ("del", False)): m.setdefault(k, v)
    return d

def save(d=None):
    with LOCK: atomic(DB, d or D)

def load():  # a damaged file is NEVER overwritten with defaults
    if os.path.exists(DB):
        try: return mig(json.load(open(DB, encoding="utf-8")))
        except Exception:
            os.replace(DB, DB + ".corrupt-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
            print("!! Data file was damaged (kept as .corrupt). Trying backups...")
            for p in sorted(glob.glob(BK + "/*.json"), reverse=True):
                try: return mig(json.load(open(p, encoding="utf-8")))
                except Exception: pass
            sys.exit("Data file damaged and no backup found. The damaged file was kept in /data (.corrupt). Nothing was erased.")
    d = seed(); save(d); return d

D = load(); save(D)
try: shutil.copy(DB, os.path.join(BK, "clinic_" + datetime.now().strftime("%Y%m%d") + ".json"))
except Exception: pass
try: SESS = json.load(open(SF))
except Exception: SESS = {}
SESS = {t: u for t, u in SESS.items() if u in D["users"]}
def save_sess():
    with LOCK: atomic(SF, SESS)

def push(uid, ev):
    qs = LIVE.get(uid, [])
    for q in qs: q.put(ev)
    return bool(qs)

def uname(i): return D["users"].get(i, {}).get("name", i)
def evt(m):
    m = dict(m); m["t"] = "msg"; m["from_name"] = uname(m["frm"]); return m

def deliver(frm, to_list, kind, icon, color, label, text, urgent=False, claim=False):
    gid = uuid.uuid4().hex[:8]
    with LOCK:
        for uid in to_list:
            if uid not in D["users"] or uid == frm: continue
            m = {"id": uuid.uuid4().hex[:10], "gid": gid, "frm": frm, "to": uid, "kind": kind, "icon": icon, "color": color,
                 "label": label, "text": text, "urgent": urgent, "claim": claim, "ts": now(), "t0": time.time(),
                 "st": "sent", "dt": 0, "rt": 0, "esc": 0, "del": False}
            D["msgs"].append(m)
            if D["dnd"].get(uid) and not urgent:  # Do Not Disturb: no pop-up, sender is told (urgent still comes through)
                push(uid, {"t": "st"}); push(frm, {"t": "toast", "text": f"{uname(uid)} is on Do Not Disturb - they will see it later"})
                if LIVE.get(uid): m["st"] = "delivered"; m["dt"] = time.time()
            elif push(uid, evt(m)): m["st"] = "delivered"; m["dt"] = time.time()
        D["msgs"] = D["msgs"][-1500:]; push(frm, {"t": "st"}); save()

def ack(uid, mid, claim=False):
    with LOCK:
        m = next((x for x in D["msgs"] if x["id"] == mid and x["to"] == uid), None)
        if not m or m["st"] == "read" or m.get("del"): return
        name = uname(uid); group = claim or not m["claim"]
        m["st"] = "read"; m["rt"] = time.time(); push(uid, {"t": "close", "id": mid})
        push(m["frm"], {"t": "toast", "text": f"{name} {'took it' if claim else 'understood'}: {m['label']}"})
        if group:
            for x in D["msgs"]:
                if x["gid"] == m["gid"] and x["id"] != mid and x["st"] != "read" and x["to"] != uid:
                    x["st"] = "read"; x["rt"] = time.time()
                    push(x["to"], {"t": "close", "id": x["id"], "note": f"{name} already {'took it' if claim else 'saw this'}"})
        push(m["frm"], {"t": "st"}); save()

def watcher():  # 2 min without reply: re-alert the receiver louder and tell the SENDER (never the admin)
    while True:
        time.sleep(10)
        with LOCK:
            for m in list(D["msgs"]):
                if m["st"] == "read" or m["esc"] or m.get("del") or not m["t0"] or time.time() - (m.get("ta") or m["t0"]) < 120: continue
                to = D["users"].get(m["to"])
                if not to or to["role"] == "admin" or D["dnd"].get(m["to"]): continue
                m["esc"] = 1; save(); push(m["to"], {"t": "esc", "id": m["id"]})
                if D["users"].get(m["frm"], {}).get("role") != "admin":
                    push(m["frm"], {"t": "info", "text": f"{to['name']} has not replied for 2 minutes: {m['text']}"})
                push(m["frm"], {"t": "st"})

def state(uid):
    u = D["users"][uid]; role = D["roles"].get(u["role"], {"label": "?", "actions": []})
    last, unread = {}, {}
    for m in D["msgs"]:
        o = m["to"] if m["frm"] == uid else m["frm"] if m["to"] == uid else None
        if o: last[o] = m; unread[o] = unread.get(o, 0) + (1 if m["to"] == uid and m["st"] != "read" and not m.get("del") else 0)
    people = []
    for i, v in D["users"].items():
        if i == uid: continue
        m = last.get(i)
        people.append({"id": i, "name": v["name"], "role": v["role"], "online": bool(LIVE.get(i)), "unread": unread.get(i, 0),
                       "last": ("Message deleted" if m.get("del") else m["text"]) if m else "", "dnd": bool(D["dnd"].get(i)), "lts": m["ts"] if m else "", "lmine": bool(m and m["frm"] == uid),
                       "lst": m["st"] if m else "", "t": m["t0"] if m else 0})
    people.sort(key=lambda p: (-p["t"], p["name"]))
    board = [{"id": i, "name": v["name"], "s": D["status"].get(i, {}).get("s", "na")} for i, v in D["users"].items() if v["role"] == "doctor"]
    return {"me": {"id": uid, "name": u["name"], "role": u["role"], "dnd": bool(D["dnd"].get(uid))}, "role": role, "roles": {k: v["label"] for k, v in D["roles"].items()},
            "people": people, "board": board, "vol": u.get("vol", 70), "can_status": bool(role.get("status")), "my_status": D["status"].get(uid, {}).get("s", "na")}

def day(t):
    if not t: return ""
    d = datetime.fromtimestamp(t).date(); n = datetime.now().date()
    return "Today" if d == n else "Yesterday" if (n - d).days == 1 else d.strftime("%d %b %Y")

def chat(uid, w):
    out = []
    for m in D["msgs"]:
        if (m["frm"] == uid and m["to"] == w) or (m["frm"] == w and m["to"] == uid):
            e = dict(evt(m), day=day(m["t0"]), age=round(time.time() - m["t0"]) if m["t0"] else 9999)
            if m.get("del"): e["text"] = ""
            out.append(e)
    return out[-200:]

def hist():
    rows = []
    for m in D["msgs"][::-1][:600]:
        rows.append({"date": datetime.fromtimestamp(m["t0"]).strftime("%d-%b %H:%M") if m["t0"] else "", "from": uname(m["frm"]), "to": uname(m["to"]),
                     "label": m["label"], "text": "[deleted]" if m.get("del") else m["text"], "urgent": m["urgent"], "st": m["st"], "dtm": fmt(m["dt"]), "rtm": fmt(m["rt"]),
                     "secs": round(m["rt"] - m["t0"]) if m["rt"] and m["t0"] else None})
    st = {}
    for r in rows:
        if r["secs"] is not None: st.setdefault(r["to"], []).append(r["secs"])
    stats = sorted([{"name": k, "n": len(v), "avg": round(sum(v) / len(v))} for k, v in st.items()], key=lambda x: -x["avg"])
    return {"rows": rows, "stats": stats}

class Hd(BaseHTTPRequestHandler):
    def log_message(s, *a): pass
    def out(s, b, ct, extra=None):
        s.send_response(200); s.send_header("Content-Type", ct); s.send_header("Content-Length", str(len(b))); s.send_header("Cache-Control", "no-cache")
        for k, v in (extra or {}).items(): s.send_header(k, v)
        s.end_headers(); s.wfile.write(b)
    def js(s, o, c=200):
        b = json.dumps(o).encode(); s.send_response(c); s.send_header("Content-Type", "application/json")
        s.send_header("Content-Length", str(len(b))); s.end_headers(); s.wfile.write(b)
    def uid(s):
        q = parse_qs(urlparse(s.path).query)
        return SESS.get(s.headers.get("X-Token") or (q.get("t") or [""])[0])

    def do_GET(s):
        p = urlparse(s.path).path
        if p == "/" or p.startswith("/static/"):
            f = "index.html" if p == "/" else os.path.basename(p); fp = os.path.join(STATIC, f)
            if not os.path.isfile(fp): return s.send_error(404)
            return s.out(open(fp, "rb").read(), {"html": "text/html; charset=utf-8", "css": "text/css", "js": "application/javascript"}.get(f.rsplit(".", 1)[-1], "application/octet-stream"))
        if p == "/api/users":
            return s.js([{"id": i, "name": v["name"], "role": D["roles"].get(v["role"], {}).get("label", "")} for i, v in D["users"].items()])
        uid = s.uid()
        if not uid: return s.js({"error": "auth"}, 401)
        if p == "/api/state": return s.js(state(uid))
        if p == "/api/chat": return s.js(chat(uid, (parse_qs(urlparse(s.path).query).get("w") or [""])[0]))
        if p.startswith("/api/admin/"):
            if D["users"][uid]["role"] != "admin": return s.js({"error": "no"}, 403)
            if p == "/api/admin/data":
                return s.js({"users": {i: {"name": v["name"], "role": v["role"]} for i, v in D["users"].items()}, "roles": D["roles"]})
            if p == "/api/admin/history": return s.js(hist())
            if p == "/api/admin/export":
                o = io.StringIO(); w = csv.writer(o)
                w.writerow(["Date", "From", "To", "Type", "Message", "Urgent", "Status", "Delivered at", "Understood at", "Seconds to understand"])
                for r in hist()["rows"]: w.writerow([r["date"], r["from"], r["to"], r["label"], r["text"], "yes" if r["urgent"] else "", r["st"], r["dtm"], r["rtm"], r["secs"] if r["secs"] is not None else ""])
                return s.out(o.getvalue().encode("utf-8-sig"), "text/csv", {"Content-Disposition": "attachment; filename=clinic_history.csv"})
        if p == "/api/stream":
            q = queue.Queue(); LIVE.setdefault(uid, []).append(q)
            for i in list(LIVE): push(i, {"t": "st"})
            try:
                s.send_response(200); s.send_header("Content-Type", "text/event-stream"); s.send_header("Cache-Control", "no-cache"); s.end_headers()
                with LOCK:
                    s.wfile.write(f'data: {json.dumps({"t": "vol", "v": D["users"][uid].get("vol", 70)})}\n\n'.encode())
                    pend = [m for m in D["msgs"] if m["to"] == uid and m["st"] != "read" and not m.get("del") and not (D["dnd"].get(uid) and not m["urgent"])]
                    for m in pend:
                        s.wfile.write(f"data: {json.dumps(evt(m))}\n\n".encode())
                        if m["st"] == "sent": m["st"] = "delivered"; m["dt"] = time.time(); push(m["frm"], {"t": "st"})
                    if pend: save()
                s.wfile.flush()
                while True:
                    try: o = f"data: {json.dumps(q.get(timeout=15))}\n\n"
                    except queue.Empty: o = ": ping\n\n"
                    s.wfile.write(o.encode()); s.wfile.flush()
            except Exception: pass
            finally:
                LIVE[uid].remove(q)
                for i in list(LIVE): push(i, {"t": "st"})
            return
        s.send_error(404)

    def do_POST(s):
        p = urlparse(s.path).path
        b = json.loads(s.rfile.read(int(s.headers.get("Content-Length", 0)) or 0) or b"{}")
        if p == "/api/login":
            u = D["users"].get(b.get("id"))
            if u and u["pw"] == H(b.get("pw", "")):
                t = uuid.uuid4().hex; SESS[t] = b["id"]; save_sess(); return s.js({"token": t})
            return s.js({"error": "Wrong password"}, 400)
        uid = s.uid()
        if not uid: return s.js({"error": "auth"}, 401)
        me = D["users"][uid]; role = D["roles"].get(me["role"], {"actions": []})
        if p == "/api/send":
            urg = bool(b.get("urgent"))
            if b.get("action") is not None:
                a = role["actions"][int(b["action"])]
                to = b["to"] if b.get("to") not in (None, "all") else [i for i, v in D["users"].items() if v["role"] == a["to"]]
                note = (b.get("note") or "").strip()[:80]
                deliver(uid, [to] if isinstance(to, str) else to, "action", a["icon"], a["color"], a["label"],
                        a["text"] + (" — " + note if note else ""), urg, bool(a.get("claim")))
            else:
                if not (b.get("text") or "").strip() or b.get("to") not in D["users"]: return s.js({"error": "empty"}, 400)
                deliver(uid, [b["to"]], "message", "💬", "#0A84FF", "Message", b["text"].strip()[:500], urg)
            return s.js({"ok": 1})
        if p == "/api/dnd":
            on = bool(b.get("on"))
            with LOCK:
                D["dnd"][uid] = on
                if not on:  # back at desk: show what arrived meanwhile
                    for m in D["msgs"]:
                        if m["to"] == uid and m["st"] != "read" and not m.get("del"): m["ta"] = time.time(); push(uid, evt(m))
                save()
            for i in list(LIVE): push(i, {"t": "st"})
            return s.js({"ok": 1})
        if p == "/api/delete":  # unsend, only within 1 minute
            with LOCK:
                m = next((x for x in D["msgs"] if x["id"] == b.get("id") and x["frm"] == uid), None)
                if not m: return s.js({"error": "Not found"}, 404)
                if time.time() - m["t0"] > 60: return s.js({"error": "Too late: a message can only be deleted within 1 minute"}, 400)
                m["del"] = True; save()
            push(m["to"], {"t": "close", "id": m["id"]}); push(m["to"], {"t": "st"}); push(uid, {"t": "st"})
            return s.js({"ok": 1})
        if p in ("/api/ack", "/api/claim"): ack(uid, b.get("id"), p == "/api/claim"); return s.js({"ok": 1})
        if p == "/api/volume":
            val = max(0, min(100, int(b.get("v", 70))))
            with LOCK: D["users"][uid]["vol"] = val; save()
            push(uid, {"t": "vol", "v": val}); return s.js({"ok": 1})
        if p == "/api/status":
            if not role.get("status") or b.get("s") not in STAT: return s.js({"error": "no"}, 403)
            with LOCK:
                D["status"][uid] = {"s": b["s"], "ts": time.time()}; save()
            for i in list(LIVE): push(i, {"t": "st"})
            return s.js({"ok": 1})
        if me["role"] != "admin": return s.js({"error": "no"}, 403)
        with LOCK:
            if p == "/api/admin/user_save":
                i = b.get("id")
                if b.get("role") not in D["roles"]: return s.js({"error": "That role does not exist"}, 400)
                if i and i in D["users"]:
                    if i == uid and b["role"] != me["role"]: return s.js({"error": "You can't change your own role"}, 400)
                    D["users"][i]["name"] = b["name"]; D["users"][i]["role"] = b["role"]
                    if b.get("pw"): D["users"][i]["pw"] = H(b["pw"])
                else:
                    if not b.get("pw") or not b.get("name"): return s.js({"error": "Name and password needed"}, 400)
                    i = slug(b["name"])
                    while i in D["users"]: i += "1"
                    D["users"][i] = {"name": b["name"], "role": b["role"], "pw": H(b["pw"])}
            elif p == "/api/admin/user_del":
                if b["id"] == uid: return s.js({"error": "You can't delete yourself"}, 400)
                D["users"].pop(b["id"], None)
                for t in [t for t, u in SESS.items() if u == b["id"]]: SESS.pop(t)
                save_sess()
            elif p == "/api/admin/role_save":
                i = b.get("id") or slug(b["label"]); old = D["roles"].get(i, {})
                D["roles"][i] = {"label": "Admin" if i == "admin" else b["label"], "actions": b.get("actions", []), **({"status": True} if old.get("status") else {})}
            elif p == "/api/admin/role_del":
                if b["id"] == "admin" or any(v["role"] == b["id"] for v in D["users"].values()): return s.js({"error": "Role is in use (or is Admin)"}, 400)
                D["roles"].pop(b["id"], None)
            save()
        s.js({"ok": 1})

def lan_ip():
    try:
        k = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); k.connect(("8.8.8.8", 80)); ip = k.getsockname()[0]; k.close(); return ip
    except Exception: return "127.0.0.1"

if __name__ == "__main__":
    if len(sys.argv) > 1:  # no .bat needed:  python server.py install | uninstall | firewall | hidden | stop
        import tools; a = sys.argv[1]; me = os.path.abspath(__file__)
        if a == "install": tools.autostart("ClinicConnectServer", me); tools.hidden(me)
        elif a == "uninstall": tools.autostart("ClinicConnectServer", me, True); tools.stop("server.py")
        elif a == "firewall": tools.firewall(PORT)
        elif a == "hidden": tools.hidden(me)
        elif a == "stop": tools.stop("server.py")
        sys.exit()
    ThreadingHTTPServer.daemon_threads = True
    threading.Thread(target=watcher, daemon=True).start()
    print(f"\n  Clinic Connect running.\n  Open on ANY device on this WiFi:  http://{lan_ip()}:{PORT}\n  Admin login: Admin / admin123\n  Keep this window open. Ctrl+C to stop.\n")
    ThreadingHTTPServer(("0.0.0.0", PORT), Hd).serve_forever()
