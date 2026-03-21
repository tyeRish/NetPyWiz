import tkinter as tk
from tkinter import ttk, simpledialog
import threading
import time
from monitor import start_monitor, status, status_lock, latency_history, history_lock
from exporter import export_to_desktop, load_session_csv
from sparkline import draw_sparkline
from nmap_scan import run_nmap
from startup import (ask_subnet, run_splash_scan, ask_rescan,
                     ask_export_mode, best_font)
from config import load as load_config, save as save_config

BG          = "#0a0a0f"
BG2         = "#0f0f1a"
BG3         = "#1a1a2e"
CYAN        = "#00f5ff"
MAGENTA     = "#ff00ff"
MAGENTA_DIM = "#cc00cc"
GREEN       = "#00ff9f"
RED         = "#ff2255"
AMBER       = "#ffaa00"
DIM         = "#444466"
WHITE       = "#e0e0ff"
YELLOW      = "#ffe94d"

device_notes  = {}
previous_macs = set()
session_file  = {"path": None}
devices       = []
subnet        = "unknown"
config        = load_config()

# ── Single root — hidden during startup ───────────────────────────────────────
root = tk.Tk()
root.withdraw()
root.title("NetPyWiz — Network Monitor")
root.configure(bg=BG)

# Set icon early so all Toplevels inherit it
try:
    from PIL import Image, ImageDraw, ImageTk

    def _make_icon():
        img  = Image.new("RGB", (64, 64), "#0a0a0f")
        draw = ImageDraw.Draw(img)
        draw.rectangle([8, 14, 56, 50], outline="#ff00ff", width=2, fill="#1a1a2e")
        for i in range(8):
            x = 13 + i * 5
            draw.rectangle([x, 20, x+3, 36], fill="#ffaa00")
        draw.rectangle([20, 48, 44, 56], outline="#ff00ff", width=1, fill="#1a1a2e")
        draw.rectangle([4,  4,  12, 12], fill="#00f5ff")
        draw.rectangle([52, 4,  60, 12], fill="#00f5ff")
        draw.rectangle([4,  52, 12, 60], fill="#00f5ff")
        draw.rectangle([52, 52, 60, 60], fill="#00f5ff")
        return img

    _icon_img  = _make_icon()
    _icon_photo = ImageTk.PhotoImage(_icon_img)
    root.iconphoto(True, _icon_photo)  # True = apply to all future Toplevels too
except Exception as e:
    print(f"Could not set icon: {e}")

# ── Startup flow ──────────────────────────────────────────────────────────────
error_msg = ""
while not devices:
    startup = ask_subnet(root, error_msg,
                       default_subnet=config.get("last_subnet", "192.168.1.0/24"))

    if not startup["subnet"] and not startup["load_file"]:
        root.destroy()
        import sys; sys.exit()

    if startup["load_file"]:
        loaded = load_session_csv(startup["load_file"])
        if not loaded:
            error_msg = "Could not read session file — try another"
            continue

        previous_macs.update(d["mac"] for d in loaded)
        session_file["path"] = startup["load_file"]

        try:
            parts  = loaded[0]["ip"].rsplit(".", 1)
            subnet = f"{parts[0]}.0/24"
        except Exception:
            subnet = "unknown"

        choice = ask_rescan(root, subnet)

        if choice == "rescan":
            scanned    = run_splash_scan(root, subnet)
            loaded_ips = {d["ip"] for d in loaded}
            for d in scanned:
                if d["ip"] not in loaded_ips:
                    d["new_device"] = True
                    loaded.append(d)
                else:
                    for ld in loaded:
                        if ld["ip"] == d["ip"]:
                            ld["hostname"] = d["hostname"]
                            ld["vendor"]   = d["vendor"]
            devices = loaded

        elif choice == "monitor_only":
            devices = loaded

        else:
            error_msg = ""
            continue

    else:
        subnet  = startup["subnet"]
        scanned = run_splash_scan(root, subnet)
        if not scanned:
            error_msg = f"No devices found on {subnet} — check subnet and try again"
            continue
        devices = scanned
        save_config({"last_subnet": subnet})

