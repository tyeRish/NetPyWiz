from scapy.all import ARP, Ether, srp
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Vendor lookup using system OUI database — no async issues
def get_vendor(mac: str) -> str:
    try:
        mac_clean = mac.upper().replace(":", "-")[:8]
        result = subprocess.run(
            ["grep", "-i", mac_clean, "/usr/share/ieee-data/oui.txt"],
            capture_output=True, text=True, timeout=1
        )
        if result.stdout:
            parts = result.stdout.strip().split("\t")
            return parts[-1].strip() if parts else "Unknown"
        return "Unknown"
    except Exception:
        return "Unknown"

def get_hostname(ip: str) -> str:
    try:
        result = socket.getnameinfo((ip, 0), socket.NI_NAMEREQD)
        return result[0]
    except Exception:
        return ip

def enrich_device(ip: str, mac: str) -> dict:
    return {
        "ip": ip,
        "mac": mac,
        "hostname": get_hostname(ip),
        "vendor": get_vendor(mac)
    }

def scan_subnet(subnet: str) -> list[dict]:
    arp = ARP(pdst=subnet)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp
    answered, _ = srp(packet, timeout=2, verbose=0)

    raw = [(r.psrc, r.hwsrc) for _, r in answered]

    devices = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(enrich_device, ip, mac): ip for ip, mac in raw}
        for future in as_completed(futures):
            devices.append(future.result())

    devices.sort(key=lambda d: list(map(int, d["ip"].split("."))))
    return devices

if __name__ == "__main__":
    results = scan_subnet("10.55.0.0/24")
    for d in results:
        print(f"IP: {d['ip']:<16} MAC: {d['mac']:<20} Host: {d['hostname']:<30} Vendor: {d['vendor']}")
