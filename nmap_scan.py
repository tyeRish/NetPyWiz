import subprocess
import xml.etree.ElementTree as ET

def run_nmap(ip: str) -> dict:
    """
    Runs nmap against a single IP.
    Returns dict with ports and os_guess.
    Uses -O for OS detection, -sV for service versions.
    XML output is easiest to parse reliably.
    """
    try:
        result = subprocess.run([
            "nmap",
            "-O",          # OS detection
            "-sV",         # service version detection
            "--open",      # only show open ports
            "-T4",         # aggressive timing — faster scan
            "-oX", "-",    # output XML to stdout
            ip
        ], capture_output=True, text=True, timeout=60)

        return parse_nmap_xml(result.stdout)

    except subprocess.TimeoutExpired:
        return {"ports": [], "os_guess": "Scan timed out"}
    except Exception as e:
        return {"ports": [], "os_guess": f"Error: {e}"}

def parse_nmap_xml(xml_str: str) -> dict:
    ports    = []
    os_guess = "Unknown"

    try:
        root = ET.fromstring(xml_str)

        # Parse open ports + services
        for port in root.findall(".//port"):
            state = port.find("state")
            if state is None or state.get("state") != "open":
                continue
            portid   = port.get("portid")
            protocol = port.get("protocol", "tcp")
            service  = port.find("service")
            svc_name = service.get("name", "unknown") if service is not None else "unknown"
            svc_prod = service.get("product", "")      if service is not None else ""
            label    = f"{svc_name} {svc_prod}".strip()
            ports.append({
                "port":     portid,
                "protocol": protocol,
                "service":  label
            })

        # Parse OS detection
        os_matches = root.findall(".//osmatch")
        if os_matches:
            # Take highest accuracy match
            best = max(os_matches, key=lambda o: int(o.get("accuracy", 0)))
            os_guess = f"{best.get('name')} ({best.get('accuracy')}% confidence)"

    except ET.ParseError:
        os_guess = "XML parse error"

    return {"ports": ports, "os_guess": os_guess}