# ── Build main UI ─────────────────────────────────────────────────────────────
root.geometry(config.get("window_size", "1280x760"))
root.minsize(900, 600)

# Header
header = tk.Frame(root, bg=BG2, height=56)
header.pack(fill="x")
header.pack_propagate(False)

logo_canvas = tk.Canvas(header, width=38, height=38,
    bg=BG2, highlightthickness=0)
logo_canvas.pack(side="left", padx=(14,4), pady=8)

def draw_eth_logo(c):
    c.create_rectangle(4, 8, 34, 32, outline=MAGENTA, width=2, fill=BG3)
    for i in range(8):
        x = 7 + i * 3.5
        c.create_rectangle(x, 12, x+2, 24, fill=AMBER, outline="")
    c.create_rectangle(11, 30, 27, 35, outline=MAGENTA, width=1, fill=BG3)

draw_eth_logo(logo_canvas)

tk.Label(header, text="NETPYWIZ",
    bg=BG2, fg=MAGENTA, font=best_font(18, True)).pack(side="left", pady=10)
tk.Label(header, text="// NETWORK MONITOR",
    bg=BG2, fg=CYAN, font=best_font(12)).pack(side="left", padx=8, pady=10)

if session_file["path"]:
    tk.Label(header, text="◈ SESSION LOADED",
        bg=BG2, fg=YELLOW, font=best_font(8)).pack(side="left", padx=8)

clock_var = tk.StringVar()
tk.Label(header, textvariable=clock_var,
    bg=BG2, fg=DIM, font=best_font(10)).pack(side="right", padx=20)
tk.Label(header, text=f"◈  {subnet}  ◈  {len(devices)} DEVICES",
    bg=BG2, fg=AMBER, font=best_font(9)).pack(side="right", padx=10)

def tick():
    clock_var.set(time.strftime("◈  %Y-%m-%d  %H:%M:%S"))
    root.after(1000, tick)
tick()

tk.Frame(root, bg=MAGENTA, height=2).pack(fill="x")

# Stats bar
stats_frame = tk.Frame(root, bg=BG2)
stats_frame.pack(fill="x")

online_var  = tk.StringVar(value="▲ ONLINE:  0")
offline_var = tk.StringVar(value="▼ OFFLINE:  0")
unknown_var = tk.StringVar(value="◈ PENDING:  0")
new_var     = tk.StringVar(value="")

for var, color in [(online_var, GREEN), (offline_var, RED), (unknown_var, DIM)]:
    tk.Label(stats_frame, textvariable=var, bg=BG2, fg=color,
        font=best_font(9, True)).pack(side="left", padx=20, pady=4)
tk.Label(stats_frame, textvariable=new_var,
    bg=BG2, fg=YELLOW, font=best_font(9, True)).pack(side="left", padx=20, pady=4)

tk.Frame(root, bg=CYAN, height=1).pack(fill="x")

# ── Toolbar ───────────────────────────────────────────────────────────────────
toolbar = tk.Frame(root, bg=BG2)
toolbar.pack(fill="x")

# Filter
tk.Label(toolbar, text="⌕", bg=BG2, fg=CYAN,
    font=best_font(13)).pack(side="left", padx=(16,4), pady=6)

filter_var = tk.StringVar()
filter_entry = tk.Entry(toolbar, textvariable=filter_var,
    bg=BG3, fg=DIM, insertbackground=CYAN, selectbackground=MAGENTA_DIM,
    font=best_font(10), relief="flat", bd=0, width=30)
filter_entry.pack(side="left", ipady=5, pady=6)
filter_entry.insert(0, "FILTER DEVICES...")

def on_filter_focus_in(e):
    if filter_entry.get() == "FILTER DEVICES...":
        filter_entry.delete(0, "end")
        filter_entry.config(fg=CYAN)

