import json
from scanner import scan_subnet

print("Scanning subnet...")
devices = scan_subnet("10.55.0.0/24")

with open("devices.json", "w") as f:
    json.dump(devices, f, indent=2)

print(f"Saved {len(devices)} devices to devices.json")
for d in devices:
    print(f"  {d['ip']:<16} {d['mac']:<20} {d['hostname']:<30} {d['vendor']}")
