import tkinter as tk
from tkinter import ttk
import threading
import ipaddress
import subprocess
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def ping_host(host: str) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", host],
            capture_output=True, timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def probe_subnet(subnet_str: str) -> bool:
    """
    Probes multiple addresses in the subnet.
    Requires at least 2 hosts to respond to avoid false positives
    from proxy ARP / ICMP redirects.
    Checks .1, .254, .2, .253 — common gateway addresses.
    """
    try:
        network = ipaddress.ip_network(subnet_str, strict=False)
        hosts   = list(network.hosts())
        if not hosts:
            return False

        # Build candidate list — .1, .254, .2, .253
        candidates = []
        for idx in [0, -1, 1, -2]:
            try:
                candidates.append(str(hosts[idx]))
            except IndexError:
                pass
        # Remove duplicates
        seen = set()
        candidates = [c for c in candidates if not (c in seen or seen.add(c))]

        # Ping all candidates in parallel
        responses = 0
        with ThreadPoolExecutor(max_workers=4) as ex:
            results = list(ex.map(ping_host, candidates))
        responses = sum(1 for r in results if r)

        # Require at least 2 responses to confirm subnet is active
        # This eliminates false positives from proxy ARP
        return responses >= 2
    except Exception:
        return False


def generate_subnets(cidr: str) -> list:
    try:
        network = ipaddress.ip_network(cidr, strict=False)
        if network.prefixlen >= 24:
            return [str(network)]
        return [str(sn) for sn in network.subnets(new_prefix=24)]
    except Exception:
        return []


def estimate_time(count: int) -> str:
    seconds = (count / 100) * 2  # ~2s per subnet with 2-host check
    if seconds < 60:
        return f"~{int(seconds)} seconds"
    mins = seconds / 60
    if mins < 60:
        return f"~{int(mins)} minute{'s' if mins >= 2 else ''}"
    return f"~{int(mins/60)}h {int(mins%60)}m"


def draw_coffee_cup(canvas, x, y, size=40):
    """
    Draws a pixel-art style coffee cup in the synthwave theme.
    Styled like the ethernet port logo — geometric, cyan/magenta.
    """
    s = size / 40  # scale factor

    # Cup body
    canvas.create_rectangle(
        x, y + 12*s, x + 28*s, y + 36*s,
        outline=CYAN, width=2, fill=BG3)

    # Cup rim
    canvas.create_rectangle(
        x - 2*s, y + 10*s, x + 30*s, y + 14*s,
        outline=CYAN, width=1, fill=BG2)

    # Handle
    canvas.create_arc(
        x + 24*s, y + 16*s, x + 38*s, y + 30*s,
        start=270, extent=180,
        outline=MAGENTA, width=2, style="arc")

    # Coffee liquid inside
    canvas.create_rectangle(
        x + 3*s, y + 16*s, x + 25*s, y + 22*s,
        outline="", fill=AMBER)

    # Saucer
    canvas.create_oval(
        x - 4*s, y + 33*s, x + 32*s, y + 40*s,
        outline=CYAN, width=1, fill=BG2)

    # Steam lines — animated separately
    return canvas


def animate_steam(canvas, x, y, size, frame, after_fn):
    """Draws animated steam above the cup."""
    canvas.delete("steam")
    s = size / 40

    # Three steam wisps with sine wave offset
    for i, ox in enumerate([6, 14, 22]):
        phase  = (frame + i * 8) % 30
        offset = math.sin(phase * 0.4) * 3 * s
        alpha  = max(0, 1 - phase / 30)

        # Steam as small vertical lines that drift and fade
        y_start = y + (8 - phase * 0.2) * s
        y_end   = y + (2 - phase * 0.2) * s
        if y_end < y - 10*s:
            continue

        col = CYAN if i % 2 == 0 else MAGENTA
        canvas.create_line(
            x + ox*s + offset, y_start,
            x + ox*s + offset * 0.5, y_end,
            fill=col, width=max(1, int(2*s)),
            tags="steam", smooth=True)

    after_fn(50, lambda: animate_steam(
        canvas, x, y, size, (frame + 1) % 30, after_fn))


