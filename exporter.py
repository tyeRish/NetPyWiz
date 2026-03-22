import csv
import os
from datetime import datetime
from monitor import status, status_lock

import platform

def get_real_user():
    # On Linux with sudo, SUDO_USER has the real username
    # On Windows, use USERNAME env var
    return (os.environ.get("SUDO_USER") or
            os.environ.get("USER") or
            os.environ.get("USERNAME") or
            "user")

def get_desktop_path():
    if platform.system() == "Windows":
        # Windows Desktop path
        desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\Users\\user"), "Desktop")
    else:
        real_user = get_real_user()
        desktop   = f"/home/{real_user}/Desktop"
    os.makedirs(desktop, exist_ok=True)
    return desktop

def fix_ownership(path: str):
    """Fix ownership on Linux only — not needed on Windows."""
    if platform.system() == "Windows":
        return
    try:
        import pwd
        real_user = get_real_user()
        pw        = pwd.getpwnam(real_user)
        uid, gid  = pw.pw_uid, pw.pw_gid
        if os.path.isdir(path):
            for root_dir, dirs, files in os.walk(path):
                os.chown(root_dir, uid, gid)
                for f in files:
                    os.chown(os.path.join(root_dir, f), uid, gid)
        else:
            os.chown(path, uid, gid)
    except Exception as e:
        print(f"Could not fix ownership: {e}")

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
    fix_ownership(folder)
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
                "Session", "IP", "MAC", "Hostname", "Alias", "Vendor",
                "Switch Port", "Patch Panel", "Status", "Last Latency (ms)",
                "Avg Latency (ms)", "Total Downtime (s)",
                "Vulnerabilities", "Notes"
            ])
        for d in devices:
            ip    = d["ip"]
            s     = current.get(ip, {})
            alive = s.get("alive")
            has_vuln = "YES" if ip in vuln_devices else "NO"
            writer.writerow([
                timestamp, ip, d["mac"], d["hostname"], d.get("alias", ""), d["vendor"],
                d.get("port",        ""),
                d.get("patch_panel", ""),
                "ONLINE" if alive else "OFFLINE" if alive is False else "UNKNOWN",
                s.get("latency")     or "",
                s.get("avg_latency") or "",
                s.get("downtime", 0),
                has_vuln,
                d.get("notes", "")
            ])

    fix_ownership(filepath)
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
                    "ip":          row.get("IP",           "").strip(),
                    "mac":         mac,
                    "hostname":    row.get("Hostname",     "").strip(),
                    "alias":       row.get("Alias",        "").strip(),
                    "vendor":      row.get("Vendor",       "").strip(),
                    "port":        row.get("Switch Port",  "").strip(),
                    "patch_panel": row.get("Patch Panel",  "").strip(),
                    "notes":       row.get("Notes",        "").strip(),
                    "previous":    True
                })
    except Exception as e:
        print(f"Failed to load session: {e}")
    return devices
