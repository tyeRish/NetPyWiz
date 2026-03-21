import socket
import struct

def send_magic_packet(mac: str, broadcast: str = "255.255.255.255", port: int = 9) -> bool:
    """
    Sends a Wake on LAN magic packet to the given MAC address.
    The magic packet is: 6 bytes of 0xFF followed by the MAC repeated 16 times.
    Broadcast address can be subnet-specific e.g. 10.55.0.255 for better delivery.
    """
    try:
        # Clean MAC — remove colons, dashes, spaces
        mac_clean = mac.replace(":", "").replace("-", "").replace(" ", "")
        if len(mac_clean) != 12:
            return False

        # Build magic packet
        mac_bytes   = bytes.fromhex(mac_clean)
        magic       = b'\xff' * 6 + mac_bytes * 16

        # Send via UDP broadcast
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(2)
        sock.sendto(magic, (broadcast, port))
        sock.close()
        return True

    except Exception as e:
        print(f"WOL error: {e}")
        return False


def get_broadcast(ip: str) -> str:
    """
    Derives the broadcast address from a device IP.
    e.g. 10.55.0.11 -> 10.55.0.255
    Subnet-specific broadcast is more reliable than 255.255.255.255
    """
    try:
        parts    = ip.split(".")
        parts[3] = "255"
        return ".".join(parts)
    except Exception:
        return "255.255.255.255"
