"""LAN /24 discovery for Pixoo devices."""
from __future__ import annotations

import ipaddress
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from .client import PixooClient

WORKERS = 64


def local_subnet() -> ipaddress.IPv4Network:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local = s.getsockname()[0]
    finally:
        s.close()
    return ipaddress.ip_network(f"{local}/24", strict=False)


def probe(ip: str) -> dict | None:
    c = PixooClient(ip)
    try:
        resp = c.channel_index()
    except Exception:
        return None
    if "SelectIndex" not in resp:
        return None
    info = {"ip": ip, "channel": resp.get("SelectIndex")}
    try:
        info.update(c.all_conf())
    except Exception:
        pass
    return info


def discover() -> list[dict]:
    net = local_subnet()
    print(f"scanning {net} ({net.num_addresses - 2} hosts)...", file=sys.stderr)
    found: list[dict] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(probe, str(ip)): ip for ip in net.hosts()}
        for fut in as_completed(futs):
            r = fut.result()
            if r:
                print(f"  {r['ip']}  channel={r.get('channel')}  "
                      f"brightness={r.get('Brightness')}", file=sys.stderr)
                found.append(r)
    found.sort(key=lambda d: tuple(int(p) for p in d["ip"].split(".")))
    return found


def _arp_map() -> dict[str, str]:
    """Best-effort IP→MAC map from the host ARP cache. Empty dict on failure."""
    import subprocess
    try:
        out = subprocess.run(["arp", "-an"], capture_output=True, text=True,
                             timeout=2).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    m: dict[str, str] = {}
    for line in out.splitlines():
        # macOS: "? (10.0.0.1) at aa:bb:cc:dd:ee:ff on en0 ..."
        if "(" not in line or ") at " not in line:
            continue
        ip = line.split("(", 1)[1].split(")", 1)[0]
        mac = line.split(") at ", 1)[1].split(" ", 1)[0]
        if mac != "(incomplete)":
            m[ip] = mac
    return m


def enrich_verbose(devices: list[dict]) -> list[dict]:
    """For each discovered device, pull weather + device time, and attach MAC."""
    def _fill(d: dict) -> dict:
        c = PixooClient(d["ip"])
        try:
            d["weather"] = c.weather_info()
        except Exception:
            d["weather"] = None
        try:
            d["device_time"] = c.device_time()
        except Exception:
            d["device_time"] = None
        return d

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        enriched = list(ex.map(_fill, devices))
    macs = _arp_map()
    for d in enriched:
        d["mac"] = macs.get(d["ip"])
    return enriched


def pick(devices: list[dict]) -> dict:
    if not devices:
        print("no Pixoos found on this LAN", file=sys.stderr)
        sys.exit(1)
    if len(devices) == 1:
        d = devices[0]
        print(f"one Pixoo found: {d['ip']}", file=sys.stderr)
        return d
    print()
    for i, d in enumerate(devices):
        print(f"  [{i}] {d['ip']}  ch={d.get('channel')}  "
              f"bright={d.get('Brightness')}")
    while True:
        try:
            choice = input("pick: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit(130)
        if choice.isdigit() and 0 <= int(choice) < len(devices):
            return devices[int(choice)]
