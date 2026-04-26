"""Kaleidoscope — moving sine pattern reflected with 6-fold radial symmetry."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


SECTORS = 6


def _hsv(h: float, s: float, v: float) -> tuple[int, int, int]:
    h6 = h * 6.0
    i = int(h6) % 6
    f = h6 - int(h6)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else: r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


class Kaleidoscope(Program):
    DESCRIPTION = "Kaleidoscope — 6-fold mirrored sine field"

    def setup(self) -> None:
        cx = WIDTH / 2 - 0.5
        cy = HEIGHT / 2 - 0.5
        sector_size = 2 * math.pi / SECTORS
        half = sector_size / 2
        n = WIDTH * HEIGHT
        self._r = [0.0] * n
        self._a = [0.0] * n
        for y in range(HEIGHT):
            for x in range(WIDTH):
                dx = x - cx
                dy = y - cy
                r = math.sqrt(dx * dx + dy * dy)
                ang = math.atan2(dy, dx) % (2 * math.pi)
                local = ang - int(ang / sector_size) * sector_size
                if local > half:
                    local = sector_size - local
                idx = y * WIDTH + x
                self._r[idx] = r
                self._a[idx] = local
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        t = self._t
        sin = math.sin
        cos = math.cos
        rA = self._r
        aA = self._a
        px = f.pixels
        for y in range(HEIGHT):
            base = y * WIDTH
            for x in range(WIDTH):
                idx = base + x
                r = rA[idx]
                a = aA[idx]
                v1 = sin(r * 0.32 + t * 1.05)
                v2 = sin(a * 8.0 + r * 0.12 - t * 0.7)
                v3 = cos(r * 0.20 + a * 5.0 + t * 0.45)
                avg = (v1 + v2 + v3) * (1.0 / 3)
                hue = (avg * 0.5 + 0.5 + t * 0.04) % 1.0
                val = 0.55 + 0.45 * sin(r * 0.18 + a * 6 + t * 1.6)
                if val < 0:
                    val = 0
                col = _hsv(hue, 0.85, val)
                pi = idx * 3
                px[pi] = col[0]
                px[pi + 1] = col[1]
                px[pi + 2] = col[2]
        return f