def on_filter_focus_out(e):
    if not filter_entry.get():
        filter_entry.insert(0, "FILTER DEVICES...")
        filter_entry.config(fg=DIM)

filter_entry.bind("<FocusIn>",  on_filter_focus_in)
filter_entry.bind("<FocusOut>", on_filter_focus_out)

tk.Frame(toolbar, bg=CYAN, width=1).pack(side="left", fill="y", padx=4)

# Rescan button
rescan_btn = tk.Button(toolbar, text="⟳  RESCAN",
    bg=BG3, fg=CYAN, font=best_font(9, True),
    relief="flat", cursor="hand2",
    activebackground=CYAN, activeforeground=BG, bd=0)
rescan_btn.pack(side="left", padx=12, pady=6, ipadx=10)

tk.Frame(root, bg=CYAN, height=1).pack(fill="x")

# Table
table_frame = tk.Frame(root, bg=BG)
table_frame.pack(fill="both", expand=True)

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview",
    background=BG3, foreground=WHITE, fieldbackground=BG3,
    rowheight=30, font=best_font(10), borderwidth=0)
style.configure("Treeview.Heading",
    background=BG2, foreground=CYAN,
    font=best_font(9, True), relief="flat", borderwidth=0)
style.map("Treeview",
    background=[("selected", "#16162a")],
    foreground=[("selected", CYAN)])
style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

columns = ("status","ip","mac","hostname","vendor","port","latency","avg_latency","downtime")
tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

col_defs = {
    "status":      ("STATUS",      90),
    "ip":          ("IP ADDRESS", 130),
    "mac":         ("MAC ADDRESS",155),
    "hostname":    ("HOSTNAME",   200),
    "vendor":      ("VENDOR",     160),
    "port":        ("SW PORT",    100),
    "latency":     ("LAT ms",      90),
    "avg_latency": ("AVG ms",      90),
    "downtime":    ("DOWN s",      80),
}

for col, (label, width) in col_defs.items():
    tree.heading(col, text=label)
    tree.column(col, width=width,
        anchor="center" if col in ("status","port","latency","avg_latency","downtime") else "w")

tree.tag_configure("green",   background=BG3, foreground=GREEN)
tree.tag_configure("red",     background=BG3, foreground=RED)
tree.tag_configure("unknown", background=BG3, foreground=DIM)
tree.tag_configure("new",     background="#1a1a00", foreground=YELLOW)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
tree.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

def add_device_row(d):
    if tree.exists(d["ip"]):
        return
    is_new = d.get("new_device", False)
    tag    = "new"   if is_new else "unknown"
    label  = "★ NEW" if is_new else "◈ INIT"
    tree.insert("", "end", iid=d["ip"], values=(
        label, d["ip"], d["mac"], d["hostname"],
        d["vendor"], d.get("port",""), "", "", "0"
    ), tags=(tag,))

for d in devices:
    add_device_row(d)

# Info bar
tk.Frame(root, bg=MAGENTA, height=1).pack(fill="x")
info_bar = tk.Frame(root, bg=BG2, height=90)
info_bar.pack(fill="x")
info_bar.pack_propagate(False)

info_ip_var     = tk.StringVar(value="")
info_status_var = tk.StringVar(value="")
info_lat_var    = tk.StringVar(value="")
info_avg_var    = tk.StringVar(value="")
info_down_var   = tk.StringVar(value="")
info_vendor_var = tk.StringVar(value="")
info_mac_var    = tk.StringVar(value="")

left_info = tk.Frame(info_bar, bg=BG2)
left_info.pack(side="left", padx=16, pady=8)
tk.Label(left_info, textvariable=info_ip_var,
    bg=BG2, fg=MAGENTA, font=best_font(14, True)).pack(anchor="w")
tk.Label(left_info, textvariable=info_status_var,
    bg=BG2, fg=GREEN, font=best_font(9)).pack(anchor="w")

