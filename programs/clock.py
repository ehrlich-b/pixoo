"""Analog clock — minute/hour/second hands on a 64x64 face."""
from __future__ import annotations

import math
import time

from pixoolib.frame import Frame
from pixoolib.runtime import Program


CX, CY = 32, 32
R_FACE = 30
HOUR_LEN = 14
MIN_LEN = 22
SEC_LEN = 26


def _line(f: Frame, x0: int, y0: int, x1: int, y1: int,
          color: tuple[int, int, int]) -> None:
    """Bresenham line."""
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        f.set(x0, y0, color)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


class Clock(Program):
    DESCRIPTION = "Analog wall clock — hour/minute/second hands"

    def render(self) -> Frame:
        f = Frame.black()
        # Tick marks: bright every 5 mins (the 12 hour positions), dim elsewhere.
        for i in range(60):
            a = math.radians(i * 6 - 90)
            r = R_FACE + (1 if i % 5 == 0 else 0)
            x = int(round(CX + r * math.cos(a)))
            y = int(round(CY + r * math.sin(a)))
            color = (200, 200, 220) if i % 5 == 0 else (60, 60, 80)
            f.set(x, y, color)
        lt = time.localtime()
        sec = lt.tm_sec
        mn = lt.tm_min + sec / 60.0
        hr = (lt.tm_hour % 12) + mn / 60.0
        ha = math.radians(hr * 30 - 90)
        ma = math.radians(mn * 6 - 90)
        sa = math.radians(sec * 6 - 90)
        _line(f, CX, CY, int(round(CX + HOUR_LEN * math.cos(ha))),
              int(round(CY + HOUR_LEN * math.sin(ha))), (180, 200, 255))
        _line(f, CX, CY, int(round(CX + MIN_LEN * math.cos(ma))),
              int(round(CY + MIN_LEN * math.sin(ma))), (255, 255, 255))
        _line(f, CX, CY, int(round(CX + SEC_LEN * math.cos(sa))),
              int(round(CY + SEC_LEN * math.sin(sa))), (255, 80, 80))
        f.set(CX, CY, (255, 255, 255))
        return f
