import os
import platform
import tkinter as tk

def check_admin():
    """Ensure the app is running with admin/root privileges."""
    try:
        if platform.system() == "Windows":
            import ctypes
            if not ctypes.windll.shell32.IsUserAnAdmin():
                # Re-launch with UAC elevation
                import sys
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas",
                    sys.executable,
                    " ".join(sys.argv),
                    None, 1
                )
                sys.exit()
        else:
            if os.geteuid() != 0:
                print("NetPyWiz requires root. Run with: sudo NetPyWiz")
                import sys; sys.exit(1)
    except Exception:
        pass

check_admin()
from tkinter import ttk, simpledialog
import threading
import time
from monitor import start_monitor, status, status_lock, latency_history, history_lock
from exporter import export_to_desktop, load_session_csv
from sparkline import draw_sparkline
from nmap_scan import run_nmap
from startup import (ask_subnets, run_splash_scan, ask_rescan,
                     ask_export_mode, best_font)
from config import load as load_config, save as save_config
from cve_lookup import lookup_cves, severity_color
from report_generator import generate_device_report, save_device_report

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
device_vulns  = {}  # { ip: { "nmap": {}, "cves_by_service": {} } }
previous_macs = set()
session_file  = {"path": None}
config        = load_config()

# subnet_data holds everything per subnet
# { subnet_str: { "devices": [], "tree": widget, ... } }
subnet_data = {}

# ── Single root ───────────────────────────────────────────────────────────────
root = tk.Tk()
root.withdraw()
root.title("NetPyWiz — Network Monitor")
root.configure(bg=BG)
root.wm_iconname("NetPyWiz")

# Set icon early — all Toplevels inherit
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
        for rx, ry in [(4,4),(52,4),(4,52),(52,52)]:
            draw.rectangle([rx, ry, rx+8, ry+8], fill="#00f5ff")
        return img

    _icon_photo = ImageTk.PhotoImage(_make_icon())
    root.iconphoto(True, _icon_photo)
except Exception as e:
    print(f"Icon error: {e}")

# ── Startup flow ──────────────────────────────────────────────────────────────
error_msg  = ""
all_devices = []  # flat list across all subnets
subnets    = []   # list of subnet strings

while not subnets:
    startup = ask_subnets(root, error_msg,
        default_subnet=config.get("last_subnet", "192.168.1.0/24"))

    if startup.get("cancelled"):
        root.destroy()
        import sys; sys.exit()

    if startup.get("load_file"):
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
            all_devices = loaded
            subnets     = [subnet]

        elif choice == "monitor_only":
            all_devices = loaded
            subnets     = [subnet]

    elif startup.get("subnets"):
        subnets_to_scan = startup["subnets"]
        found_any = False

        for sn in subnets_to_scan:
            scanned = run_splash_scan(root, sn)
            if scanned:
                all_devices.extend(scanned)
                subnets.append(sn)
                found_any = True
                save_config({
                "last_subnet": sn,
                "nvd_api_key": startup.get("api_key", "")
            })
        config["nvd_api_key"] = startup.get("api_key", "")

        if not found_any:
            error_msg = "No devices found on any subnet — check and try again"
            subnets   = []
            all_devices = []

# Group devices by subnet
for sn in subnets:
    subnet_data[sn] = {
        "devices": [d for d in all_devices if d.get("subnet", sn) == sn
                    or (len(subnets) == 1)],
        "selected_ip":   {"ip": None},
        "detached":      set(),
        "filter_var":    None,
        "tree":          None,
        "spark_mini":    None,
        "info_vars":     {},
        "status_bar":    None,
        "rescan_btn":    None,
    }

# ── Main Window ───────────────────────────────────────────────────────────────
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

subnet_summary = " + ".join(subnets)
tk.Label(header, text=f"◈  {subnet_summary}  ◈  {len(all_devices)} DEVICES",
    bg=BG2, fg=AMBER, font=best_font(9)).pack(side="right", padx=10)

def tick():
    clock_var.set(time.strftime("◈  %Y-%m-%d  %H:%M:%S"))
    root.after(1000, tick)