tk.Frame(info_bar, bg=DIM, width=1).pack(side="left", fill="y", pady=8)

mid_info = tk.Frame(info_bar, bg=BG2)
mid_info.pack(side="left", padx=16, pady=8)
for label, var, color in [
    ("LATENCY",  info_lat_var,  CYAN),
    ("AVG",      info_avg_var,  CYAN),
    ("DOWNTIME", info_down_var, RED),
]:
    row = tk.Frame(mid_info, bg=BG2)
    row.pack(anchor="w")
    tk.Label(row, text=f"{label:<10}", bg=BG2, fg=DIM,
        font=best_font(8)).pack(side="left")
    tk.Label(row, textvariable=var, bg=BG2, fg=color,
        font=best_font(8, True)).pack(side="left")

tk.Frame(info_bar, bg=DIM, width=1).pack(side="left", fill="y", pady=8)

right_info = tk.Frame(info_bar, bg=BG2)
right_info.pack(side="left", padx=16, pady=8)
for label, var in [("VENDOR", info_vendor_var), ("MAC", info_mac_var)]:
    row = tk.Frame(right_info, bg=BG2)
    row.pack(anchor="w")
    tk.Label(row, text=f"{label:<8}", bg=BG2, fg=DIM,
        font=best_font(8)).pack(side="left")
    tk.Label(row, textvariable=var, bg=BG2, fg=WHITE,
        font=best_font(8)).pack(side="left")

spark_mini = tk.Canvas(info_bar, width=200, height=70,
    bg=BG2, highlightthickness=0)
spark_mini.pack(side="right", padx=16, pady=8)

tk.Label(info_bar,
    text="◈ CLICK ROW TO INSPECT  //  DOUBLE-CLICK FOR FULL DETAIL",
    bg=BG2, fg=DIM, font=best_font(7)).pack(side="right", padx=8)

selected_ip = {"ip": None}

def update_info_bar(ip):
    selected_ip["ip"] = ip
    d_info = next((d for d in devices if d["ip"] == ip), {})
    with status_lock:
        s = dict(status.get(ip, {}))
    with history_lock:
        samples = list(latency_history.get(ip, []))
    alive = s.get("alive")
    info_ip_var.set(ip)
    info_status_var.set("▲ ONLINE" if alive else "▼ OFFLINE" if alive is False else "◈ INIT")
    info_lat_var.set(f"{s.get('latency') or '---'} ms")
    info_avg_var.set(f"{s.get('avg_latency') or '---'} ms")
    info_down_var.set(f"{s.get('downtime', 0)}s")
    info_vendor_var.set(d_info.get("vendor", ""))
    info_mac_var.set(d_info.get("mac", ""))
    draw_sparkline(spark_mini, samples, 200, 70, mini=True)

def refresh_info_bar():
    if selected_ip["ip"]:
        try:
            update_info_bar(selected_ip["ip"])
        except Exception:
            pass
    root.after(1000, refresh_info_bar)

