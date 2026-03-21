from scapy.all import IP, ICMP, sr1
import threading
import time

status = {}
status_lock = threading.Lock()

def ping_device(ip: str) -> tuple[bool, float | None]:
    try:
        start = time.time()
        reply = sr1(IP(dst=ip)/ICMP(), timeout=1, verbose=0)
        if reply is not None:
            rtt = (time.time() - start) * 1000
            return True, round(rtt, 2)
        return False, None
    except Exception:
        return False, None

def ping_worker(ip: str):
    # Public — also called directly by rescan for new devices
    latency_samples = []
    while True:
        alive, latency = ping_device(ip)
        with status_lock:
            prev = status[ip]["alive"]
            if prev is False:
                status[ip]["downtime"] += 1
            if latency is not None:
                latency_samples.append(latency)
                if len(latency_samples) > 60:
                    latency_samples.pop(0)
            status[ip]["alive"]       = alive
            status[ip]["latency"]     = latency
            status[ip]["avg_latency"] = (
                round(sum(latency_samples) / len(latency_samples), 2)
                if latency_samples else None
            )
        time.sleep(1)

def start_monitor(devices: list[dict]):
    for d in devices:
        with status_lock:
            status[d["ip"]] = {
                "alive": None, "latency": None,
                "avg_latency": None, "downtime": 0
            }
    for d in devices:
        t = threading.Thread(target=ping_worker, args=(d["ip"],), daemon=True)
        t.start()