tick()

tk.Frame(root, bg=MAGENTA, height=2).pack(fill="x")

# Global stats bar
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
    bg=BG2, fg=YELLOW, font=best_font(9, True)).pack(side="left", padx=20)

tk.Frame(root, bg=CYAN, height=1).pack(fill="x")

# ── Notebook (tabs) ───────────────────────────────────────────────────────────
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

# Tab styling
style.configure("TNotebook",
    background=BG, borderwidth=0, tabmargins=0)
style.configure("TNotebook.Tab",
    background=BG2, foreground=DIM,
    font=best_font(9, True), padding=[16,6],
    borderwidth=0)
style.map("TNotebook.Tab",
    background=[("selected", BG3)],
    foreground=[("selected", CYAN)])

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

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
columns = list(col_defs.keys())

def build_tab(sn):
    """Builds a full tab UI for one subnet."""
    sd = subnet_data[sn]

    tab = tk.Frame(notebook, bg=BG)
    notebook.add(tab, text=f"  {sn}  ")

    # Toolbar
    toolbar = tk.Frame(tab, bg=BG2)
    toolbar.pack(fill="x")

    tk.Label(toolbar, text="⌕", bg=BG2, fg=CYAN,
        font=best_font(13)).pack(side="left", padx=(16,4), pady=6)

    filter_var = tk.StringVar()
    sd["filter_var"] = filter_var

    filter_entry = tk.Entry(toolbar, textvariable=filter_var,
        bg=BG3, fg=DIM, insertbackground=CYAN,
        selectbackground=MAGENTA_DIM,
        font=best_font(10), relief="flat", bd=0, width=30)
    filter_entry.pack(side="left", ipady=5, pady=6)
    filter_entry.insert(0, "FILTER DEVICES...")

    def on_focus_in(e):
        if filter_entry.get() == "FILTER DEVICES...":
            filter_entry.delete(0, "end")
            filter_entry.config(fg=CYAN)

    def on_focus_out(e):
        if not filter_entry.get():
            filter_entry.insert(0, "FILTER DEVICES...")
            filter_entry.config(fg=DIM)

    filter_entry.bind("<FocusIn>",  on_focus_in)
    filter_entry.bind("<FocusOut>", on_focus_out)

    tk.Frame(toolbar, bg=CYAN, width=1).pack(side="left", fill="y", padx=4)

    rescan_btn = tk.Button(toolbar, text="⟳  RESCAN",
        bg=BG3, fg=CYAN, font=best_font(9, True),
        relief="flat", cursor="hand2",
        activebackground=CYAN, activeforeground=BG, bd=0)
    rescan_btn.pack(side="left", padx=12, pady=6, ipadx=10)
    sd["rescan_btn"] = rescan_btn

    tk.Frame(tab, bg=CYAN, height=1).pack(fill="x")

    # Table
    table_frame = tk.Frame(tab, bg=BG)
    table_frame.pack(fill="both", expand=True)

    tree = ttk.Treeview(table_frame, columns=columns,
        show="headings", selectmode="browse")
    sd["tree"] = tree

    for col, (label, width) in col_defs.items():
        tree.heading(col, text=label)
        tree.column(col, width=width,
            anchor="center" if col in
                ("status","port","latency","avg_latency","downtime") else "w")

    tree.tag_configure("green",   background=BG3, foreground=GREEN)
    tree.tag_configure("red",     background=BG3, foreground=RED)
    tree.tag_configure("unknown", background=BG3, foreground=DIM)
    tree.tag_configure("new",     background="#1a1a00", foreground=YELLOW)

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical",
        command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Populate rows
    for d in sd["devices"]:
        is_new = d.get("new_device", False)
        tree.insert("", "end", iid=d["ip"], values=(
            "★ NEW" if is_new else "◈ INIT",
            d["ip"], d["mac"], d["hostname"], d["vendor"],
            d.get("port",""), "", "", "0"
        ), tags=("new" if is_new else "unknown",))

    # Info bar
    tk.Frame(tab, bg=MAGENTA, height=1).pack(fill="x")
    info_bar = tk.Frame(tab, bg=BG2, height=90)
    info_bar.pack(fill="x")
    info_bar.pack_propagate(False)

    ivars = {
        "ip":     tk.StringVar(),
        "status": tk.StringVar(),
        "lat":    tk.StringVar(),
        "avg":    tk.StringVar(),
        "down":   tk.StringVar(),
        "vendor": tk.StringVar(),
        "mac":    tk.StringVar(),
    }
    sd["info_vars"] = ivars

    li = tk.Frame(info_bar, bg=BG2)
    li.pack(side="left", padx=16, pady=8)
    tk.Label(li, textvariable=ivars["ip"],
        bg=BG2, fg=MAGENTA, font=best_font(14, True)).pack(anchor="w")
    tk.Label(li, textvariable=ivars["status"],
        bg=BG2, fg=GREEN, font=best_font(9)).pack(anchor="w")

    tk.Frame(info_bar, bg=DIM, width=1).pack(side="left", fill="y", pady=8)

    mi = tk.Frame(info_bar, bg=BG2)
    mi.pack(side="left", padx=16, pady=8)
    for lbl, key, col in [
        ("LATENCY",  "lat",  CYAN),
        ("AVG",      "avg",  CYAN),
        ("DOWNTIME", "down", RED),
    ]:
        row = tk.Frame(mi, bg=BG2)
        row.pack(anchor="w")
        tk.Label(row, text=f"{lbl:<10}", bg=BG2, fg=DIM,
            font=best_font(8)).pack(side="left")
        tk.Label(row, textvariable=ivars[key], bg=BG2, fg=col,
            font=best_font(8, True)).pack(side="left")

    tk.Frame(info_bar, bg=DIM, width=1).pack(side="left", fill="y", pady=8)

    ri = tk.Frame(info_bar, bg=BG2)
    ri.pack(side="left", padx=16, pady=8)
    for lbl, key in [("VENDOR", "vendor"), ("MAC", "mac")]:
        row = tk.Frame(ri, bg=BG2)
        row.pack(anchor="w")
        tk.Label(row, text=f"{lbl:<8}", bg=BG2, fg=DIM,
            font=best_font(8)).pack(side="left")
        tk.Label(row, textvariable=ivars[key], bg=BG2, fg=WHITE,
            font=best_font(8)).pack(side="left")

    spark_mini = tk.Canvas(info_bar, width=200, height=70,
        bg=BG2, highlightthickness=0)
    spark_mini.pack(side="right", padx=16, pady=8)
    sd["spark_mini"] = spark_mini

    tk.Label(info_bar,
        text="◈ CLICK TO INSPECT  //  DOUBLE-CLICK FOR DETAIL",
        bg=BG2, fg=DIM, font=best_font(7)).pack(side="right", padx=8)

    # Filter logic
    def apply_filter(*args, _sn=sn):
        _sd    = subnet_data[_sn]
        query  = _sd["filter_var"].get().strip().lower()
        if query == "filter devices...":
            query = ""
        for d in _sd["devices"]:
            ip       = d["ip"]
            haystack = " ".join([ip,
                d.get("hostname",""), d.get("vendor",""),
                d.get("mac",""),      d.get("port","")]).lower()
            match = (query in haystack) if query else True
            if not match and ip not in _sd["detached"]:
                _sd["tree"].detach(ip)
                _sd["detached"].add(ip)
            elif match and ip in _sd["detached"]:
                _sd["tree"].reattach(ip, "", "end")
                _sd["detached"].discard(ip)

    filter_var.trace_add("write", apply_filter)

    # Rescan logic
    rescan_running = threading.Event()

    def do_rescan(_sn=sn):
        if rescan_running.is_set():
            return
        rescan_running.set()
        sd2 = subnet_data[_sn]
        sd2["rescan_btn"].config(state="disabled", text="⟳  SCANNING...")

        def rescan_thread():
            from scanner import scan_subnet as _scan
            from monitor import ping_worker
            found        = _scan(_sn)
            existing_ips = {d["ip"] for d in sd2["devices"]}
            new_devs     = []

            for d in found:
                if d["ip"] not in existing_ips:
                    d["port"]       = ""
                    d["notes"]      = ""
                    d["new_device"] = True
                    d["subnet"]     = _sn
                    new_devs.append(d)
                    sd2["devices"].append(d)
                    all_devices.append(d)
                    with status_lock:
                        status[d["ip"]] = {
                            "alive": None, "latency": None,
                            "avg_latency": None, "downtime": 0,
                            "first_seen": None, "total_pings": 0,
                            "online_pings": 0
                        }
                    with history_lock:
                        latency_history[d["ip"]] = []
                    t = threading.Thread(
                        target=ping_worker, args=(d["ip"],), daemon=True)
                    t.start()
                    root.after(0, lambda dev=d, t=sd2["tree"]: (
                        t.exists(dev["ip"]) or t.insert(
                            "", "end", iid=dev["ip"],
                            values=("★ NEW", dev["ip"], dev["mac"],
                                    dev["hostname"], dev["vendor"],
                                    "", "", "", "0"),
                            tags=("new",))
                    ))

            msg = (f"◈ RESCAN COMPLETE  //  {len(new_devs)} NEW"
                   if new_devs else "◈ RESCAN COMPLETE  //  NO NEW DEVICES")
            col = GREEN if new_devs else DIM
            root.after(0, lambda: sd2["rescan_btn"].config(
                state="normal", text="⟳  RESCAN"))
            rescan_running.clear()

        threading.Thread(target=rescan_thread, daemon=True).start()

    rescan_btn.config(command=do_rescan)

    # Click handlers
    def on_single_click(event, _sn=sn):
        _sd  = subnet_data[_sn]
        item = _sd["tree"].identify_row(event.y)
        if not item:
            return
        _sd["selected_ip"]["ip"] = item
        update_info_bar(_sn, item)

    def on_double_click(event, _sn=sn):
        _sd  = subnet_data[_sn]
        item = _sd["tree"].identify_row(event.y)
        col  = _sd["tree"].identify_column(event.x)
        if not item:
            return
        if col == "#6":
            cur = _sd["tree"].item(item)["values"][5]
            new_val = simpledialog.askstring(
                "Switch Port", f"Enter switch port for {item}:",
                initialvalue=cur, parent=root)
            if new_val is not None:
                ex    = list(_sd["tree"].item(item)["values"])
                ex[5] = new_val
                _sd["tree"].item(item, values=ex)
                for d in _sd["devices"]:
                    if d["ip"] == item:
                        d["port"] = new_val
            return
        open_detail_popup(item)

    tree.bind("<Button-1>", on_single_click)
    tree.bind("<Double-1>", on_double_click)