# Detail popup
def open_detail_popup(ip):
    d_info = next((d for d in devices if d["ip"] == ip), {})

    popup = tk.Toplevel(root)
    popup.title(f"NetPyWiz  //  {ip}")
    popup.configure(bg=BG)
    popup.geometry("1000x640")
    popup.resizable(True, True)

    hdr = tk.Frame(popup, bg=BG2, height=48)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text=f"▓▓  {ip}",
        bg=BG2, fg=MAGENTA, font=best_font(14, True)).pack(side="left", padx=16, pady=8)
    tk.Label(hdr, text=d_info.get("hostname",""),
        bg=BG2, fg=CYAN, font=best_font(10)).pack(side="left", pady=8)
    if d_info.get("new_device"):
        tk.Label(hdr, text="★ NEW DEVICE",
            bg=BG2, fg=YELLOW, font=best_font(9, True)).pack(side="left", padx=12)
    tk.Label(hdr, text=d_info.get("vendor",""),
        bg=BG2, fg=DIM, font=best_font(9)).pack(side="right", padx=16, pady=8)
    tk.Frame(popup, bg=MAGENTA, height=1).pack(fill="x")

    body = tk.Frame(popup, bg=BG)
    body.pack(fill="both", expand=True, padx=16, pady=12)

    left  = tk.Frame(body, bg=BG)
    right = tk.Frame(body, bg=BG)
    left.pack(side="left",  fill="both", expand=True)
    right.pack(side="right", fill="both", expand=True, padx=(16,0))

    tk.Label(left, text="LATENCY HISTORY  (last 60s)",
        bg=BG, fg=CYAN, font=best_font(8, True)).pack(anchor="w")

    spark = tk.Canvas(left, width=320, height=140,
        bg=BG3, highlightthickness=1, highlightbackground=MAGENTA_DIM)
    spark.pack(fill="x", pady=(4,12))

    with history_lock:
        samples = list(latency_history.get(ip, []))
    draw_sparkline(spark, samples, 320, 140, mini=False)

    def refresh_spark():
        if not popup.winfo_exists():
            return
        with history_lock:
            s2 = list(latency_history.get(ip, []))
        draw_sparkline(spark, s2, 320, 140, mini=False)
        popup.after(1000, refresh_spark)

    popup.after(1000, refresh_spark)

    with status_lock:
        s = dict(status.get(ip, {}))

    total  = s.get("total_pings",  0)
    online = s.get("online_pings", 0)
    uptime = round((online / total * 100), 1) if total > 0 else 0
    alive  = s.get("alive")

    stats = [
        ("STATUS",      "▲ ONLINE" if alive else "▼ OFFLINE" if alive is False else "◈ INIT",
                         GREEN if alive else RED if alive is False else DIM),
        ("FIRST SEEN",  s.get("first_seen", "---"),  WHITE),
        ("LATENCY",     f"{s.get('latency') or '---'} ms",     CYAN),
        ("AVG LATENCY", f"{s.get('avg_latency') or '---'} ms", CYAN),
        ("DOWNTIME",    f"{s.get('downtime', 0)}s",  RED),
        ("UPTIME",      f"{uptime}%",                GREEN),
        ("MAC",         d_info.get("mac","---"),     WHITE),
        ("SW PORT",     d_info.get("port","---"),    AMBER),
    ]

    for label, val, col in stats:
        row = tk.Frame(left, bg=BG)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=f"{label:<14}", bg=BG, fg=DIM,
            font=best_font(8)).pack(side="left")
        tk.Label(row, text=val, bg=BG, fg=col,
            font=best_font(8, True)).pack(side="left")

    tk.Label(left, text="NOTES:", bg=BG, fg=DIM,
        font=best_font(8)).pack(anchor="w", pady=(12,2))
    notes_box = tk.Text(left, height=4, bg=BG3, fg=WHITE,
        insertbackground=CYAN, font=best_font(9),
        relief="flat", bd=0)
    notes_box.pack(fill="x")
    notes_box.insert("1.0", device_notes.get(ip, ""))

    def save_notes(event=None):
        device_notes[ip] = notes_box.get("1.0", "end-1c")
        for d in devices:
            if d["ip"] == ip:
                d["notes"] = device_notes[ip]

    notes_box.bind("<KeyRelease>", save_notes)

    # nmap panel
    tk.Label(right, text="NMAP SCAN",
        bg=BG, fg=CYAN, font=best_font(8, True)).pack(anchor="w")

    nmap_outer = tk.Frame(right, bg=BG3,
        highlightthickness=1, highlightbackground=MAGENTA_DIM)
    nmap_outer.pack(fill="both", expand=True, pady=(4,0))

    nmap_status_var = tk.StringVar(value="◈ SCANNING PORTS...")
    nmap_status_lbl = tk.Label(nmap_outer, textvariable=nmap_status_var,
        bg=BG3, fg=AMBER, font=best_font(8))
    nmap_status_lbl.pack(pady=8, padx=8, anchor="w")

    nmap_dot_var = tk.StringVar(value="")
    tk.Label(nmap_outer, textvariable=nmap_dot_var,
        bg=BG3, fg=MAGENTA, font=best_font(10)).pack(padx=8, anchor="w")

    nmap_scanning = {"active": True}

    def animate_nmap_dots():
        if not nmap_scanning["active"] or not popup.winfo_exists():
            nmap_dot_var.set("")
            return
        nmap_dot_var.set("█" * ((len(nmap_dot_var.get()) % 8) + 1))
        popup.after(200, animate_nmap_dots)

    popup.after(200, animate_nmap_dots)

    os_var = tk.StringVar(value="")
    tk.Label(nmap_outer, textvariable=os_var,
        bg=BG3, fg=MAGENTA, font=best_font(8, True),
        wraplength=300, justify="left").pack(padx=8, anchor="w")

    port_frame = tk.Frame(nmap_outer, bg=BG3)
    port_frame.pack(fill="both", expand=True, padx=8, pady=4)

    def run_nmap_thread():
        result = run_nmap(ip)
        if popup.winfo_exists():
            root.after(0, lambda: populate_nmap(result))

    def populate_nmap(result):
        nmap_scanning["active"] = False
        nmap_status_var.set("◈ SCAN COMPLETE")
        nmap_status_lbl.config(fg=GREEN)
        os_var.set(f"OS: {result['os_guess']}")

        if not result["ports"]:
            tk.Label(port_frame, text="NO OPEN PORTS FOUND",
                bg=BG3, fg=DIM, font=best_font(8)).pack(pady=8)
            return

        hrow = tk.Frame(port_frame, bg=BG3)
        hrow.pack(fill="x")
        for txt, w in [("PORT",7), ("PROTO",6), ("SERVICE",22)]:
            tk.Label(hrow, text=txt, width=w, bg=BG3, fg=CYAN,
                font=best_font(8, True), anchor="w").pack(side="left")

        tk.Frame(port_frame, bg=MAGENTA_DIM, height=1).pack(fill="x", pady=2)

        c  = tk.Canvas(port_frame, bg=BG3, highlightthickness=0)
        sb = ttk.Scrollbar(port_frame, orient="vertical", command=c.yview)
        inner = tk.Frame(c, bg=BG3)
        inner.bind("<Configure>",
            lambda e: c.configure(scrollregion=c.bbox("all")))
        c.create_window((0,0), window=inner, anchor="nw")
        c.configure(yscrollcommand=sb.set)
        c.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for p in result["ports"]:
            pr = tk.Frame(inner, bg=BG3)
            pr.pack(fill="x", pady=1)
            tk.Label(pr, text=p["port"],     width=7,  bg=BG3, fg=GREEN,
                font=best_font(8), anchor="w").pack(side="left")
            tk.Label(pr, text=p["protocol"], width=6,  bg=BG3, fg=DIM,
                font=best_font(8), anchor="w").pack(side="left")
            tk.Label(pr, text=p["service"],  width=22, bg=BG3, fg=WHITE,
                font=best_font(8), anchor="w").pack(side="left")

    threading.Thread(target=run_nmap_thread, daemon=True).start()

