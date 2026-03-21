from pysnmp.hlapi import (
    getCmd, SnmpEngine, CommunityData,
    UdpTransportTarget, ContextData, ObjectType, ObjectIdentity
)

# Standard SNMP OIDs for finding what port a MAC is on
# These are bridge MIB OIDs — supported by most managed switches
# OID translates MAC address to bridge port number
MAC_TO_PORT_OID = "1.3.6.1.2.1.17.4.3.1.2"
PORT_TO_IFINDEX_OID = "1.3.6.1.2.1.17.1.4.1.2"
IFINDEX_TO_NAME_OID = "1.3.6.1.2.1.31.1.1.1.1"

def mac_to_oid_suffix(mac: str) -> str:
    # Convert "aa:bb:cc:dd:ee:ff" to "170.187.204.221.238.255"
    # SNMP bridge MIB uses MAC as OID suffix in decimal
    return ".".join(str(int(x, 16)) for x in mac.split(":"))

def get_switch_port(switch_ip: str, mac: str, community: str = "public") -> str | None:
    """
    Asks the switch at switch_ip what port the given MAC is on.
    Returns port name string or None if unreachable/unsupported.
    community defaults to 'public' — most common default
    """
    try:
        mac_suffix = mac_to_oid_suffix(mac)
        full_oid = f"{MAC_TO_PORT_OID}.{mac_suffix}"

        # Send SNMP GET request — timeout=2, retries=1 keeps it fast
        error_indication, error_status, _, var_binds = next(
            getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((switch_ip, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(full_oid))
            )
        )

        if error_indication or error_status:
            return None

        # var_binds[0][1] is the bridge port number
        bridge_port = int(var_binds[0][1])

        # Now look up the interface name from the bridge port number
        ifindex_oid = f"{PORT_TO_IFINDEX_OID}.{bridge_port}"
        _, _, _, vb2 = next(
            getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((switch_ip, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(ifindex_oid))
            )
        )
        ifindex = int(vb2[0][1])

        # Finally get the human readable port name e.g. "GigabitEthernet0/1"
        name_oid = f"{IFINDEX_TO_NAME_OID}.{ifindex}"
        _, _, _, vb3 = next(
            getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((switch_ip, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(name_oid))
            )
        )
        return str(vb3[0][1])

    except Exception:
        return None
