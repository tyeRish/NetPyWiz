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

# ── Notes storage — persists for session ──────────────────────────────────────
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
        bg=BG, fg=MAGENTA, font=("Courier New", 13, "bold")).pack(pady=(28,4))
    tk.Label(dialog, text="INITIALIZE SUBNET SCAN",
        bg=BG, fg=CYAN, font=("Courier New", 9)).pack()
    tk.Frame(dialog, bg=MAGENTA, height=1).pack(fill="x", padx=30, pady=14)
    tk.Label(dialog, text="TARGET SUBNET  (CIDR notation)",
        bg=BG, fg=DIM, font=("Courier New", 8)).pack()

    entry_var = tk.StringVar(value="192.168.1.0/24")
    entry = tk.Entry(dialog, textvariable=entry_var,
        bg=BG3, fg=CYAN, insertbackground=CYAN, selectbackground=MAGENTA,
        font=("Courier New", 13), relief="flat", justify="center", bd=0)
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
        bg=MAGENTA_DIM, fg=BG, font=("Courier New", 11, "bold"),
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
    bg=BG, fg=MAGENTA, font=("Courier New", 14, "bold")).pack(pady=(24,4))
tk.Label(splash, text=f"SCANNING  {subnet} ...",
    bg=BG, fg=CYAN, font=("Courier New", 10)).pack()
tk.Label(splash, text="THIS MAY TAKE UP TO 30 SECONDS",
    bg=BG, fg=DIM, font=("Courier New", 8)).pack(pady=4)

dot_var  = tk.StringVar(value="")
dot_label= tk.Label(splash, textvariable=dot_var, bg=BG, fg=MAGENTA,
    font=("Courier New", 12))
dot_label.pack()

devices   = []
scan_done = threading.Event()

def run_scan():
    global devices
    devices = scan_subnet(subnet)
    for d in devices:
        d["port"] = ""
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
root.geometry("1280x720")
root.minsize(900, 500)

# Header
header = tk.Frame(root, bg=BG2, height=56)
header.pack(fill="x")
header.pack_propagate(False)

tk.Label(header, text="▓▓ NETPYWIZ",
    bg=BG2, fg=MAGENTA, font=("Courier New", 18, "bold")).pack(side="left", padx=20, pady=10)
tk.Label(header, text="// NETWORK MONITOR",
    bg=BG2, fg=CYAN, font=("Courier New", 12)).pack(side="left", pady=10)

clock_var = tk.StringVar()
tk.Label(header, textvariable=clock_var,
    bg=BG2, fg=DIM, font=("Courier New", 10)).pack(side="right", padx=20)
tk.Label(header, text=f"◈  {subnet}  ◈  {len(devices)} DEVICES",
    bg=BG2, fg=AMBER, font=("Courier New", 9)).pack(side="right", padx=10)

def tick():
    clock_var.set(time.strftime("◈  %Y-%m-%d  %H:%M:%S"))
    root.after(1000, tick)
tick()

tk.Frame(root, bg=MAGENTA, height=2).pack(fill="x")

# Stats bar
stats_frame = tk.Frame(root, bg=BG2)
stats_frame.pack(fill="x")

online_var  = tk.StringVar(value="● ONLINE:  0")
offline_var = tk.StringVar(value="● OFFLINE:  0")
unknown_var = tk.StringVar(value="◈ PENDING:  0")

for var, color in [(online_var, GREEN), (offline_var, RED), (unknown_var, DIM)]:
    tk.Label(stats_frame, textvariable=var, bg=BG2, fg=color,
        font=("Courier New", 9, "bold")).pack(side="left", padx=20, pady=4)

tk.Frame(root, bg=CYAN, height=1).pack(fill="x")

# Table
table_frame = tk.Frame(root, bg=BG)
table_frame.pack(fill="both", expand=True)

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview",
    background=BG3, foreground=WHITE, fieldbackground=BG3,
    rowheight=30, font=("Courier New", 10), borderwidth=0)
style.configure("Treeview.Heading",
    background=BG2, foreground=CYAN,
    font=("Courier New", 9, "bold"), relief="flat", borderwidth=0)
style.map("Treeview",
    background=[("selected", "#2a2a4a")],
    foreground=[("selected", CYAN)])
style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

