# NetPyWiz — Network Monitor & Security Tool

A portable, professional network monitoring and security reconnaissance tool for Linux.

## Features

- Live subnet monitoring with real-time ping status
- ARP discovery — IP, MAC, hostname, vendor
- Latency tracking with sparkline graphs
- nmap port scanning + OS detection
- CVE vulnerability lookup per device
- Firewall detection
- Subnet auto-discovery
- Multi-subnet tab support
- Wake on LAN
- Device aliases + switch port labeling
- Session save/load with new device detection
- Per-device vulnerability reports
- CSV export

## Install (Linux)
```bash
curl -sSL https://raw.githubusercontent.com/tyeRish/NetPyWiz/main/install.sh | sudo bash
```

## Requirements

- Linux (Debian/Ubuntu/Mint/Arch/Fedora)
- Must run as root (raw socket access for ARP/ICMP)
- Internet connection for CVE lookups (optional — cached after first lookup)

## Run
```bash
sudo NetPyWiz
```

Or click NetPyWiz in your app menu.

## Usage

1. Enter subnet in CIDR format e.g. `192.168.1.0/24`
2. Or use **Auto-Discover** to find active subnets automatically
3. Monitor devices in real time
4. Click a device to inspect — double-click for full detail + port scan
5. Right-click for quick actions — copy IP/MAC, WOL, set alias
6. **End Session + Export** saves CSV + vulnerability reports to Desktop

## License

MIT
