import csv
import os
from datetime import datetime
from monitor import status, status_lock

def get_desktop_path():
    real_user = os.environ.get("SUDO_USER") or os.environ.get("USER")
    desktop   = f"/home/{real_user}/Desktop"
    os.makedirs(desktop, exist_ok=True)
    return desktop

def subnet_to_filename(subnet: str) -> str:
    return subnet.replace("/", "-")

def create_session_folder(subnet: str) -> str:
    """Creates and returns a timestamped session folder on Desktop."""
    timestamp  = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    subnet_str = subnet_to_filename(subnet)
    folder     = os.path.join(
        get_desktop_path(),
        f"NetPyWiz_{subnet_str}_{timestamp}"
    )
    os.makedirs(folder, exist_ok=True)
    return folder

def export_to_desktop(devices: list[dict], append_to: str = None,
                      subnet: str = "unknown",
                      vuln_devices: set = None,
                      folder: str = None) -> str:
    """
    Exports session CSV. If folder is provided, saves inside it.
    vuln_devices is a set of IPs that have vulnerabilities.
    """
    with status_lock:
        current = dict(status)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if append_to:
        filepath     = append_to
        write_mode   = "a"
        write_header = False
    else:
        if folder:
            filepath = os.path.join(folder, "session_report.csv")
        else:
            subnet_str = subnet_to_filename(subnet)
            filepath   = os.path.join(
                get_desktop_path(),
                f"NetPyWiz_{subnet_str}_{timestamp}.csv"
            )
        write_mode   = "w"
        write_header = True

    vuln_devices = vuln_devices or set()

    with open(filepath, write_mode, newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "Session", "IP", "MAC", "Hostname", "Vendor",
                "Switch Port", "Status", "Last Latency (ms)",
                "Avg Latency (ms)", "Total Downtime (s)",
                "Vulnerabilities", "Notes"
            ])
        for d in devices:
            ip    = d["ip"]
            s     = current.get(ip, {})
            alive = s.get("alive")
            has_vuln = "YES" if ip in vuln_devices else "NO"
            writer.writerow([
                timestamp, ip, d["mac"], d["hostname"], d["vendor"],
                d.get("port",  ""),
                "ONLINE" if alive else "OFFLINE" if alive is False else "UNKNOWN",
                s.get("latency")     or "",
                s.get("avg_latency") or "",
                s.get("downtime", 0),
                has_vuln,
                d.get("notes", "")
            ])

    print(f"{'Appended' if append_to else 'Exported'} to {filepath}")
    return filepath


def load_session_csv(filepath: str) -> list[dict]:
    devices   = []
    seen_macs = set()
    try:
        with open(filepath, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mac = row.get("MAC", "").strip()
                if mac in seen_macs:
                    continue
                seen_macs.add(mac)
                devices.append({
                    "ip":       row.get("IP",          "").strip(),
                    "mac":      mac,
                    "hostname": row.get("Hostname",    "").strip(),
                    "vendor":   row.get("Vendor",      "").strip(),
                    "port":     row.get("Switch Port", "").strip(),
                    "notes":    row.get("Notes",       "").strip(),
                    "previous": True
                })
    except Exception as e:
        print(f"Failed to load session: {e}")
    return devices
