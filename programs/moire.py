"""Moire — two rotating sine-grid layers interfere into shifting beats."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


SPACING_A = 8.0
SPACING_B = 9.4


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


class Moire(Program):
    DESCRIPTION = "Moire — two rotating sine grids beat into shifting patterns"

    def setup(self) -> None:
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        cx = WIDTH / 2 - 0.5
        cy = HEIGHT / 2 - 0.5
        ang_a = self._t * 0.10
        ang_b = self._t * 0.07 + 0.4
        cs_a = math.cos(ang_a); sn_a = math.sin(ang_a)
        cs_b = math.cos(ang_b); sn_b = math.sin(ang_b)
        ka = 2 * math.pi / SPACING_A
        kb = 2 * math.pi / SPACING_B
        sin = math.sin
        px = f.pixels
        for y in range(HEIGHT):
            dy = y - cy
            for x in range(WIDTH):
                dx = x - cx
                ax = dx * cs_a - dy * sn_a
                ay = dx * sn_a + dy * cs_a
                bx = dx * cs_b - dy * sn_b
                by = dx * sn_b + dy * cs_b
                a = sin(ax * ka) + sin(ay * ka)
                b = sin(bx * kb) + sin(by * kb)
                v = (a + b) * 0.25 + 0.5
                if v < 0:
                    v = 0.0
                elif v > 1:
                    v = 1.0
                hue = (v * 0.45 + self._t * 0.05) % 1.0
                col = _hsv(hue, 0.82, v)
                pi = (y * WIDTH + x) * 3
                px[pi] = col[0]
                px[pi + 1] = col[1]
                px[pi + 2] = col[2]
        return f
