"""Phyllotaxis — golden-angle spiral grows one seed at a time, then resets."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


GOLDEN = math.pi * (3 - math.sqrt(5))   # ≈137.5°
SCALE = 2.45
DOTS_PER_FRAME = 6
MAX_DOTS = 750
HOLD_FRAMES = 80


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


class Phyllotaxis(Program):
    DESCRIPTION = "Phyllotaxis — sunflower spiral built one seed at a time"

    def setup(self) -> None:
        self._n = 0
        self._hold = 0

    def update(self, dt: float, events) -> None:
        if self._n >= MAX_DOTS:
            self._hold += 1
            if self._hold > HOLD_FRAMES:
                self._n = 0
                self._hold = 0
            return
        self._n = min(MAX_DOTS, self._n + DOTS_PER_FRAME)

    def render(self) -> Frame:
        f = Frame.black()
        cx = WIDTH / 2 - 0.5
        cy = HEIGHT / 2 - 0.5
        for i in range(self._n):
            ang = i * GOLDEN
            r = SCALE * math.sqrt(i)
            x = cx + r * math.cos(ang)
            y = cy + r * math.sin(ang)
            xi = int(round(x))
            yi = int(round(y))
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                hue = (i * 0.0028) % 1.0
                rgb = _hsv(hue, 0.82, 0.95)
                f.set(xi, yi, rgb)
                # Two-pixel diagonal "petal" for legibility on later seeds.
                if i > 60 and i % 3 == 0:
                    if 0 <= xi + 1 < WIDTH:
                        f.set(xi + 1, yi, (rgb[0] // 2, rgb[1] // 2, rgb[2] // 2))
        return f