# ── Filter logic ─────────────────────────────────────────────────────────────
detached = set()

def apply_filter(*args):
    query = filter_var.get().strip().lower()
    if query == "filter devices...":
        query = ""
    for d in devices:
        ip = d["ip"]
        haystack = " ".join([
            ip,
            d.get("hostname", ""),
            d.get("vendor",   ""),
            d.get("mac",      ""),
            d.get("port",     ""),
        ]).lower()
        match = (query in haystack) if query else True
        if not match and ip not in detached:
            # Detach — tree.exists() is True here so safe to detach
            tree.detach(ip)
            detached.add(ip)
        elif match and ip in detached:
            # Reattach — detached items do NOT exist in tree
            # so we must use reattach not insert
            tree.reattach(ip, "", "end")
            detached.discard(ip)

filter_var.trace_add("write", apply_filter)

# ── Rescan logic ──────────────────────────────────────────────────────────────
rescan_running = threading.Event()

def do_rescan():
    if rescan_running.is_set():
        return
    rescan_running.set()
    rescan_btn.config(state="disabled", text="⟳  SCANNING...")
    status_bar.config(text="◈ RESCANNING SUBNET...", fg=AMBER)

    def rescan_thread():
        from scanner import scan_subnet
        found        = scan_subnet(subnet)
        existing_ips = {d["ip"] for d in devices}
        new_devs     = []

        for d in found:
            if d["ip"] not in existing_ips:
                d["port"]       = ""
                d["notes"]      = ""
                d["new_device"] = True
                new_devs.append(d)
                devices.append(d)
                with status_lock:
                    from monitor import ping_worker, history_lock
                    status[d["ip"]] = {
                        "alive": None, "latency": None,
                        "avg_latency": None, "downtime": 0,
                        "first_seen": None, "total_pings": 0,
                        "online_pings": 0
                    }
                    latency_history[d["ip"]] = []
                t = threading.Thread(target=ping_worker, args=(d["ip"],), daemon=True)
                t.start()
                root.after(0, lambda dev=d: add_device_row(dev))

        msg = (f"◈ RESCAN COMPLETE  //  {len(new_devs)} NEW DEVICE(S) FOUND"
               if new_devs else "◈ RESCAN COMPLETE  //  NO NEW DEVICES FOUND")
        col = GREEN if new_devs else DIM
        root.after(0, lambda: status_bar.config(text=msg, fg=col))
        root.after(0, lambda: rescan_btn.config(state="normal", text="⟳  RESCAN"))
        rescan_running.clear()

    threading.Thread(target=rescan_thread, daemon=True).start()

