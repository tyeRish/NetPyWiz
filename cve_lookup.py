import requests
import json
import os
import re
import time

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".netpywiz_cache.json")
NVD_URL    = "https://services.nvd.nist.gov/rest/json/cves/2.0"

def load_cache() -> dict:
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass

def check_internet() -> bool:
    try:
        requests.get("https://services.nvd.nist.gov", timeout=3)
        return True
    except Exception:
        return False

def parse_service_version(service_str: str) -> tuple[str, str]:
    """
    Extract product and version from nmap service string.
    e.g. "OpenSSH 8.2p1" -> ("openssh", "8.2p1")
         "Apache httpd 2.4.41" -> ("apache_httpd", "2.4.41")
    """
    service_str = service_str.strip()
    # Match "ProductName X.Y.Z" pattern
    match = re.match(r"^([\w\s\-]+?)\s+([\d][\d\.\w\-]+)$", service_str)
    if match:
        product = match.group(1).strip().lower().replace(" ", "_")
        version = match.group(2).strip()
        return product, version
    # No version found — just return the name
    return service_str.lower().replace(" ", "_"), ""

def lookup_cves(service_str: str, api_key: str = "") -> list[dict]:
    """
    Returns list of CVE dicts for a given service string.
    Uses cache first, falls back to NVD API.
    """
    if not service_str or service_str in ("unknown", "---", ""):
        return []

    cache     = load_cache()
    cache_key = service_str.lower().strip()

    # Return cached result if available
    if cache_key in cache:
        return cache[cache_key]

    # Need internet for fresh lookup
    if not check_internet():
        return [{"error": "REQUIRES INTERNET CONNECTION — NO CACHED DATA"}]

    product, version = parse_service_version(service_str)

    # Build search query
    keyword = f"{product.replace('_', ' ')} {version}".strip()

    headers = {}
    if api_key:
        headers["apiKey"] = api_key

    try:
        # NVD asks for 6 second delay between requests without API key
        time.sleep(1)

        resp = requests.get(NVD_URL, params={
            "keywordSearch":  keyword,
            "resultsPerPage": 20,
        }, headers=headers, timeout=10)

        if resp.status_code != 200:
            return [{"error": f"NVD API error: {resp.status_code}"}]

        data  = resp.json()
        vulns = data.get("vulnerabilities", [])
        cves  = []

        for v in vulns:
            cve  = v.get("cve", {})
            cid  = cve.get("id", "")

            # Get English description
            desc = ""
            for d in cve.get("descriptions", []):
                if d.get("lang") == "en":
                    desc = d.get("value", "")
                    break

            # Get severity — prefer CVSSv3, fall back to v2
            severity = "UNKNOWN"
            score    = ""
            metrics  = cve.get("metrics", {})

            if metrics.get("cvssMetricV31"):
                m        = metrics["cvssMetricV31"][0]
                severity = m.get("cvssData", {}).get("baseSeverity", "UNKNOWN")
                score    = str(m.get("cvssData", {}).get("baseScore", ""))
            elif metrics.get("cvssMetricV30"):
                m        = metrics["cvssMetricV30"][0]
                severity = m.get("cvssData", {}).get("baseSeverity", "UNKNOWN")
                score    = str(m.get("cvssData", {}).get("baseScore", ""))
            elif metrics.get("cvssMetricV2"):
                m        = metrics["cvssMetricV2"][0]
                severity = m.get("baseSeverity", "UNKNOWN")
                score    = str(m.get("cvssData", {}).get("baseScore", ""))

            cves.append({
                "id":       cid,
                "severity": severity.upper(),
                "score":    score,
                "summary":  desc[:300] + ("..." if len(desc) > 300 else ""),
                "url":      f"https://nvd.nist.gov/vuln/detail/{cid}",
                "service":  service_str,
            })

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
        cves.sort(key=lambda c: severity_order.get(c["severity"], 4))

        # Cache and return
        cache[cache_key] = cves
        save_cache(cache)
        return cves

    except requests.exceptions.ConnectionError:
        return [{"error": "NO INTERNET CONNECTION"}]
    except Exception as e:
        return [{"error": f"Lookup failed: {e}"}]


def severity_color(severity: str) -> str:
    return {
        "CRITICAL": "#ff2255",
        "HIGH":     "#ff6600",
        "MEDIUM":   "#ffaa00",
        "LOW":      "#00ff9f",
    }.get(severity.upper(), "#444466")
