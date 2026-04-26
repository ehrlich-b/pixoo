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
    ow, oh = WIDTH * scale, HEIGHT * scale
    src = frame.pixels
    raw = bytearray(oh * (1 + ow * 3))
    o = 0
    for y in range(oh):
        raw[o] = 0  # PNG filter byte: None
        o += 1
        sy = y // scale
        row_src = sy * WIDTH * 3
        for x in range(ow):
            si = row_src + (x // scale) * 3
            raw[o] = src[si]
            raw[o + 1] = src[si + 1]
            raw[o + 2] = src[si + 2]
            o += 3
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
        pass

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