rescan_btn.config(command=do_rescan)

# Click handlers
def on_single_click(event):
    item = tree.identify_row(event.y)
    if not item:
        return
    update_info_bar(item)

def on_double_click(event):
    item = tree.identify_row(event.y)
    col  = tree.identify_column(event.x)
    if not item:
        return
    if col == "#6":
        current_val = tree.item(item)["values"][5]
        new_val = simpledialog.askstring(
            "Switch Port", f"Enter switch port for {item}:",
            initialvalue=current_val, parent=root)
        if new_val is not None:
            existing    = list(tree.item(item)["values"])
            existing[5] = new_val
            tree.item(item, values=existing)
            for d in devices:
                if d["ip"] == item:
                    d["port"] = new_val
        return
    open_detail_popup(item)

tree.bind("<Button-1>", on_single_click)
tree.bind("<Double-1>", on_double_click)

# Update loop
def update_table():
    with status_lock:
        current = dict(status)

    online = offline = pending = new_count = 0
    for ip, s in current.items():
        if not tree.exists(ip):
            continue
        d_info  = next((d for d in devices if d["ip"] == ip), {})
        is_new  = d_info.get("new_device", False)
        alive   = s.get("alive")

        if is_new:
            new_count += 1
            tag   = "new"
            label = "★ NEW"
            if alive is True:   online  += 1
            elif alive is False: offline += 1
            else:                pending += 1
        elif alive is None:
            tag, label = "unknown", "◈ INIT"
            pending += 1
        elif alive:
            tag, label = "green", "▲ ONLINE"
            online += 1
        else:
            tag, label = "red", "▼ OFFLINE"
            offline += 1

        existing = list(tree.item(ip)["values"])
        tree.item(ip, values=(
            label,
            existing[1], existing[2], existing[3], existing[4], existing[5],
            f"{s['latency']} ms"     if s.get("latency")     else "---",
            f"{s['avg_latency']} ms" if s.get("avg_latency") else "---",
            s.get("downtime", 0)
        ), tags=(tag,))

    online_var.set(f"▲ ONLINE:  {online}")
    offline_var.set(f"▼ OFFLINE:  {offline}")
    unknown_var.set(f"◈ PENDING:  {pending}")
    new_var.set(f"★ NEW:  {new_count}" if new_count else "")
    root.after(1000, update_table)