# Build all tabs
for sn in subnets:
    build_tab(sn)

# ── Info bar updater ──────────────────────────────────────────────────────────
def update_info_bar(sn, ip):
    sd     = subnet_data[sn]
    d_info = next((d for d in sd["devices"] if d["ip"] == ip), {})
    with status_lock:
        s = dict(status.get(ip, {}))
    with history_lock:
        samples = list(latency_history.get(ip, []))
    alive = s.get("alive")
    iv    = sd["info_vars"]
    iv["ip"].set(ip)
    iv["status"].set("▲ ONLINE" if alive else "▼ OFFLINE" if alive is False else "◈ INIT")
    iv["lat"].set(f"{s.get('latency') or '---'} ms")
    iv["avg"].set(f"{s.get('avg_latency') or '---'} ms")
    iv["down"].set(f"{s.get('downtime', 0)}s")
    iv["vendor"].set(d_info.get("vendor", ""))
    iv["mac"].set(d_info.get("mac", ""))
    draw_sparkline(sd["spark_mini"], samples, 200, 70, mini=True)

def refresh_all_info_bars():
    for sn, sd in subnet_data.items():
        ip = sd["selected_ip"]["ip"]
        if ip:
            try:
                update_info_bar(sn, ip)
            except Exception:
                pass
    root.after(1000, refresh_all_info_bars)

