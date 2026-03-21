import tkinter as tk
from tkinter import ttk, simpledialog, font
import json
import threading
import time
from monitor import start_monitor, status, status_lock
from exporter import export_to_desktop
from scanner import scan_subnet

# ── Color Palette ─────────────────────────────────────────────────────────────
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
GRID_LINE   = "#1a1a3a"

# ── Subnet Dialog ─────────────────────────────────────────────────────────────
def ask_subnet():
    dialog = tk.Tk()
    dialog.title("NetPyWiz")
    dialog.configure(bg=BG)
    dialog.geometry("500x280")
    dialog.resizable(False, False)

    # Center on screen
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 250
    y = (dialog.winfo_screenheight() // 2) - 140
    dialog.geometry(f"+{x}+{y}")

    result = {"subnet": None}

    # Header
    tk.Label(dialog,
        text="▓▓ NETPYWIZ // NETWORK MONITOR ▓▓",
        bg=BG, fg=MAGENTA,
        font=("Courier New", 13, "bold")
    ).pack(pady=(28, 4))

    tk.Label(dialog,
        text="INITIALIZE SUBNET SCAN",
        bg=BG, fg=CYAN,
        font=("Courier New", 9)
    ).pack()

    # Divider
    tk.Frame(dialog, bg=MAGENTA, height=1).pack(fill="x", padx=30, pady=14)

    tk.Label(dialog,
        text="TARGET SUBNET  (CIDR notation)",
        bg=BG, fg=DIM,
        font=("Courier New", 8)
    ).pack()

    entry_var = tk.StringVar(value="192.168.1.0/24")
    entry = tk.Entry(dialog,
        textvariable=entry_var,
        bg=BG3, fg=CYAN,
        insertbackground=CYAN,
        selectbackground=MAGENTA,
        font=("Courier New", 13),
        relief="flat",
        justify="center",
        bd=0
    )
    entry.pack(padx=50, pady=10, ipady=8, fill="x")
    entry.select_range(0, "end")
    entry.focus()

    # Cyan border frame around entry
    tk.Frame(dialog, bg=CYAN, height=1).pack(fill="x", padx=50)

    def confirm(event=None):
        result["subnet"] = entry_var.get().strip()
        dialog.destroy()

    entry.bind("<Return>", confirm)
    entry.bind("<KP_Enter>", confirm)

    tk.Button(dialog,
        text="► INITIATE SCAN",
        command=confirm,
        bg=MAGENTA_DIM, fg=BG,
        font=("Courier New", 11, "bold"),
        relief="flat",
        cursor="hand2",
        activebackground=MAGENTA,
        activeforeground=BG,
        bd=0
    ).pack(pady=16, ipadx=20, ipady=6)

    dialog.mainloop()
    return result["subnet"]

# ── Get subnet from user ──────────────────────────────────────────────────────
subnet = ask_subnet()
if not subnet:
    exit()

# ── Scan ──────────────────────────────────────────────────────────────────────
# Show a scanning splash before main window
splash = tk.Tk()
splash.title("NetPyWiz")
splash.configure(bg=BG)
splash.geometry("400x160")
splash.resizable(False, False)
splash.update_idletasks()
x = (splash.winfo_screenwidth() // 2) - 200
y = (splash.winfo_screenheight() // 2) - 80
splash.geometry(f"+{x}+{y}")

tk.Label(splash,
    text="▓▓ NETPYWIZ ▓▓",
    bg=BG, fg=MAGENTA,
    font=("Courier New", 14, "bold")
).pack(pady=(24, 4))

scan_label = tk.Label(splash,
    text=f"SCANNING  {subnet} ...",
    bg=BG, fg=CYAN,
    font=("Courier New", 10)
)
scan_label.pack()

tk.Label(splash,
    text="THIS MAY TAKE UP TO 30 SECONDS",
    bg=BG, fg=DIM,
    font=("Courier New", 8)
).pack(pady=4)

# Animated dots
dot_var = tk.StringVar(value="")
dot_label = tk.Label(splash, textvariable=dot_var, bg=BG, fg=MAGENTA, font=("Courier New", 12))
dot_label.pack()

devices = []
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
    current = dot_var.get()
    dot_var.set("█" * ((len(current) % 8) + 1))
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
    tk.Tk().withdraw()
    from tkinter import messagebox
    messagebox.showerror("NetPyWiz", f"No devices found on {subnet}")
    exit()

# ── Main Window ───────────────────────────────────────────────────────────────
root = tk.Tk()
root.title("NetPyWiz — Network Monitor")
root.configure(bg=BG)
root.geometry("1280x720")
root.minsize(900, 500)

# ── Header Bar ────────────────────────────────────────────────────────────────
header = tk.Frame(root, bg=BG2, height=56)
header.pack(fill="x", side="top")
header.pack_propagate(False)

tk.Label(header,
    text="▓▓ NETPYWIZ",
    bg=BG2, fg=MAGENTA,
    font=("Courier New", 18, "bold")
).pack(side="left", padx=20, pady=10)

tk.Label(header,
    text="// NETWORK MONITOR",
    bg=BG2, fg=CYAN,
    font=("Courier New", 12)
).pack(side="left", pady=10)

# Live clock
clock_var = tk.StringVar()
tk.Label(header,
    textvariable=clock_var,
    bg=BG2, fg=DIM,
    font=("Courier New", 10)
).pack(side="right", padx=20)

def tick():
    clock_var.set(time.strftime("◈  %Y-%m-%d  %H:%M:%S"))
    root.after(1000, tick)
tick()

# Subnet label
tk.Label(header,
    text=f"◈  {subnet}  ◈  {len(devices)} DEVICES",
    bg=BG2, fg=AMBER,
    font=("Courier New", 9)
).pack(side="right", padx=10)

# Magenta accent line under header
tk.Frame(root, bg=MAGENTA, height=2).pack(fill="x")

# ── Stats Bar ─────────────────────────────────────────────────────────────────
stats_frame = tk.Frame(root, bg=BG2)
stats_frame.pack(fill="x")

online_var  = tk.StringVar(value="ONLINE:  0")
offline_var = tk.StringVar(value="OFFLINE:  0")
unknown_var = tk.StringVar(value="PENDING:  0")

for var, color in [(online_var, GREEN), (offline_var, RED), (unknown_var, DIM)]:
    tk.Label(stats_frame,
        textvariable=var,
        bg=BG2, fg=color,
        font=("Courier New", 9, "bold")
    ).pack(side="left", padx=20, pady=4)

tk.Frame(root, bg=CYAN, height=1).pack(fill="x")

# ── Table ─────────────────────────────────────────────────────────────────────
table_frame = tk.Frame(root, bg=BG)
table_frame.pack(fill="both", expand=True)

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview",
    background=BG3,
    foreground=WHITE,
    fieldbackground=BG3,
    rowheight=30,
    font=("Courier New", 10),
    borderwidth=0
)
style.configure("Treeview.Heading",
    background=BG2,
    foreground=CYAN,
    font=("Courier New", 9, "bold"),
    relief="flat",
    borderwidth=0
)
style.map("Treeview",
    background=[("selected", "#2a2a4a")],
    foreground=[("selected", CYAN)]
)
style.layout("Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

columns = ("status", "ip", "mac", "hostname", "vendor", "port", "latency", "avg_latency", "downtime")
tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")

headers = {
    "status":      ("STATUS",       80),
    "ip":          ("IP ADDRESS",  130),
    "mac":         ("MAC ADDRESS", 155),
    "hostname":    ("HOSTNAME",    200),
    "vendor":      ("VENDOR",      160),
    "port":        ("SW PORT",     100),
    "latency":     ("LAT ms",       80),
    "avg_latency": ("AVG ms",       80),
    "downtime":    ("DOWN s",       80),
}

for col, (label, width) in headers.items():
    tree.heading(col, text=label)
    tree.column(col, width=width, anchor="center" if col in ("status","port","latency","avg_latency","downtime") else "w")

# Row color tags
tree.tag_configure("green",
    background="#001a0f",
    foreground=GREEN
)
tree.tag_configure("red",
    background="#1a000a",
    foreground=RED
)
tree.tag_configure("unknown",
    background=BG3,
    foreground=DIM
)

scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
tree.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Populate rows
for d in devices:
    tree.insert("", "end", iid=d["ip"], values=(
        "INIT...", d["ip"], d["mac"], d["hostname"], d["vendor"], "", "", "", "0"
    ), tags=("unknown",))

# ── Double click to edit port ──────────────────────────────────────────────────
def on_double_click(event):
    item = tree.identify_row(event.y)
    col  = tree.identify_column(event.x)
    if not item or col != "#6":
        return
    current_val = tree.item(item)["values"][5]
    new_val = simpledialog.askstring(
        "Switch Port",
        f"Enter switch port for {item}:",
        initialvalue=current_val,
        parent=root
    )
    if new_val is not None:
        existing = list(tree.item(item)["values"])
        existing[5] = new_val
        tree.item(item, values=existing)
        for d in devices:
            if d["ip"] == item:
                d["port"] = new_val

tree.bind("<Double-1>", on_double_click)

# ── Update Loop ────────────────────────────────────────────────────────────────
def update_table():
    with status_lock:
        current = dict(status)

    online = offline = pending = 0

    for ip, s in current.items():
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
            f"{s['latency']} ms"    if s.get("latency")     else "---",
            f"{s['avg_latency']} ms" if s.get("avg_latency") else "---",
            s.get("downtime", 0)
        ), tags=(tag,))

    online_var.set(f"● ONLINE:  {online}")
    offline_var.set(f"● OFFLINE:  {offline}")
    unknown_var.set(f"◈ PENDING:  {pending}")

    root.after(1000, update_table)

# ── Bottom Bar ─────────────────────────────────────────────────────────────────
tk.Frame(root, bg=MAGENTA, height=1).pack(fill="x")
bottom = tk.Frame(root, bg=BG2, height=44)
bottom.pack(fill="x", side="bottom")
bottom.pack_propagate(False)

status_bar = tk.Label(bottom,
    text="◈ DOUBLE-CLICK  [SW PORT]  COLUMN TO EDIT  //  MONITORING ACTIVE",
    bg=BG2, fg=DIM,
    font=("Courier New", 8),
    anchor="w"
)
status_bar.pack(side="left", padx=16)

def on_close():
    path = export_to_desktop(devices)
    status_bar.config(text=f"◈ EXPORTED → {path}", fg=GREEN)
    root.after(1500, root.destroy)

root.protocol("WM_DELETE_WINDOW", on_close)

btn = tk.Button(bottom,
    text="⏹  END SESSION + EXPORT",
    command=on_close,
    bg=BG3, fg=MAGENTA,
    font=("Courier New", 9, "bold"),
    relief="flat",
    cursor="hand2",
    activebackground=MAGENTA,
    activeforeground=BG,
    bd=0
)
btn.pack(side="right", padx=16, pady=8, ipadx=12)

# ── Launch ─────────────────────────────────────────────────────────────────────
threading.Thread(target=start_monitor, args=(devices,), daemon=True).start()
root.after(1000, update_table)
root.mainloop()
