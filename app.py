import tkinter as tk
from tkinter import ttk, simpledialog
import threading
import time
from monitor import start_monitor, status, status_lock, latency_history, history_lock
from exporter import export_to_desktop
from scanner import scan_subnet
from sparkline import draw_sparkline
from nmap_scan import run_nmap

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

# Detect best available font
def best_font(size=10, bold=False):
    weight = "bold" if bold else "normal"
    try:
        import tkinter.font as tkfont
        available = tkfont.families()
        for name in ["JetBrains Mono", "Fira Mono", "DejaVu Sans Mono", "Courier New"]:
            if name in available:
                return (name, size, weight)
    except Exception:
        pass
    return ("Courier New", size, weight)

device_notes = {}

# ── Subnet Dialog ─────────────────────────────────────────────────────────────
def ask_subnet():
    dialog = tk.Tk()
    dialog.title("NetPyWiz")
    dialog.configure(bg=BG)
    dialog.geometry("500x280")
    dialog.resizable(False, False)
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 250
    y = (dialog.winfo_screenheight() // 2) - 140
    dialog.geometry(f"+{x}+{y}")
    result = {"subnet": None}

    tk.Label(dialog, text="▓▓ NETPYWIZ // NETWORK MONITOR ▓▓",
        bg=BG, fg=MAGENTA, font=best_font(13, True)).pack(pady=(28,4))
    tk.Label(dialog, text="INITIALIZE SUBNET SCAN",
        bg=BG, fg=CYAN, font=best_font(9)).pack()
    tk.Frame(dialog, bg=MAGENTA, height=1).pack(fill="x", padx=30, pady=14)
    tk.Label(dialog, text="TARGET SUBNET  (CIDR notation)",
        bg=BG, fg=DIM, font=best_font(8)).pack()

    entry_var = tk.StringVar(value="192.168.1.0/24")
    entry = tk.Entry(dialog, textvariable=entry_var,
        bg=BG3, fg=CYAN, insertbackground=CYAN, selectbackground=MAGENTA,
        font=best_font(13), relief="flat", justify="center", bd=0)
    entry.pack(padx=50, pady=10, ipady=8, fill="x")
    entry.select_range(0, "end")
    entry.focus()
    tk.Frame(dialog, bg=CYAN, height=1).pack(fill="x", padx=50)

    def confirm(event=None):
        result["subnet"] = entry_var.get().strip()
        dialog.destroy()

    entry.bind("<Return>",   confirm)
    entry.bind("<KP_Enter>", confirm)
    tk.Button(dialog, text="► INITIATE SCAN", command=confirm,
        bg=MAGENTA_DIM, fg=BG, font=best_font(11, True),
        relief="flat", cursor="hand2",
        activebackground=MAGENTA, activeforeground=BG, bd=0
    ).pack(pady=16, ipadx=20, ipady=6)

    dialog.mainloop()
    return result["subnet"]

# ── Splash scan ───────────────────────────────────────────────────────────────
subnet = ask_subnet()
if not subnet:
    import sys; sys.exit()

splash = tk.Tk()
splash.title("NetPyWiz")
splash.configure(bg=BG)
splash.geometry("400x160")
splash.resizable(False, False)
splash.update_idletasks()
x = (splash.winfo_screenwidth() // 2) - 200
y = (splash.winfo_screenheight() // 2) - 80
splash.geometry(f"+{x}+{y}")

tk.Label(splash, text="▓▓ NETPYWIZ ▓▓",
    bg=BG, fg=MAGENTA, font=best_font(14, True)).pack(pady=(24,4))
tk.Label(splash, text=f"SCANNING  {subnet} ...",
    bg=BG, fg=CYAN, font=best_font(10)).pack()
tk.Label(splash, text="THIS MAY TAKE UP TO 30 SECONDS",
    bg=BG, fg=DIM, font=best_font(8)).pack(pady=4)

dot_var = tk.StringVar(value="")
tk.Label(splash, textvariable=dot_var, bg=BG, fg=MAGENTA,
    font=best_font(12)).pack()

devices   = []
scan_done = threading.Event()

def run_scan():
    global devices
    devices = scan_subnet(subnet)
    for d in devices:
        d["port"]  = ""
        d["notes"] = ""
    scan_done.set()

def animate_dots():
    if scan_done.is_set():
        splash.destroy()
        return
    dot_var.set("█" * ((len(dot_var.get()) % 8) + 1))
    splash.after(200, animate_dots)

threading.Thread(target=run_scan, daemon=True).start()
splash.after(200, animate_dots)

def check_scan_done():
    if scan_done.is_set():
        splash.destroy()
    else:
        splash.after(300, check_scan_done)

splash.after(300, check_scan_done)
splash.mainloop()

if not devices:
    import sys
    tk.Tk().withdraw()
    from tkinter import messagebox
    messagebox.showerror("NetPyWiz", f"No devices found on {subnet}")
    sys.exit()

# ── Main Window ───────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("NetPyWiz — Network Monitor")
root.configure(bg=BG)
root.geometry("1280x760")
root.minsize(900, 600)

# ── Header ────────────────────────────────────────────────────────────────────
header = tk.Frame(root, bg=BG2, height=56)
header.pack(fill="x")
header.pack_propagate(False)

# Ethernet port logo drawn on canvas
logo_canvas = tk.Canvas(header, width=38, height=38,
    bg=BG2, highlightthickness=0)
logo_canvas.pack(side="left", padx=(14,4), pady=8)

def draw_eth_logo(c):
    # Outer rectangle — ethernet port body
    c.create_rectangle(4, 8, 34, 32, outline=MAGENTA, width=2, fill=BG3)
    # Gold contact pins inside
    pin_colors = [AMBER, AMBER, AMBER, AMBER, AMBER, AMBER, AMBER, AMBER]
    for i, col in enumerate(pin_colors):
        x = 7 + i * 3.5
        c.create_rectangle(x, 12, x+2, 24, fill=col, outline="")
    # Latch tab at bottom
    c.create_rectangle(11, 30, 27, 35, outline=MAGENTA, width=1, fill=BG3)

draw_eth_logo(logo_canvas)

tk.Label(header, text="NETPYWIZ",
    bg=BG2, fg=MAGENTA, font=best_font(18, True)).pack(side="left", pady=10)
tk.Label(header, text="// NETWORK MONITOR",
    bg=BG2, fg=CYAN, font=best_font(12)).pack(side="left", padx=8, pady=10)

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

# ── Stats bar ─────────────────────────────────────────────────────────────────
stats_frame = tk.Frame(root, bg=BG2)
stats_frame.pack(fill="x")

online_var  = tk.StringVar(value="▲ ONLINE:  0")
offline_var = tk.StringVar(value="▼ OFFLINE:  0")
unknown_var = tk.StringVar(value="◈ PENDING:  0")

for var, color in [(online_var, GREEN), (offline_var, RED), (unknown_var, DIM)]:
    tk.Label(stats_frame, textvariable=var, bg=BG2, fg=color,
        font=best_font(9, True)).pack(side="left", padx=20, pady=4)

tk.Frame(root, bg=CYAN, height=1).pack(fill="x")

# ── Table ─────────────────────────────────────────────────────────────────────
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

# Font-only color tags — no background highlight
tree.tag_configure("green",   background=BG3, foreground=GREEN)
tree.tag_configure("red",     background=BG3, foreground=RED)
tree.tag_configure("unknown", background=BG3, foreground=DIM)
tree.tag_configure("selected_green", background="#16162a", foreground=GREEN)
tree.tag_configure("selected_red",   background="#16162a", foreground=RED)
tree.tag_configure("selected_unk",   background="#16162a", foreground=DIM)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
tree.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

for d in devices:
    tree.insert("", "end", iid=d["ip"], values=(
        "◈ INIT", d["ip"], d["mac"], d["hostname"],
        d["vendor"], "", "", "", "0"
    ), tags=("unknown",))

# ── Info bar — single click populates this ────────────────────────────────────
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

# Left block — IP + status
left_info = tk.Frame(info_bar, bg=BG2)
left_info.pack(side="left", padx=16, pady=8)

tk.Label(left_info, textvariable=info_ip_var,
    bg=BG2, fg=MAGENTA, font=best_font(14, True)).pack(anchor="w")
tk.Label(left_info, textvariable=info_status_var,
    bg=BG2, fg=GREEN, font=best_font(9)).pack(anchor="w")

tk.Frame(info_bar, bg=DIM, width=1).pack(side="left", fill="y", pady=8)

# Mid block — latency stats
mid_info = tk.Frame(info_bar, bg=BG2)
mid_info.pack(side="left", padx=16, pady=8)

for label, var, color in [
    ("LATENCY", info_lat_var, CYAN),
    ("AVG",     info_avg_var, CYAN),
    ("DOWNTIME",info_down_var, RED),
]:
    row = tk.Frame(mid_info, bg=BG2)
    row.pack(anchor="w")
    tk.Label(row, text=f"{label:<10}", bg=BG2, fg=DIM,
        font=best_font(8)).pack(side="left")
    tk.Label(row, textvariable=var, bg=BG2, fg=color,
        font=best_font(8, True)).pack(side="left")

tk.Frame(info_bar, bg=DIM, width=1).pack(side="left", fill="y", pady=8)

# Right block — device info
right_info = tk.Frame(info_bar, bg=BG2)
right_info.pack(side="left", padx=16, pady=8)

for label, var in [("VENDOR", info_vendor_var), ("MAC", info_mac_var)]:
    row = tk.Frame(right_info, bg=BG2)
    row.pack(anchor="w")
    tk.Label(row, text=f"{label:<8}", bg=BG2, fg=DIM,
        font=best_font(8)).pack(side="left")
    tk.Label(row, textvariable=var, bg=BG2, fg=WHITE,
        font=best_font(8)).pack(side="left")

# Mini sparkline in info bar
spark_mini = tk.Canvas(info_bar, width=200, height=70,
    bg=BG2, highlightthickness=0)
spark_mini.pack(side="right", padx=16, pady=8)

tk.Label(info_bar, text="◈ CLICK ROW TO INSPECT  //  DOUBLE-CLICK FOR FULL DETAIL",
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
        update_info_bar(selected_ip["ip"])
    root.after(1000, refresh_info_bar)

root.after(1000, refresh_info_bar)

# ── Full detail popup ─────────────────────────────────────────────────────────
def open_detail_popup(ip):
    d_info = next((d for d in devices if d["ip"] == ip), {})

    popup = tk.Toplevel(root)
    popup.title(f"NetPyWiz  //  {ip}")
    popup.configure(bg=BG)
    popup.geometry("1000x640")
    popup.resizable(True, True)

    # Header
    hdr = tk.Frame(popup, bg=BG2, height=48)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text=f"▓▓  {ip}",
        bg=BG2, fg=MAGENTA, font=best_font(14, True)).pack(side="left", padx=16, pady=8)
    tk.Label(hdr, text=d_info.get("hostname",""),
        bg=BG2, fg=CYAN, font=best_font(10)).pack(side="left", pady=8)
    tk.Label(hdr, text=d_info.get("vendor",""),
        bg=BG2, fg=DIM, font=best_font(9)).pack(side="right", padx=16, pady=8)
    tk.Frame(popup, bg=MAGENTA, height=1).pack(fill="x")

    body = tk.Frame(popup, bg=BG)
    body.pack(fill="both", expand=True, padx=16, pady=12)

    left  = tk.Frame(body, bg=BG)
    right = tk.Frame(body, bg=BG)
    left.pack(side="left",  fill="both", expand=True)
    right.pack(side="right", fill="both", expand=True, padx=(16,0))

    # Sparkline
    tk.Label(left, text="LATENCY HISTORY  (last 60s)",
        bg=BG, fg=CYAN, font=best_font(8, True)).pack(anchor="w")

    spark = tk.Canvas(left, width=320, height=140,
        bg=BG3, highlightthickness=1, highlightbackground=MAGENTA_DIM)
    spark.pack(fill="x", pady=(4,12))

    with history_lock:
        samples = list(latency_history.get(ip, []))
    draw_sparkline(spark, samples, 320, 140, mini=False)

    # Live refresh sparkline every second
    def refresh_spark():
        if not popup.winfo_exists():
            return
        with history_lock:
            s2 = list(latency_history.get(ip, []))
        draw_sparkline(spark, s2, 320, 140, mini=False)
        popup.after(1000, refresh_spark)

    popup.after(1000, refresh_spark)

    # Stats
    with status_lock:
        s = dict(status.get(ip, {}))

    total  = s.get("total_pings",  0)
    online = s.get("online_pings", 0)
    uptime = round((online / total * 100), 1) if total > 0 else 0

    alive = s.get("alive")
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

    # Notes
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
    nmap_dot_lbl = tk.Label(nmap_outer, textvariable=nmap_dot_var,
        bg=BG3, fg=MAGENTA, font=best_font(10))
    nmap_dot_lbl.pack(padx=8, anchor="w")

    nmap_scanning = {"active": True}

    def animate_nmap_dots():
        if not nmap_scanning["active"]:
            nmap_dot_var.set("")
            return
        if not popup.winfo_exists():
            return
        current = nmap_dot_var.get()
        nmap_dot_var.set("█" * ((len(current) % 8) + 1))
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

        # Column headers
        hrow = tk.Frame(port_frame, bg=BG3)
        hrow.pack(fill="x")
        for txt, w in [("PORT",7), ("PROTO",6), ("SERVICE",22)]:
            tk.Label(hrow, text=txt, width=w, bg=BG3, fg=CYAN,
                font=best_font(8, True), anchor="w").pack(side="left")

        tk.Frame(port_frame, bg=MAGENTA_DIM, height=1).pack(fill="x", pady=2)

        # Scrollable list
        c = tk.Canvas(port_frame, bg=BG3, highlightthickness=0)
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

# ── Click handlers ─────────────────────────────────────────────────────────────
last_selected = {"ip": None}

def on_single_click(event):
    item = tree.identify_row(event.y)
    if not item:
        return
    update_info_bar(item)
    last_selected["ip"] = item

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

tree.bind("<Button-1>",  on_single_click)
tree.bind("<Double-1>",  on_double_click)

# ── Update loop ────────────────────────────────────────────────────────────────
def update_table():
    with status_lock:
        current = dict(status)

    online = offline = pending = 0
    for ip, s in current.items():
        if not tree.exists(ip):
            continue
        alive = s.get("alive")
        if alive is None:
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
    root.after(1000, update_table)

# ── Bottom bar ─────────────────────────────────────────────────────────────────
tk.Frame(root, bg=MAGENTA, height=1).pack(fill="x")
bottom = tk.Frame(root, bg=BG2, height=44)
bottom.pack(fill="x", side="bottom")
bottom.pack_propagate(False)

status_bar = tk.Label(bottom,
    text="◈ MONITORING ACTIVE",
    bg=BG2, fg=DIM, font=best_font(8), anchor="w")
status_bar.pack(side="left", padx=16)

def on_close():
    path = export_to_desktop(devices)
    status_bar.config(text=f"◈ EXPORTED → {path}", fg=GREEN)
    root.after(1500, root.destroy)

root.protocol("WM_DELETE_WINDOW", on_close)

tk.Button(bottom, text="⏹  END SESSION + EXPORT",
    command=on_close,
    bg=BG3, fg=MAGENTA, font=best_font(9, True),
    relief="flat", cursor="hand2",
    activebackground=MAGENTA, activeforeground=BG, bd=0
).pack(side="right", padx=16, pady=8, ipadx=12)

# ── Launch ─────────────────────────────────────────────────────────────────────
threading.Thread(target=start_monitor, args=(devices,), daemon=True).start()
root.after(1000, update_table)
root.after(1000, refresh_info_bar)
root.mainloop()