columns = ("status","ip","mac","hostname","vendor","port","latency","avg_latency","downtime")
tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

col_defs = {
    "status":      ("STATUS",      80),
    "ip":          ("IP ADDRESS", 130),
    "mac":         ("MAC ADDRESS",155),
    "hostname":    ("HOSTNAME",   200),
    "vendor":      ("VENDOR",     160),
    "port":        ("SW PORT",    100),
    "latency":     ("LAT ms",      80),
    "avg_latency": ("AVG ms",      80),
    "downtime":    ("DOWN s",      80),
}

for col, (label, width) in col_defs.items():
    tree.heading(col, text=label)
    tree.column(col, width=width,
        anchor="center" if col in ("status","port","latency","avg_latency","downtime") else "w")

tree.tag_configure("green",   background="#001a0f", foreground=GREEN)
tree.tag_configure("red",     background="#1a000a", foreground=RED)
tree.tag_configure("unknown", background=BG3,       foreground=DIM)
tree.tag_configure("inline",  background="#0f0f2a", foreground=DIM)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
tree.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

for d in devices:
    tree.insert("", "end", iid=d["ip"], values=(
        "INIT...", d["ip"], d["mac"], d["hostname"],
        d["vendor"], "", "", "", "0"
    ), tags=("unknown",))

# ── Inline expansion ──────────────────────────────────────────────────────────
# We insert a fake row below the selected device that acts as an info panel.
# It contains a mini sparkline canvas embedded via a window.
expanded_ip     = None
inline_canvas   = None
inline_frame_id = None
inline_iid      = "__inline_panel__"

def collapse_inline():
    global expanded_ip, inline_canvas, inline_frame_id
    if tree.exists(inline_iid):
        tree.delete(inline_iid)
    expanded_ip     = None
    inline_canvas   = None
    inline_frame_id = None

def expand_inline(ip: str):
    global expanded_ip, inline_canvas

    # Collapse if already open
    if expanded_ip == ip:
        collapse_inline()
        return

    collapse_inline()
    expanded_ip = ip

    # Insert fake row directly below the selected device
    try:
        idx = tree.index(ip)
        tree.insert("", idx + 1, iid=inline_iid,
            values=("", "", "", "", "", "", "", "", ""),
            tags=("inline",))
    except Exception:
        return

    # Build a frame to embed in the fake row
    frame = tk.Frame(tree, bg="#0f0f2a", pady=6)

    # Mini sparkline
    spark_canvas = tk.Canvas(frame, width=220, height=60,
        bg="#0f0f2a", highlightthickness=0)
    spark_canvas.pack(side="left", padx=(12,8))
    inline_canvas = spark_canvas

    # Quick stats
    with status_lock:
        s = dict(status.get(ip, {}))

    info_frame = tk.Frame(frame, bg="#0f0f2a")
    info_frame.pack(side="left", padx=8)

    alive = s.get("alive")
    status_str = "● ONLINE" if alive else "● OFFLINE" if alive is False else "◈ INIT"
    status_col = GREEN if alive else RED if alive is False else DIM

    tk.Label(info_frame, text=status_str, bg="#0f0f2a", fg=status_col,
        font=("Courier New", 9, "bold")).grid(row=0, column=0, sticky="w")
    tk.Label(info_frame, text=f"LATENCY:  {s.get('latency') or '---'} ms",
        bg="#0f0f2a", fg=CYAN, font=("Courier New", 8)).grid(row=1, column=0, sticky="w")
    tk.Label(info_frame, text=f"AVG:      {s.get('avg_latency') or '---'} ms",
        bg="#0f0f2a", fg=CYAN, font=("Courier New", 8)).grid(row=2, column=0, sticky="w")
    tk.Label(info_frame, text=f"DOWNTIME: {s.get('downtime', 0)}s",
        bg="#0f0f2a", fg=RED, font=("Courier New", 8)).grid(row=3, column=0, sticky="w")

    # Notes field
    notes_frame = tk.Frame(frame, bg="#0f0f2a")
    notes_frame.pack(side="left", padx=16)
    tk.Label(notes_frame, text="NOTES:", bg="#0f0f2a", fg=DIM,
        font=("Courier New", 7)).pack(anchor="w")
    notes_text = tk.Text(notes_frame, width=30, height=3,
        bg=BG3, fg=WHITE, insertbackground=CYAN,
        font=("Courier New", 8), relief="flat", bd=0)
    notes_text.pack()
    notes_text.insert("1.0", device_notes.get(ip, ""))

    def save_notes(event=None):
        device_notes[ip] = notes_text.get("1.0", "end-1c")
        for d in devices:
            if d["ip"] == ip:
                d["notes"] = device_notes[ip]

    notes_text.bind("<KeyRelease>", save_notes)

    tk.Label(notes_frame, text="DOUBLE-CLICK ROW FOR FULL DETAIL",
        bg="#0f0f2a", fg=DIM, font=("Courier New", 7)).pack(anchor="w", pady=(4,0))

    # Embed frame into the tree row
    tree.item(inline_iid, values=("", "", "", "", "", "", "", "", ""))
    tree.set_row_height = lambda: None
    style.configure("Treeview", rowheight=30)
    frame_id = tree.tag_configure("inline")
    tree_frame_window = tree.insert
    canvas_id = tree.item(inline_iid)

    # Use a window item in the treeview
    frame.update_idletasks()
    tree.tag_configure("inline", background="#0f0f2a")

    # Draw initial sparkline
    with history_lock:
        samples = list(latency_history.get(ip, []))
    draw_sparkline(spark_canvas, samples, 220, 60, mini=True)

    # Embed the frame as a Treeview window
    tree_window = tk.Canvas(tree, width=tree.winfo_width(), height=80,
        bg="#0f0f2a", highlightthickness=0)
    frame.pack(in_=tree_window, fill="both", expand=True)
    tree.item(inline_iid, tags=("inline",))

    global inline_frame_id
    inline_frame_id = tree.tag_configure

    # Attach frame to row using place — positioned under selected row
    tree.update_idletasks()
    bbox = tree.bbox(ip)
    if bbox:
        tree_window.place(x=0, y=bbox[1] + bbox[3], width=tree.winfo_width(), height=80)
    else:
        tree_window.place(x=0, y=0, width=tree.winfo_width(), height=80)

    # Update sparkline every second
    def refresh_spark():
        if not tree.exists(inline_iid) or expanded_ip != ip:
            return
        with history_lock:
            s2 = list(latency_history.get(ip, []))
        draw_sparkline(spark_canvas, s2, 220, 60, mini=True)
        root.after(1000, refresh_spark)

    root.after(1000, refresh_spark)