# ── Detail popup ──────────────────────────────────────────────────────────────
def open_detail_popup(ip):
    d_info = next((d for d in all_devices if d["ip"] == ip), {})

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
        ("SUBNET",      d_info.get("subnet","---"),  CYAN),
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
        for d in all_devices:
            if d["ip"] == ip:
                d["notes"] = device_notes[ip]

    notes_box.bind("<KeyRelease>", save_notes)

    # nmap
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
        nmap_result = run_nmap(ip)
        if popup.winfo_exists():
            root.after(0, lambda: populate_nmap(nmap_result))

    def populate_nmap(nmap_result):
        nmap_scanning["active"] = False
        nmap_status_var.set("◈ PORTS SCANNED — LOOKING UP CVEs...")
        nmap_status_lbl.config(fg=AMBER)
        os_var.set(f"OS: {nmap_result['os_guess']}")

        # Firewall detection
        fw_keywords = ["firewall","fortinet","paloalto","pfsense",
                       "checkpoint","sonicwall","cisco asa","juniper"]
        fw_detected = any(k in nmap_result.get("os_guess","").lower()
                         for k in fw_keywords)
        fw_label = tk.Label(port_frame,
            text=f"{'⚠ FIREWALL DETECTED' if fw_detected else '◈ NO FIREWALL DETECTED'}",
            bg=BG3,
            fg=RED if fw_detected else DIM,
            font=best_font(8, True))
        fw_label.pack(anchor="w", pady=(0,4))

        if not nmap_result["ports"]:
            tk.Label(port_frame, text="NO OPEN PORTS FOUND",
                bg=BG3, fg=DIM, font=best_font(8)).pack(pady=8)
            nmap_status_var.set("◈ SCAN COMPLETE")
            nmap_status_lbl.config(fg=GREEN)
            return

        # Port headers
        hrow = tk.Frame(port_frame, bg=BG3)
        hrow.pack(fill="x")
        for txt, w in [("PORT",7),("PROTO",6),("SERVICE",28)]:
            tk.Label(hrow, text=txt, width=w, bg=BG3, fg=CYAN,
                font=best_font(8, True), anchor="w").pack(side="left")
        tk.Frame(port_frame, bg=MAGENTA_DIM, height=1).pack(fill="x", pady=2)

        # Scrollable port + CVE list
        c  = tk.Canvas(port_frame, bg=BG3, highlightthickness=0)
        sb = ttk.Scrollbar(port_frame, orient="vertical", command=c.yview)
        inner = tk.Frame(c, bg=BG3)
        inner.bind("<Configure>",
            lambda e: c.configure(scrollregion=c.bbox("all")))
        c.create_window((0,0), window=inner, anchor="nw")
        c.configure(yscrollcommand=sb.set)
        c.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        for p in nmap_result["ports"]:
            pr = tk.Frame(inner, bg=BG3)
            pr.pack(fill="x", pady=1)
            tk.Label(pr, text=p["port"],     width=7,  bg=BG3, fg=GREEN,
                font=best_font(8), anchor="w").pack(side="left")
            tk.Label(pr, text=p["protocol"], width=6,  bg=BG3, fg=DIM,
                font=best_font(8), anchor="w").pack(side="left")
            tk.Label(pr, text=p["service"],  width=28, bg=BG3, fg=WHITE,
                font=best_font(8), anchor="w").pack(side="left")

        # CVE lookup in background
        def cve_thread():
            cves_by_service = {}
            services = list({p["service"] for p in nmap_result["ports"]
                            if p["service"] not in ("unknown","")})
            for svc in services:
                cves = lookup_cves(svc,
                    api_key=config.get("nvd_api_key",""))
                if cves:
                    cves_by_service[svc] = cves

            # Store for export
            device_vulns[ip] = {
                "nmap":            nmap_result,
                "cves_by_service": cves_by_service
            }

            if popup.winfo_exists():
                root.after(0, lambda: populate_cves(cves_by_service))

        def populate_cves(cves_by_service):
            nmap_status_var.set("◈ SCAN COMPLETE")
            nmap_status_lbl.config(fg=GREEN)

            all_cves = []
            for svc, cves in cves_by_service.items():
                for c2 in cves:
                    if "error" not in c2:
                        all_cves.append(c2)

            if not all_cves:
                tk.Label(inner,
                    text="  ◈ No known CVEs found for detected services",
                    bg=BG3, fg=DIM, font=best_font(7)).pack(anchor="w", pady=4)
                return

            # CVE section header
            tk.Frame(inner, bg=MAGENTA_DIM, height=1).pack(
                fill="x", pady=(8,2))
            tk.Label(inner, text=f"  CVEs FOUND: {len(all_cves)}",
                bg=BG3, fg=MAGENTA, font=best_font(8, True)).pack(anchor="w")

            for cve in all_cves:
                col = severity_color(cve["severity"])
                cf  = tk.Frame(inner, bg=BG3)
                cf.pack(fill="x", pady=2)

                # Severity badge + ID
                tk.Label(cf,
                    text=f"[{cve['severity']}]",
                    width=10, bg=BG3, fg=col,
                    font=best_font(7, True), anchor="w").pack(side="left")
                tk.Label(cf,
                    text=cve["id"],
                    bg=BG3, fg=WHITE,
                    font=best_font(7, True), anchor="w").pack(side="left")
                if cve.get("score"):
                    tk.Label(cf,
                        text=f"  Score: {cve['score']}",
                        bg=BG3, fg=col,
                        font=best_font(7), anchor="w").pack(side="left")

                # Service
                tk.Label(inner,
                    text=f"    Service: {cve['service']}",
                    bg=BG3, fg=DIM, font=best_font(7), anchor="w").pack(
                    fill="x")

                # Summary — wrapped
                tk.Label(inner,
                    text=f"    {cve['summary']}",
                    bg=BG3, fg="#aaaacc",
                    font=best_font(7),
                    wraplength=320, justify="left", anchor="w").pack(
                    fill="x", padx=4)

                # Clickable URL
                url_label = tk.Label(inner,
                    text=f"    ► {cve['url']}",
                    bg=BG3, fg=CYAN,
                    font=best_font(7),
                    cursor="hand2", anchor="w")
                url_label.pack(fill="x")
                url_label.bind("<Button-1>",
                    lambda e, url=cve["url"]: __import__("webbrowser").open(url))

                tk.Frame(inner, bg=DIM, height=1).pack(
                    fill="x", pady=2)

        threading.Thread(target=cve_thread, daemon=True).start()

    threading.Thread(target=run_nmap_thread, daemon=True).start()

