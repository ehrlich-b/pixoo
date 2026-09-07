"""Glue: choose a PixooClient from cache / env / discovery."""
from __future__ import annotations

import os

from . import state
from .client import PixooClient
from .discover import discover, pick


def get_client(rediscover: bool = False) -> PixooClient:
    if ip := os.environ.get("PIXOO_IP"):
        return PixooClient(ip)
    if not rediscover:
        if cached := state.load():
            if cached.get("ip"):
                return PixooClient(cached["ip"])
    d = pick(discover())
    state.save(d)
    return PixooClient(d["ip"])


def ensure_primed(c: PixooClient) -> None:
    """Auto-prime once per (device, channel) so text overlays actually render."""
    if state.is_primed(c.ip):
        return
    c.prime()
    state.set_primed(True,c.ip)
