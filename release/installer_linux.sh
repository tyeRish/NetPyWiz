#!/bin/bash

# ── NetPyWiz Linux Installer ──────────────────────────────────────────────────
APP_NAME="NetPyWiz"
INSTALL_DIR="/usr/local/bin"
BINARY="dist/NetPyWiz"

echo ""
echo "▓▓ NETPYWIZ // INSTALLER ▓▓"
echo "────────────────────────────"

# Check running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root: sudo bash installer_linux.sh"
    exit 1
fi

# Check binary exists
if [ ! -f "$BINARY" ]; then
    echo "ERROR: dist/NetPyWiz not found. Run PyInstaller first."
    exit 1
fi

echo "► Checking dependencies..."

# Check and install ieee-data for vendor lookup
if ! dpkg -l ieee-data &>/dev/null; then
    echo "  Installing ieee-data (MAC vendor database)..."
    apt install -y ieee-data
else
    echo "  ieee-data: OK"
fi

# Check and install Npcap/libpcap for Scapy
if ! dpkg -l libpcap-dev &>/dev/null; then
    echo "  Installing libpcap (required for Scapy)..."
    apt install -y libpcap-dev
else
    echo "  libpcap: OK"
fi

echo "► Installing NetPyWiz to $INSTALL_DIR..."
cp "$BINARY" "$INSTALL_DIR/NetPyWiz"
chmod +x "$INSTALL_DIR/NetPyWiz"

echo "► Creating desktop shortcut..."
cat > /usr/share/applications/netpywiz.desktop << 'DESKTOP'
[Desktop Entry]
Name=NetPyWiz
GenericName=Network Monitor
Comment=Network monitoring and security reconnaissance tool
Exec=pkexec /usr/local/bin/NetPyWiz
Icon=network-wired
Terminal=false
Type=Application
Categories=Network;Security;
StartupNotify=true
DESKTOP

echo "► Installing pkexec policy..."
cat > /usr/share/polkit-1/actions/com.netpywiz.policy << 'POLICY'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="com.netpywiz.run">
    <description>Run NetPyWiz Network Monitor</description>
    <message>NetPyWiz requires administrator privileges for network scanning</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>auth_admin</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/local/bin/NetPyWiz</annotate>
    <annotate key="org.freedesktop.policykit.exec.allow_gui">true</annotate>
  </action>
</policyconfig>
POLICY

echo ""
echo "────────────────────────────"
echo "✓ NetPyWiz installed successfully!"
echo ""
echo "  Run from terminal:  sudo NetPyWiz"
echo "  Or from app menu:   search NetPyWiz"
echo ""
