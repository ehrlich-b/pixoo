"""Snapshot driver — writes the latest frame as a PNG on disk.

Lets you daemonize a program (`./pixoo run life --snap &`) and inspect what
it's rendering by reading the PNG file. Stdlib only (zlib + struct).

Writes are atomic (tmp + rename) so a concurrent reader never sees a torn
frame. Throttled to ~10Hz to keep disk churn down.
"""
from __future__ import annotations

import os
import struct
import time
import zlib

from .frame import HEIGHT, WIDTH, Frame
from .runtime import Event


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_png(path: str, frame: Frame, scale: int = 8) -> None:
    """Write `frame` as a PNG at `path`, nearest-neighbor upscaled by `scale`."""
    if not isinstance(scale, int) or isinstance(scale, bool) or scale < 1:
        raise ValueError("PNG scale must be a positive integer")
    ow, oh = WIDTH * scale, HEIGHT * scale
    src = frame.pixels
    rows = []
    for y in range(HEIGHT):
        row = src[y * WIDTH * 3:(y + 1) * WIDTH * 3]
        expanded = b"".join(bytes(row[x:x + 3]) * scale for x in range(0, len(row), 3))
        rows.append((b"\0" + expanded) * scale)
    raw = b"".join(rows)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", ow, oh, 8, 2, 0, 0, 0)
    png = (
        sig
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + _chunk(b"IEND", b"")
    )
    tmp = path + ".tmp"
    with open(tmp, "wb") as fp:
        fp.write(png)
    os.replace(tmp, path)


class SnapshotDriver:
    def __init__(self, path: str, scale: int = 8, throttle_hz: float = 10.0) -> None:
        self.path = path
        self.scale = scale
        self._min_dt = 1.0 / throttle_hz if throttle_hz > 0 else 0.0
        self._last = 0.0

    def start(self) -> None:
        from pathlib import Path
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def stop(self) -> None:
        pass

    def render(self, frame: Frame) -> None:
        now = time.monotonic()
        if now - self._last < self._min_dt:
            return
        self._last = now
        write_png(self.path, frame, self.scale)

    def events(self) -> list[Event]:
        return []
