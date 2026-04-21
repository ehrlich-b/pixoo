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