# ── Full detail popup ─────────────────────────────────────────────────────────
def open_detail_popup(ip: str):
    d_info = next((d for d in devices if d["ip"] == ip), {})

    popup = tk.Toplevel(root)
    popup.title(f"NetPyWiz  //  {ip}")
    popup.configure(bg=BG)
    popup.geometry("720x580")
    popup.resizable(True, True)

    # Header
    hdr = tk.Frame(popup, bg=BG2, height=48)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    tk.Label(hdr, text=f"▓▓  {ip}",
        bg=BG2, fg=MAGENTA, font=("Courier New", 14, "bold")).pack(side="left", padx=16, pady=8)
    tk.Label(hdr, text=d_info.get("hostname",""),
        bg=BG2, fg=CYAN, font=("Courier New", 10)).pack(side="left", pady=8)
    tk.Label(hdr, text=d_info.get("vendor",""),
        bg=BG2, fg=DIM, font=("Courier New", 9)).pack(side="right", padx=16, pady=8)
    tk.Frame(popup, bg=MAGENTA, height=1).pack(fill="x")

    # Body — two columns
    body = tk.Frame(popup, bg=BG)
    body.pack(fill="both", expand=True, padx=16, pady=12)

    left  = tk.Frame(body, bg=BG)
    right = tk.Frame(body, bg=BG)
    left.pack(side="left",  fill="both", expand=True)
    right.pack(side="right", fill="both", expand=True, padx=(16,0))

    # ── Left: sparkline + stats ───────────────────────────────────────────────
    tk.Label(left, text="LATENCY HISTORY  (last 60s)",
        bg=BG, fg=CYAN, font=("Courier New", 8, "bold")).pack(anchor="w")

    spark = tk.Canvas(left, width=320, height=140,
        bg=BG3, highlightthickness=1, highlightbackground=MAGENTA_DIM)
    spark.pack(fill="x", pady=(4,12))

    with history_lock:
        samples = list(latency_history.get(ip, []))
    draw_sparkline(spark, samples, 320, 140, mini=False)

    # Stats grid
    with status_lock:
        s = dict(status.get(ip, {}))

    total   = s.get("total_pings",  0)
    online  = s.get("online_pings", 0)
    uptime  = round((online / total * 100), 1) if total > 0 else 0

    stats = [
        ("STATUS",       "● ONLINE" if s.get("alive") else "● OFFLINE", GREEN if s.get("alive") else RED),
        ("FIRST SEEN",   s.get("first_seen", "---"),  WHITE),
        ("LATENCY",      f"{s.get('latency') or '---'} ms", CYAN),
        ("AVG LATENCY",  f"{s.get('avg_latency') or '---'} ms", CYAN),
        ("DOWNTIME",     f"{s.get('downtime', 0)}s",  RED),
        ("UPTIME",       f"{uptime}%",                GREEN),
        ("MAC",          d_info.get("mac","---"),     WHITE),
        ("SW PORT",      d_info.get("port","---"),    AMBER),
    ]

    for label, val, col in stats:
        row = tk.Frame(left, bg=BG)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=f"{label:<14}", bg=BG, fg=DIM,
            font=("Courier New", 8)).pack(side="left")
        tk.Label(row, text=val, bg=BG, fg=col,
            font=("Courier New", 8, "bold")).pack(side="left")

    # Notes
    tk.Label(left, text="NOTES:", bg=BG, fg=DIM,
        font=("Courier New", 8), pady=(12,0)).pack(anchor="w", pady=(12,2))
    notes_box = tk.Text(left, height=4, bg=BG3, fg=WHITE,
        insertbackground=CYAN, font=("Courier New", 9),
        relief="flat", bd=0)
    notes_box.pack(fill="x")
    notes_box.insert("1.0", device_notes.get(ip, ""))

    def save_notes_popup(event=None):
        device_notes[ip] = notes_box.get("1.0", "end-1c")
        for d in devices:
            if d["ip"] == ip:
                d["notes"] = device_notes[ip]

    notes_box.bind("<KeyRelease>", save_notes_popup)

    # ── Right: nmap ───────────────────────────────────────────────────────────
    tk.Label(right, text="NMAP SCAN",
        bg=BG, fg=CYAN, font=("Courier New", 8, "bold")).pack(anchor="w")

    nmap_frame = tk.Frame(right, bg=BG3,
        highlightthickness=1, highlightbackground=MAGENTA_DIM)
    nmap_frame.pack(fill="both", expand=True, pady=(4,0))

    nmap_status = tk.Label(nmap_frame,
        text="◈ SCANNING PORTS...  THIS MAY TAKE 30-60 SECONDS",
        bg=BG3, fg=AMBER, font=("Courier New", 8))
    nmap_status.pack(pady=20)

    os_var = tk.StringVar(value="")
    tk.Label(nmap_frame, textvariable=os_var,
        bg=BG3, fg=MAGENTA, font=("Courier New", 8, "bold"),
        wraplength=280, justify="left").pack(padx=8, anchor="w")

    port_list = tk.Frame(nmap_frame, bg=BG3)
    port_list.pack(fill="both", expand=True, padx=8, pady=4)

    def run_nmap_thread():
        result = run_nmap(ip)
        root.after(0, lambda: populate_nmap(result))

    def populate_nmap(result):
        nmap_status.destroy()
        os_var.set(f"OS: {result['os_guess']}")

        if not result["ports"]:
            tk.Label(port_list, text="NO OPEN PORTS FOUND",
                bg=BG3, fg=DIM, font=("Courier New", 8)).pack(pady=8)
            return

        # Header
        hrow = tk.Frame(port_list, bg=BG3)
        hrow.pack(fill="x")
        for txt, w in [("PORT", 60), ("PROTO", 50), ("SERVICE", 180)]:
            tk.Label(hrow, text=txt, width=w//7, bg=BG3, fg=CYAN,
                font=("Courier New", 8, "bold"), anchor="w").pack(side="left")

        tk.Frame(port_list, bg=MAGENTA_DIM, height=1).pack(fill="x", pady=2)

        # Scrollable port list
        canvas_ports = tk.Canvas(port_list, bg=BG3, highlightthickness=0)
        scroll_ports = ttk.Scrollbar(port_list, orient="vertical",
            command=canvas_ports.yview)
        ports_inner  = tk.Frame(canvas_ports, bg=BG3)

        ports_inner.bind("<Configure>",
            lambda e: canvas_ports.configure(
                scrollregion=canvas_ports.bbox("all")))

        canvas_ports.create_window((0,0), window=ports_inner, anchor="nw")
        canvas_ports.configure(yscrollcommand=scroll_ports.set)
        canvas_ports.pack(side="left", fill="both", expand=True)
        scroll_ports.pack(side="right", fill="y")

        for p in result["ports"]:
            prow = tk.Frame(ports_inner, bg=BG3)
            prow.pack(fill="x", pady=1)
            tk.Label(prow, text=p["port"], width=6, bg=BG3, fg=GREEN,
                font=("Courier New", 8), anchor="w").pack(side="left")
            tk.Label(prow, text=p["protocol"], width=5, bg=BG3, fg=DIM,
                font=("Courier New", 8), anchor="w").pack(side="left")
            tk.Label(prow, text=p["service"], bg=BG3, fg=WHITE,
                font=("Courier New", 8), anchor="w").pack(side="left")

    threading.Thread(target=run_nmap_thread, daemon=True).start()

    # Refresh sparkline every second while popup is open
    def refresh_popup_spark():
        if not popup.winfo_exists():
            return
        with history_lock:
            s2 = list(latency_history.get(ip, []))
        draw_sparkline(spark, s2, 320, 140, mini=False)
        popup.after(1000, refresh_popup_spark)

    popup.after(1000, refresh_popup_spark)

