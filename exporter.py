import csv
import os
from datetime import datetime
from monitor import status, status_lock

def export_to_desktop(devices: list[dict]):
    real_user = os.environ.get("SUDO_USER") or os.environ.get("USER")
    desktop   = f"/home/{real_user}/Desktop"
    os.makedirs(desktop, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath  = os.path.join(desktop, f"NetPyWiz_Session_{timestamp}.csv")

    with status_lock:
        current = dict(status)

    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "IP", "MAC", "Hostname", "Vendor", "Switch Port",
            "Status", "Last Latency (ms)", "Avg Latency (ms)",
            "Total Downtime (s)", "Notes"
        ])
        for d in devices:
            ip = d["ip"]
            s  = current.get(ip, {})
            alive = s.get("alive")
            writer.writerow([
                ip,
                d["mac"],
                d["hostname"],
                d["vendor"],
                d.get("port", ""),
                "ONLINE" if alive else "OFFLINE" if alive is False else "UNKNOWN",
                s.get("latency")     or "",
                s.get("avg_latency") or "",
                s.get("downtime", 0),
                d.get("notes", "")
            ])

    print(f"Exported to {filepath}")
    return filepath