# Bottom bar
tk.Frame(root, bg=MAGENTA, height=1).pack(fill="x")
bottom = tk.Frame(root, bg=BG2, height=44)
bottom.pack(fill="x", side="bottom")
bottom.pack_propagate(False)

status_bar = tk.Label(bottom,
    text="◈ MONITORING ACTIVE",
    bg=BG2, fg=DIM, font=best_font(8), anchor="w")
status_bar.pack(side="left", padx=16)

def on_close():
    # Save window geometry for next launch
    save_config({"window_size": root.geometry().split("+")[0]})
    if tray_icon["instance"]:
        tray_icon["instance"].stop()
    if session_file["path"]:
        choice = ask_export_mode(root)
        if choice == "cancel":
            return
        path = export_to_desktop(devices, subnet=subnet,
            append_to=session_file["path"] if choice == "append" else None)
    else:
        path = export_to_desktop(devices, subnet=subnet)
    status_bar.config(text=f"◈ EXPORTED → {path}", fg=GREEN)
    root.after(1500, root.destroy)

root.protocol("WM_DELETE_WINDOW", on_close)

tk.Button(bottom, text="⏹  END SESSION + EXPORT",
    command=on_close,
    bg=BG3, fg=MAGENTA, font=best_font(9, True),
    relief="flat", cursor="hand2",
    activebackground=MAGENTA, activeforeground=BG, bd=0
).pack(side="right", padx=16, pady=8, ipadx=12)

# ── Tray Icon ─────────────────────────────────────────────────────────────────
tray_icon = {"instance": None}

def make_tray_image():
    from PIL import Image, ImageDraw
    img  = Image.new("RGB", (64, 64), "#0a0a0f")
    draw = ImageDraw.Draw(img)

    # Ethernet port body
    draw.rectangle([8, 14, 56, 50], outline="#ff00ff", width=2, fill="#1a1a2e")

    # 8 gold contact pins
    for i in range(8):
        x = 13 + i * 5
        draw.rectangle([x, 20, x+3, 36], fill="#ffaa00")

    # Latch tab at bottom
    draw.rectangle([20, 48, 44, 56], outline="#ff00ff", width=1, fill="#1a1a2e")

    # Cyan corner accents
    draw.rectangle([4,  4,  12, 12], fill="#00f5ff")
    draw.rectangle([52, 4,  60, 12], fill="#00f5ff")
    draw.rectangle([4,  52, 12, 60], fill="#00f5ff")
    draw.rectangle([52, 52, 60, 60], fill="#00f5ff")

    return img

def setup_tray():
    try:
        import pystray

        icon_img = make_tray_image()

        def show_window(icon, item):
            root.after(0, root.deiconify)
            root.after(0, root.lift)

        def exit_app(icon, item):
            root.after(0, on_close)

        menu = pystray.Menu(
            pystray.MenuItem("Show NetPyWiz", show_window, default=True),
            pystray.MenuItem("Exit + Export", exit_app)
        )

        icon = pystray.Icon("NetPyWiz", icon_img, "NetPyWiz Monitor", menu)
        tray_icon["instance"] = icon

        def on_minimize(event):
            if root.state() == "iconic":
                root.withdraw()
                icon.notify("NetPyWiz", "Still monitoring in the background.")

        root.bind("<Unmap>", on_minimize)
        threading.Thread(target=icon.run, daemon=True).start()

    except Exception as e:
        print(f"Tray icon unavailable: {e}")

# ── Launch ─────────────────────────────────────────────────────────────────────
threading.Thread(target=start_monitor, args=(devices,), daemon=True).start()
root.after(1000, update_table)
root.after(1000, refresh_info_bar)
root.after(500, setup_tray)
root.deiconify()

root.mainloop()