# ── Global update loop ────────────────────────────────────────────────────────
def update_all_tables():
    with status_lock:
        current = dict(status)

    total_online = total_offline = total_pending = total_new = 0

    for sn, sd in subnet_data.items():
        tree = sd["tree"]
        for d in sd["devices"]:
            ip     = d["ip"]
            if not tree.exists(ip):
                continue
            s      = current.get(ip, {})
            is_new = d.get("new_device", False)
            alive  = s.get("alive")

            if is_new:
                total_new += 1
                tag   = "new"
                label = "★ NEW"
                if alive is True:    total_online  += 1
                elif alive is False: total_offline += 1
                else:                total_pending += 1
            elif alive is None:
                tag, label = "unknown", "◈ INIT"
                total_pending += 1
            elif alive:
                tag, label = "green", "▲ ONLINE"
                total_online += 1
            else:
                tag, label = "red", "▼ OFFLINE"
                total_offline += 1

            ex = list(tree.item(ip)["values"])
            tree.item(ip, values=(
                label,
                ex[1], ex[2], ex[3], ex[4], ex[5],
                f"{s['latency']} ms"     if s.get("latency")     else "---",
                f"{s['avg_latency']} ms" if s.get("avg_latency") else "---",
                s.get("downtime", 0)
            ), tags=(tag,))

    online_var.set(f"▲ ONLINE:  {total_online}")
    offline_var.set(f"▼ OFFLINE:  {total_offline}")
    unknown_var.set(f"◈ PENDING:  {total_pending}")
    new_var.set(f"★ NEW:  {total_new}" if total_new else "")
    root.after(1000, update_all_tables)