# ── Click handlers ─────────────────────────────────────────────────────────────
def on_single_click(event):
    item = tree.identify_row(event.y)
    if not item or item == inline_iid:
        return
    expand_inline(item)

def on_double_click(event):
    item = tree.identify_row(event.y)
    col  = tree.identify_column(event.x)
    if not item or item == inline_iid:
        return

    # Double click on SW PORT column = edit port
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

    # Double click anywhere else = full detail popup
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
            tag, label = "green", "● ONLINE"
            online += 1
        else:
            tag, label = "red", "● OFFLINE"
            offline += 1

        existing = list(tree.item(ip)["values"])
        tree.item(ip, values=(
            label,
            existing[1], existing[2], existing[3], existing[4], existing[5],
            f"{s['latency']} ms"     if s.get("latency")     else "---",
            f"{s['avg_latency']} ms" if s.get("avg_latency") else "---",
            s.get("downtime", 0)
        ), tags=(tag,))

    online_var.set(f"● ONLINE:  {online}")
    offline_var.set(f"● OFFLINE:  {offline}")
    unknown_var.set(f"◈ PENDING:  {pending}")
    root.after(1000, update_table)

# ── Bottom bar ─────────────────────────────────────────────────────────────────
tk.Frame(root, bg=MAGENTA, height=1).pack(fill="x")
bottom = tk.Frame(root, bg=BG2, height=44)
bottom.pack(fill="x", side="bottom")
bottom.pack_propagate(False)

status_bar = tk.Label(bottom,
    text="◈ CLICK ROW = EXPAND  //  DOUBLE-CLICK = DETAIL POPUP  //  DOUBLE-CLICK SW PORT = EDIT",
    bg=BG2, fg=DIM, font=("Courier New", 8), anchor="w")
status_bar.pack(side="left", padx=16)

def on_close():
    path = export_to_desktop(devices)
    status_bar.config(text=f"◈ EXPORTED → {path}", fg=GREEN)
    root.after(1500, root.destroy)

root.protocol("WM_DELETE_WINDOW", on_close)

tk.Button(bottom, text="⏹  END SESSION + EXPORT",
    command=on_close,
    bg=BG3, fg=MAGENTA, font=("Courier New", 9, "bold"),
    relief="flat", cursor="hand2",
    activebackground=MAGENTA, activeforeground=BG, bd=0
).pack(side="right", padx=16, pady=8, ipadx=12)

# ── Launch ─────────────────────────────────────────────────────────────────────
threading.Thread(target=start_monitor, args=(devices,), daemon=True).start()
root.after(1000, update_table)
root.mainloop()
