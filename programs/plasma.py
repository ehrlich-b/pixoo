"""Plasma — three-axis sine sum mapped through a rainbow palette."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


def _hsv_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else:        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


_PALETTE = tuple(_hsv_rgb(i / 256.0, 0.85, 1.0) for i in range(256))


class Plasma(Program):
    DESCRIPTION = "Sine-sum plasma drifting through a rainbow palette"

    def setup(self) -> None:
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt * 0.7

    def render(self) -> Frame:
        f = Frame.black()
        t = self._t
        sx = [math.sin(x / 8.0 + t) for x in range(WIDTH)]
        sy = [math.sin(y / 8.0 + t * 0.7) for y in range(HEIGHT)]
        sxy = [math.sin(d / 12.0 + t * 0.5) for d in range(WIDTH + HEIGHT - 1)]
        pal = _PALETTE
        for y in range(HEIGHT):
            sy_y = sy[y]
            base = y
            for x in range(WIDTH):
                v = sx[x] + sy_y + sxy[x + y]
                idx = int((v + 3.0) * 42.5) & 255
                f.set(x, y, pal[idx])
        return f