# ── Tray ──────────────────────────────────────────────────────────────────────
tray_icon = {"instance": None}

def make_tray_image():
    from PIL import Image, ImageDraw
    img  = Image.new("RGB", (64, 64), "#0a0a0f")
    draw = ImageDraw.Draw(img)
    draw.rectangle([8, 14, 56, 50], outline="#ff00ff", width=2, fill="#1a1a2e")
    for i in range(8):
        x = 13 + i * 5
        draw.rectangle([x, 20, x+3, 36], fill="#ffaa00")
    draw.rectangle([20, 48, 44, 56], outline="#ff00ff", width=1, fill="#1a1a2e")
    for rx, ry in [(4,4),(52,4),(4,52),(52,52)]:
        draw.rectangle([rx, ry, rx+8, ry+8], fill="#00f5ff")
    return img

def setup_tray():
    try:
        import pystray
        icon = pystray.Icon("NetPyWiz", make_tray_image(), "NetPyWiz Monitor",
            pystray.Menu(
                pystray.MenuItem("Show NetPyWiz",
                    lambda i,it: root.after(0, root.deiconify), default=True),
                pystray.MenuItem("Exit + Export",
                    lambda i,it: root.after(0, on_close))
            ))
        tray_icon["instance"] = icon
        def on_minimize(event):
            if root.state() == "iconic":
                root.withdraw()
        root.bind("<Unmap>", on_minimize)
        threading.Thread(target=icon.run, daemon=True).start()
    except Exception as e:
        print(f"Tray unavailable: {e}")