def run_discovery_dialog(root) -> list:
    selected = []

    # ── Range input ───────────────────────────────────────────────────────────
    range_result = {"cidr": None, "cancelled": False}

    rd = tk.Toplevel(root)
    rd.title("NetPyWiz — Subnet Discovery")
    rd.configure(bg=BG)
    rd.geometry("520x420")
    rd.resizable(False, False)
    rd.grab_set()
    rd.update_idletasks()
    x = (rd.winfo_screenwidth() // 2) - 260
    y = (rd.winfo_screenheight() // 2) - 210
    rd.geometry(f"+{x}+{y}")

    tk.Label(rd, text="▓▓ SUBNET DISCOVERY ▓▓",
        bg=BG, fg=MAGENTA, font=best_font(13, True)).pack(pady=(20,4))
    tk.Label(rd, text="SCAN A RANGE FOR ACTIVE SUBNETS",
        bg=BG, fg=CYAN, font=best_font(9)).pack()
    tk.Frame(rd, bg=MAGENTA, height=1).pack(fill="x", padx=30, pady=10)

    tk.Label(rd, text="Enter a CIDR range to sweep",
        bg=BG, fg=DIM, font=best_font(8)).pack()

    entry_var = tk.StringVar(value="192.168.0.0/16")
    entry = tk.Entry(rd, textvariable=entry_var,
        bg=BG3, fg=CYAN, insertbackground=CYAN, selectbackground=MAGENTA,
        font=best_font(12), relief="flat", justify="center", bd=0)
    entry.pack(padx=50, pady=8, ipady=8, fill="x")
    entry.select_range(0, "end")
    entry.focus()
    tk.Frame(rd, bg=CYAN, height=1).pack(fill="x", padx=50)

    # Live estimate
    estimate_var = tk.StringVar(value="")
    tk.Label(rd, textvariable=estimate_var,
        bg=BG, fg=AMBER, font=best_font(8)).pack(pady=4)

    def update_estimate(*args):
        try:
            subs = generate_subnets(entry_var.get().strip())
            if subs:
                estimate_var.set(
                    f"{len(subs)} subnets  ·  {estimate_time(len(subs))}")
            else:
                estimate_var.set("⚠ Invalid CIDR")
        except Exception:
            estimate_var.set("")

    entry_var.trace_add("write", update_estimate)
    update_estimate()

    # Presets
    preset_frame = tk.Frame(rd, bg=BG)
    preset_frame.pack(pady=4)
    tk.Label(preset_frame, text="QUICK:",
        bg=BG, fg=DIM, font=best_font(7)).pack(side="left", padx=4)
    for preset in ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]:
        tk.Button(preset_frame, text=preset,
            command=lambda p=preset: entry_var.set(p),
            bg=BG3, fg=AMBER, font=best_font(7),
            relief="flat", cursor="hand2",
            activebackground=AMBER, activeforeground=BG, bd=0
        ).pack(side="left", padx=4, ipadx=6, ipady=2)

    def confirm_range(event=None):
        range_result["cidr"] = entry_var.get().strip()
        rd.grab_release()
        rd.destroy()

    def cancel_range():
        range_result["cancelled"] = True
        rd.grab_release()
        rd.destroy()

    entry.bind("<Return>",   confirm_range)
    entry.bind("<KP_Enter>", confirm_range)
    rd.protocol("WM_DELETE_WINDOW", cancel_range)

    tk.Button(rd, text="🔍  START SWEEP",
        command=confirm_range,
        bg=MAGENTA_DIM, fg=BG, font=best_font(10, True),
        relief="flat", cursor="hand2",
        activebackground=MAGENTA, activeforeground=BG, bd=0
    ).pack(pady=10, ipadx=20, ipady=6)

    root.wait_window(rd)

    if range_result["cancelled"] or not range_result["cidr"]:
        return []

    cidr             = range_result["cidr"]
    subnets_to_probe = generate_subnets(cidr)
    total            = len(subnets_to_probe)

    if not subnets_to_probe:
        return []

    # ── Discovery dialog ──────────────────────────────────────────────────────
    dd = tk.Toplevel(root)
    dd.title("NetPyWiz — Discovering Subnets")
    dd.configure(bg=BG)
    dd.geometry("600x640")
    dd.resizable(True, True)
    dd.grab_set()
    dd.update_idletasks()
    x = (dd.winfo_screenwidth() // 2) - 300
    y = (dd.winfo_screenheight() // 2) - 320
    dd.geometry(f"+{x}+{y}")

    # Header with coffee cup
    hdr = tk.Frame(dd, bg=BG)
    hdr.pack(fill="x", padx=20, pady=(16,4))

    cup_canvas = tk.Canvas(hdr, width=50, height=52,
        bg=BG, highlightthickness=0)
    cup_canvas.pack(side="left", padx=(0,12))
    draw_coffee_cup(cup_canvas, 5, 5, size=40)
    animate_steam(cup_canvas, 5, 5, 40, 0, cup_canvas.after)

    msg_frame = tk.Frame(hdr, bg=BG)
    msg_frame.pack(side="left", fill="x", expand=True)

    tk.Label(msg_frame, text="▓▓ SUBNET DISCOVERY ▓▓",
        bg=BG, fg=MAGENTA, font=best_font(13, True), anchor="w").pack(anchor="w")

    est = estimate_time(total)
    tk.Label(msg_frame,
        text=f"This will take {est} — go grab yourself a coffee ☕",
        bg=BG, fg=AMBER, font=best_font(8), anchor="w").pack(anchor="w")
    tk.Label(msg_frame,
        text=f"Scanning {cidr}  ·  {total} subnets  ·  requires 2+ hosts to confirm",
        bg=BG, fg=DIM, font=best_font(7), anchor="w").pack(anchor="w")

    tk.Frame(dd, bg=MAGENTA, height=1).pack(fill="x", padx=20, pady=6)

    progress_var = tk.StringVar(value=f"SWEEPING  {cidr} ...")
    tk.Label(dd, textvariable=progress_var,
        bg=BG, fg=CYAN, font=best_font(9)).pack()

    stats_var = tk.StringVar(value=f"0 / {total} probed  ·  0 found")
    tk.Label(dd, textvariable=stats_var,
        bg=BG, fg=DIM, font=best_font(8)).pack(pady=2)

    # Progress bar
    pb_outer = tk.Frame(dd, bg=BG2, height=18)
    pb_outer.pack(fill="x", padx=20, pady=(4,0))
    pb_outer.pack_propagate(False)
    pb_fill = tk.Frame(pb_outer, bg=CYAN, height=18)
    pb_fill.place(x=0, y=0, relheight=1.0, width=0)

    pct_var = tk.StringVar(value="0%")
    tk.Label(dd, textvariable=pct_var,
        bg=BG, fg=CYAN, font=best_font(8, True)).pack(pady=2)

    tk.Frame(dd, bg=MAGENTA, height=1).pack(fill="x", padx=20, pady=4)
    tk.Label(dd, text="ACTIVE SUBNETS FOUND:",
        bg=BG, fg=CYAN, font=best_font(8, True)).pack(anchor="w", padx=20)

    list_frame = tk.Frame(dd, bg=BG)
    list_frame.pack(fill="both", expand=True, padx=20, pady=4)

    sb2     = ttk.Scrollbar(list_frame, orient="vertical")
    listbox = tk.Listbox(list_frame,
        bg=BG3, fg=GREEN, selectbackground=MAGENTA_DIM,
        selectforeground=WHITE, font=best_font(10),
        relief="flat", bd=0,
        yscrollcommand=sb2.set,
        selectmode=tk.MULTIPLE)
    sb2.config(command=listbox.yview)
    listbox.pack(side="left", fill="both", expand=True)
    sb2.pack(side="right", fill="y")

    tk.Label(dd,
        text="Click to select/deselect  ·  None pre-selected — choose what to monitor",
        bg=BG, fg=DIM, font=best_font(7)).pack(pady=2)

    # Buttons — stop/pause + confirm + cancel
    btn_frame = tk.Frame(dd, bg=BG)
    btn_frame.pack(pady=6)

    stop_btn = tk.Button(btn_frame,
        text="⏸  PAUSE SCAN",
        bg=BG3, fg=AMBER, font=best_font(9),
        relief="flat", cursor="hand2",
        activebackground=AMBER, activeforeground=BG, bd=0)
    stop_btn.pack(side="left", padx=6, ipadx=10, ipady=5)

    confirm_btn = tk.Button(btn_frame,
        text="▶  MONITOR SELECTED",
        state="disabled",
        bg=MAGENTA_DIM, fg=BG, font=best_font(9, True),
        relief="flat", cursor="hand2",
        activebackground=MAGENTA, activeforeground=BG, bd=0)
    confirm_btn.pack(side="left", padx=6, ipadx=10, ipady=5)

    cancel_btn = tk.Button(btn_frame, text="✕  CANCEL",
        bg=BG3, fg=RED, font=best_font(9),
        relief="flat", cursor="hand2",
        activebackground=RED, activeforeground=BG, bd=0)
    cancel_btn.pack(side="left", padx=6, ipadx=10, ipady=5)

    # Shared state
    state = {
        "probed":    0,
        "found":     [],
        "done":      False,
        "cancelled": False,
        "paused":    False,
    }
    state_lock = threading.Lock()

    def on_confirm():
        with state_lock:
            state["cancelled"] = True
        idxs = listbox.curselection()
        for i in idxs:
            selected.append(listbox.get(i))
        dd.grab_release()
        dd.destroy()

    def on_cancel():
        with state_lock:
            state["cancelled"] = True
        dd.grab_release()
        dd.destroy()

    def on_stop_pause():
        with state_lock:
            paused = state["paused"]
            state["paused"] = not paused
        if paused:
            stop_btn.config(text="⏸  PAUSE SCAN", fg=AMBER)
        else:
            stop_btn.config(text="▶  RESUME SCAN", fg=GREEN)
            # Enable confirm immediately when paused
            confirm_btn.config(state="normal")

    confirm_btn.config(command=on_confirm)
    cancel_btn.config(command=on_cancel)
    stop_btn.config(command=on_stop_pause)
    dd.protocol("WM_DELETE_WINDOW", on_cancel)

    def probe_worker(sn):
        # Respect pause — wait until resumed
        while True:
            with state_lock:
                if state["cancelled"]:
                    return
                if not state["paused"]:
                    break
            threading.Event().wait(0.2)

        with state_lock:
            if state["cancelled"]:
                return

        alive = probe_subnet(sn)

        with state_lock:
            state["probed"] += 1
            if alive:
                state["found"].append(sn)

    def run_sweep():
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(probe_worker, sn)
                       for sn in subnets_to_probe]
            for f in as_completed(futures):
                with state_lock:
                    if state["cancelled"]:
                        for pending in futures:
                            pending.cancel()
                        break
        with state_lock:
            state["done"] = True

    # Poll state from main thread
    displayed = {"count": 0}

    def poll_state():
        if not dd.winfo_exists():
            return

        with state_lock:
            probed    = state["probed"]
            found     = list(state["found"])
            done      = state["done"]
            cancelled = state["cancelled"]
            paused    = state["paused"]

        # Add new results
        for i in range(displayed["count"], len(found)):
            listbox.insert(tk.END, found[i])
            # NOT pre-selected — user picks manually
            listbox.see(tk.END)
            displayed["count"] += 1

        # Update progress bar
        pct   = int((probed / total) * 100) if total > 0 else 0
        dd.update_idletasks()
        bar_w  = pb_outer.winfo_width()
        fill_w = max(int(bar_w * pct / 100), 0)
        pb_fill.place(x=0, y=0, relheight=1.0, width=fill_w)

        if done:
            pb_fill.config(bg=GREEN)
        elif paused:
            pb_fill.config(bg=AMBER)
        else:
            pb_fill.config(bg=CYAN)

        stats_var.set(f"{probed} / {total} probed  ·  {len(found)} found")
        pct_var.set(f"{pct}%")

        if done or cancelled:
            progress_var.set("◈ SWEEP COMPLETE" if done else "◈ PAUSED / STOPPED")
            confirm_btn.config(state="normal")
            stop_btn.config(state="disabled")
            if done and len(found) == 0:
                progress_var.set("⚠  NO ACTIVE SUBNETS FOUND")
                progress_var_label = tk.Label(dd,
                    text="Try a different range",
                    bg=BG, fg=DIM, font=best_font(8))
            return

        dd.after(200, poll_state)

    threading.Thread(target=run_sweep, daemon=True).start()
    dd.after(200, poll_state)
    root.wait_window(dd)

    with state_lock:
        state["cancelled"] = True

    return selected
