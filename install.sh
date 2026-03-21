#!/bin/bash

# ── NetPyWiz Installer ────────────────────────────────────────────────────────
set -e

REPO="https://github.com/tyeRish/NetPyWiz"
BINARY_URL="$REPO/releases/latest/download/NetPyWiz"
INSTALL_DIR="/usr/local/bin"
POLICY_DIR="/usr/share/polkit-1/actions"
DESKTOP_DIR="/usr/share/applications"

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

echo ""
echo -e "${MAGENTA}▓▓ NETPYWIZ // INSTALLER ▓▓${NC}"
echo -e "${CYAN}────────────────────────────${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}ERROR: Run with sudo${NC}"
    echo "curl -sSL $REPO/raw/main/install.sh | sudo bash"
    exit 1
fi

if [ -f /etc/debian_version ]; then
    OS="debian"
elif [ -f /etc/arch-release ]; then
    OS="arch"
elif [ -f /etc/fedora-release ]; then
    OS="fedora"
else
    OS="unknown"
fi

echo -e "► ${CYAN}Detected OS:${NC} $OS"
echo -e "► ${CYAN}Installing dependencies...${NC}"

if [ "$OS" = "debian" ]; then
    apt-get update -qq
    apt-get install -y -qq libpcap-dev ieee-data nmap policykit-1 curl
elif [ "$OS" = "arch" ]; then
    pacman -Sy --noconfirm libpcap nmap polkit curl
elif [ "$OS" = "fedora" ]; then
    dnf install -y -q libpcap nmap polkit curl
else
    echo -e "${RED}WARNING: Unknown OS — install libpcap and nmap manually if needed${NC}"
fi

echo -e "► ${CYAN}Downloading NetPyWiz...${NC}"
curl -sSL "$BINARY_URL" -o "$INSTALL_DIR/NetPyWiz"
chmod +x "$INSTALL_DIR/NetPyWiz"

echo -e "► ${CYAN}Creating desktop launcher...${NC}"
tee "$DESKTOP_DIR/netpywiz.desktop" > /dev/null << 'DESKTOP'
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

echo -e "► ${CYAN}Installing privilege policy...${NC}"
tee "$POLICY_DIR/com.netpywiz.policy" > /dev/null << 'POLICY'
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

update-desktop-database 2>/dev/null || true

echo ""
echo -e "${MAGENTA}▓▓ NETPYWIZ INSTALLED ▓▓${NC}"
echo -e "${CYAN}────────────────────────────${NC}"
echo -e "  ${GREEN}Run from terminal:${NC}  sudo NetPyWiz"
echo -e "  ${GREEN}Or search:${NC}          NetPyWiz in your app menu"
echo ""