# ── Bottom bar ────────────────────────────────────────────────────────────────
tk.Frame(root, bg=MAGENTA, height=1).pack(fill="x")
bottom = tk.Frame(root, bg=BG2, height=44)
bottom.pack(fill="x", side="bottom")
bottom.pack_propagate(False)

status_bar = tk.Label(bottom,
    text="◈ MONITORING ACTIVE",
    bg=BG2, fg=DIM, font=best_font(8), anchor="w")
status_bar.pack(side="left", padx=16)

def on_close():
    save_config({"window_size": root.geometry().split("+")[0]})
    if tray_icon["instance"]:
        tray_icon["instance"].stop()

    from exporter import create_session_folder
    from report_generator import generate_device_report, save_device_report

    if session_file["path"]:
        choice = ask_export_mode(root)
        if choice == "cancel":
            return

    folders = []
    for sn, sd in subnet_data.items():
        vuln_ips = set(device_vulns.keys())

        if session_file["path"] and choice == "append":
            export_to_desktop(sd["devices"], subnet=sn,
                append_to=session_file["path"],
                vuln_devices=vuln_ips)
            folders.append(os.path.dirname(session_file["path"]))
        else:
            folder = create_session_folder(sn)
            export_to_desktop(sd["devices"], subnet=sn,
                folder=folder, vuln_devices=vuln_ips)

            # Generate per-device vulnerability reports
            for ip, vdata in device_vulns.items():
                d_info = next((d for d in sd["devices"] if d["ip"] == ip), None)
                if not d_info:
                    continue
                report = generate_device_report(
                    d_info,
                    vdata["nmap"],
                    vdata["cves_by_service"]
                )
                save_device_report(report, ip, folder)

            folders.append(folder)

    path = ", ".join(folders)
    status_bar.config(text=f"◈ EXPORTED → {path}", fg=GREEN)
    root.after(1500, root.destroy)

root.protocol("WM_DELETE_WINDOW", on_close)

tk.Button(bottom, text="⏹  END SESSION + EXPORT",
    command=on_close,
    bg=BG3, fg=MAGENTA, font=best_font(9, True),
    relief="flat", cursor="hand2",
    activebackground=MAGENTA, activeforeground=BG, bd=0
).pack(side="right", padx=16, pady=8, ipadx=12)

# ── Launch ────────────────────────────────────────────────────────────────────
threading.Thread(target=start_monitor, args=(all_devices,), daemon=True).start()
root.after(1000, update_all_tables)
root.after(1000, refresh_all_info_bars)
root.after(500,  setup_tray)
root.deiconify()
root.mainloop()
