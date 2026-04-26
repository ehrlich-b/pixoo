"""Voronoi — drifting sites; nearest-site coloring with edge highlights."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_SITES = 16
SPEED = 5.0
EDGE_RATIO = 1.05


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


class Voronoi(Program):
    DESCRIPTION = "Voronoi cells — drifting sites with edge highlights"

    def setup(self) -> None:
        self._sites: list[list[float]] = []
        self._colors: list[tuple[int, int, int]] = []
        for i in range(N_SITES):
            x = random.uniform(4, WIDTH - 4)
            y = random.uniform(4, HEIGHT - 4)
            ang = random.uniform(0, 2 * math.pi)
            vx = math.cos(ang) * SPEED
            vy = math.sin(ang) * SPEED
            self._sites.append([x, y, vx, vy])
            hue = (i / N_SITES + 0.07) % 1.0
            self._colors.append(_hsv(hue, 0.82, 0.92))

    def update(self, dt: float, events) -> None:
        for s in self._sites:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            if s[0] < 0:
                s[0] = 0; s[2] = -s[2]
            elif s[0] >= WIDTH:
                s[0] = WIDTH - 1; s[2] = -s[2]
            if s[1] < 0:
                s[1] = 0; s[3] = -s[3]
            elif s[1] >= HEIGHT:
                s[1] = HEIGHT - 1; s[3] = -s[3]

    def render(self) -> Frame:
        f = Frame.black()
        sites = self._sites
        colors = self._colors
        n = len(sites)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                best = 1e18
                sec = 1e18
                best_i = 0
                for i in range(n):
                    s = sites[i]
                    dx = x - s[0]
                    dy = y - s[1]
                    d = dx * dx + dy * dy
                    if d < best:
                        sec = best
                        best = d
                        best_i = i
                    elif d < sec:
                        sec = d
                if best > 0.5 and sec / best < EDGE_RATIO:
                    f.set(x, y, (240, 240, 250))
                else:
                    f.set(x, y, colors[best_i])
        # Site dots on top.
        for i in range(n):
            sx = int(sites[i][0])
            sy = int(sites[i][1])
            f.set(sx, sy, (255, 255, 255))
            f.set(sx + 1, sy, (255, 255, 255))
            f.set(sx, sy + 1, (255, 255, 255))
            f.set(sx + 1, sy + 1, (255, 255, 255))
        return f
