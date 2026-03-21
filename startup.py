import tkinter as tk
from tkinter import filedialog
from subnet_discovery import run_discovery_dialog
from subnet_discovery import run_discovery_dialog
import threading
from scanner import scan_subnet
from exporter import load_session_csv

BG          = "#0a0a0f"
BG2         = "#0f0f1a"
BG3         = "#1a1a2e"
CYAN        = "#00f5ff"
MAGENTA     = "#ff00ff"
MAGENTA_DIM = "#cc00cc"
RED         = "#ff2255"
AMBER       = "#ffaa00"
DIM         = "#444466"
YELLOW      = "#ffe94d"

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


def ask_subnets(root, error_msg="", default_subnet="192.168.1.0/24", nvd_api_key=""):
    result = {"subnets": [], "load_file": None, "cancelled": False, "api_key": ""}
    queued = []

    dialog = tk.Toplevel(root)
    dialog.title("NetPyWiz")
    dialog.configure(bg=BG)
    dialog.geometry("520x660")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() // 2) - 260
    y = (dialog.winfo_screenheight() // 2) - 290
    dialog.geometry(f"+{x}+{y}")

    tk.Label(dialog, text="▓▓ NETPYWIZ // NETWORK MONITOR ▓▓",
        bg=BG, fg=MAGENTA, font=best_font(13, True)).pack(pady=(16,4))
    tk.Label(dialog, text="INITIALIZE SUBNET SCAN",
        bg=BG, fg=CYAN, font=best_font(9)).pack()

    if error_msg:
        tk.Label(dialog, text=f"⚠  {error_msg}",
            bg=BG, fg=RED, font=best_font(8, True)).pack(pady=(4,0))

    tk.Frame(dialog, bg=MAGENTA, height=1).pack(fill="x", padx=30, pady=8)
    tk.Label(dialog, text="TARGET SUBNET  (CIDR notation)",
        bg=BG, fg=DIM, font=best_font(8)).pack()

    entry_var = tk.StringVar(value=default_subnet)
    entry = tk.Entry(dialog, textvariable=entry_var,
        bg=BG3, fg=CYAN, insertbackground=CYAN, selectbackground=MAGENTA,
        font=best_font(12), relief="flat", justify="center", bd=0)
    entry.pack(padx=50, pady=6, ipady=8, fill="x")
    entry.select_range(0, "end")
    entry.focus()
    tk.Frame(dialog, bg=CYAN, height=1).pack(fill="x", padx=50)

    # Queue display
    queue_frame = tk.Frame(dialog, bg=BG)
    queue_frame.pack(fill="x", padx=50, pady=4)
    queue_label = tk.Label(queue_frame, text="", bg=BG, fg=AMBER, font=best_font(8))
    queue_label.pack(anchor="w")

    def refresh_queue():
        if queued:
            queue_label.config(
                text="QUEUED:\n" + "\n".join(f"  ◈ {s}" for s in queued))
        else:
            queue_label.config(text="")

    def add_to_queue(event=None):
        val = entry_var.get().strip()
        if val and val not in queued:
            queued.append(val)
            refresh_queue()
            entry_var.set("")
            entry.focus()

    def start_scan(event=None):
        val = entry_var.get().strip()
        if val and val not in queued:
            queued.append(val)
        if queued:
            result["subnets"] = list(queued)
            result["api_key"] = api_var.get().strip()
            dialog.grab_release()
            dialog.destroy()

    entry.bind("<Return>",   start_scan)
    entry.bind("<KP_Enter>", start_scan)

    # Scan buttons
    btn_frame = tk.Frame(dialog, bg=BG)
    btn_frame.pack(pady=6)

    tk.Button(btn_frame, text="+ ADD ANOTHER SUBNET",
        command=add_to_queue,
        bg=BG3, fg=CYAN, font=best_font(9),
        relief="flat", cursor="hand2",
        activebackground=CYAN, activeforeground=BG, bd=0
    ).pack(side="left", padx=6, ipadx=10, ipady=4)

    tk.Button(btn_frame, text="► INITIATE SCAN",
        command=start_scan,
        bg=MAGENTA_DIM, fg=BG, font=best_font(9, True),
        relief="flat", cursor="hand2",
        activebackground=MAGENTA, activeforeground=BG, bd=0
    ).pack(side="left", padx=6, ipadx=10, ipady=4)

    # Load session
    # Auto-discover button
    tk.Frame(dialog, bg=DIM, height=1).pack(fill="x", padx=30, pady=(6,0))
    tk.Label(dialog, text="— OR AUTO-DISCOVER SUBNETS —",
        bg=BG, fg=DIM, font=best_font(7)).pack(pady=(6,0))

    def auto_discover():
        discovered = run_discovery_dialog(root)
        if discovered:
            result["subnets"] = discovered
            result["api_key"] = api_var.get().strip()
            dialog.grab_release()
            dialog.destroy()

    tk.Button(dialog, text="🔍  AUTO-DISCOVER SUBNETS",
        command=auto_discover,
        bg=BG3, fg=YELLOW, font=best_font(9),
        relief="flat", cursor="hand2",
        activebackground=YELLOW, activeforeground=BG, bd=0
    ).pack(pady=6, ipadx=16, ipady=4)

    tk.Frame(dialog, bg=DIM, height=1).pack(fill="x", padx=30, pady=(6,0))
    tk.Label(dialog, text="— OR LOAD A PREVIOUS SESSION —",
        bg=BG, fg=DIM, font=best_font(7)).pack()

    def load_file():
        path = filedialog.askopenfilename(
            parent=dialog,
            title="Load Previous NetPyWiz Session",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if path:
            result["load_file"] = path
            result["api_key"]   = api_var.get().strip()
            dialog.grab_release()
            dialog.destroy()

    tk.Button(dialog, text="📂  LOAD SESSION CSV", command=load_file,
        bg=BG3, fg=CYAN, font=best_font(9),
        relief="flat", cursor="hand2",
        activebackground=CYAN, activeforeground=BG, bd=0
    ).pack(pady=6, ipadx=16, ipady=4)

    # NVD API Key
    tk.Frame(dialog, bg=DIM, height=1).pack(fill="x", padx=30, pady=(8,0))
    api_frame = tk.Frame(dialog, bg=BG)
    api_frame.pack(fill="x", padx=50, pady=6)

    tk.Label(api_frame, text="NVD API KEY  (optional — faster CVE lookups)",
        bg=BG, fg=DIM, font=best_font(7)).pack(anchor="w")

    api_var = tk.StringVar(value=nvd_api_key)
    api_entry = tk.Entry(api_frame, textvariable=api_var,
        bg=BG3, fg=CYAN, insertbackground=CYAN,
        font=best_font(8), relief="flat", bd=0, show="*")
    api_entry.pack(fill="x", ipady=5)
    tk.Frame(api_frame, bg=DIM, height=1).pack(fill="x")

    tk.Label(api_frame,
        text="Register free at nvd.nist.gov/developers/request-an-api-key",
        bg=BG, fg=DIM, font=best_font(6)).pack(anchor="w", pady=(2,0))

    dialog.protocol("WM_DELETE_WINDOW", lambda: (
        result.update({"cancelled": True}),
        dialog.grab_release(),
        dialog.destroy()
    ))

    root.wait_window(dialog)
    return result


def run_splash_scan(root, subnet_str):
    found     = []
    scan_done = threading.Event()
    stop_anim = threading.Event()

    splash = tk.Toplevel(root)
    splash.title("NetPyWiz")
    splash.configure(bg=BG)
    splash.geometry("400x160")
    splash.resizable(False, False)
    splash.grab_set()
    splash.update_idletasks()
    x = (splash.winfo_screenwidth() // 2) - 200
    y = (splash.winfo_screenheight() // 2) - 80
    splash.geometry(f"+{x}+{y}")

    tk.Label(splash, text="▓▓ NETPYWIZ ▓▓",
        bg=BG, fg=MAGENTA, font=best_font(14, True)).pack(pady=(24,4))
    tk.Label(splash, text=f"SCANNING  {subnet_str} ...",
        bg=BG, fg=CYAN, font=best_font(10)).pack()
    tk.Label(splash, text="THIS MAY TAKE UP TO 30 SECONDS",
        bg=BG, fg=DIM, font=best_font(8)).pack(pady=4)

    dot_var = tk.StringVar(value="")
    tk.Label(splash, textvariable=dot_var, bg=BG, fg=MAGENTA,
        font=best_font(12)).pack()

    def run_scan():
        r = scan_subnet(subnet_str)
        for d in r:
            d["port"]   = d.get("port",  "")
            d["notes"]  = d.get("notes", "")
            d["subnet"] = subnet_str
        found.extend(r)
        stop_anim.set()
        scan_done.set()

    def animate_dots():
        if stop_anim.is_set():
            return
        dot_var.set("█" * ((len(dot_var.get()) % 8) + 1))
        splash.after(200, animate_dots)

    def poll_done():
        if scan_done.is_set():
            splash.grab_release()
            splash.destroy()
        else:
            splash.after(200, poll_done)

    threading.Thread(target=run_scan, daemon=True).start()
    splash.after(200, animate_dots)
    splash.after(200, poll_done)
    root.wait_window(splash)
    return found


def ask_rescan(root, subnet_str):
    result = {"choice": "cancel"}

    d = tk.Toplevel(root)
    d.title("NetPyWiz")
    d.configure(bg=BG)
    d.geometry("440x240")
    d.resizable(False, False)
    d.grab_set()
    d.update_idletasks()
    x = (d.winfo_screenwidth() // 2) - 220
    y = (d.winfo_screenheight() // 2) - 120
    d.geometry(f"+{x}+{y}")

    tk.Label(d, text="SESSION LOADED",
        bg=BG, fg=MAGENTA, font=best_font(13, True)).pack(pady=(24,4))
    tk.Label(d, text="Would you like to rescan the subnet\nto check for new devices?",
        bg=BG, fg="#e0e0ff", font=best_font(9), justify="center").pack(pady=4)
    tk.Label(d, text=f"◈  {subnet_str}",
        bg=BG, fg=CYAN, font=best_font(9)).pack(pady=4)
    tk.Frame(d, bg=MAGENTA, height=1).pack(fill="x", padx=30, pady=12)

    btn_frame = tk.Frame(d, bg=BG)
    btn_frame.pack()

    def do_rescan():
        result["choice"] = "rescan"
        d.grab_release()
        d.destroy()

    def monitor_only():
        result["choice"] = "monitor_only"
        d.grab_release()
        d.destroy()

    tk.Button(btn_frame, text="⟳  RESCAN + LOAD",
        command=do_rescan,
        bg=MAGENTA_DIM, fg=BG, font=best_font(9, True),
        relief="flat", cursor="hand2",
        activebackground=MAGENTA, activeforeground=BG, bd=0
    ).pack(side="left", padx=8, ipadx=12, ipady=6)

    tk.Button(btn_frame, text="▶  MONITOR LOADED ONLY",
        command=monitor_only,
        bg=BG3, fg=CYAN, font=best_font(9),
        relief="flat", cursor="hand2",
        activebackground=CYAN, activeforeground=BG, bd=0
    ).pack(side="left", padx=8, ipadx=12, ipady=6)

    root.wait_window(d)
    return result["choice"]


def ask_export_mode(root):
    result = {"choice": "cancel"}

    d = tk.Toplevel(root)
    d.title("NetPyWiz — Export")
    d.configure(bg=BG)
    d.geometry("420x220")
    d.resizable(False, False)
    d.grab_set()
    d.update_idletasks()
    x = (d.winfo_screenwidth() // 2) - 210
    y = (d.winfo_screenheight() // 2) - 110
    d.geometry(f"+{x}+{y}")

    tk.Label(d, text="EXPORT SESSION",
        bg=BG, fg=MAGENTA, font=best_font(13, True)).pack(pady=(24,4))
    tk.Label(d,
        text="A previous session file was loaded.\nAppend this session or create a new file?",
        bg=BG, fg="#e0e0ff", font=best_font(9), justify="center").pack(pady=4)
    tk.Frame(d, bg=MAGENTA, height=1).pack(fill="x", padx=30, pady=12)

    btn_frame = tk.Frame(d, bg=BG)
    btn_frame.pack()

    def do_append():
        result["choice"] = "append"
        d.grab_release()
        d.destroy()

    def do_new():
        result["choice"] = "new"
        d.grab_release()
        d.destroy()

    tk.Button(btn_frame, text="+ APPEND TO EXISTING",
        command=do_append,
        bg=BG3, fg=CYAN, font=best_font(9),
        relief="flat", cursor="hand2",
        activebackground=CYAN, activeforeground=BG, bd=0
    ).pack(side="left", padx=8, ipadx=12, ipady=6)

    tk.Button(btn_frame, text="★ NEW REPORT",
        command=do_new,
        bg=MAGENTA_DIM, fg=BG, font=best_font(9, True),
        relief="flat", cursor="hand2",
        activebackground=MAGENTA, activeforeground=BG, bd=0
    ).pack(side="left", padx=8, ipadx=12, ipady=6)

    root.wait_window(d)
    return result["choice"]
