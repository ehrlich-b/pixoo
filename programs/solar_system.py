"""Solar system — top-down planets orbit a sun at scaled real periods."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


CX, CY = WIDTH / 2, HEIGHT / 2
SUN_COLOR = (255, 220, 80)
# (name, orbital radius (px), period (s sim time), color, size_px)
PLANETS = (
    ("mercury", 4.5,   2.5, (180, 170, 160), 1),
    ("venus",   7.5,   6.4, (240, 200, 130), 1),
    ("earth",  11.0,  10.0, ( 90, 160, 240), 2),
    ("mars",   14.5,  18.8, (220,  90,  70), 1),
    ("jupiter",20.5, 118.6, (220, 170, 110), 3),
    ("saturn", 25.0, 294.6, (210, 195, 140), 2),
    ("uranus", 28.5, 840.5, (130, 220, 230), 1),
    ("neptune",30.5,1647.4, (110, 130, 240), 1),
)
TRAIL_LEN = 28


class SolarSystem(Program):
    DESCRIPTION = "Top-down solar system — eight planets at scaled periods"

    def setup(self) -> None:
        self._t = 0.0
        self._trails: list[list[tuple[int, int]]] = [[] for _ in PLANETS]

    def update(self, dt: float, events) -> None:
        self._t += dt * 1.5
        for i, (_, radius, period, _, _) in enumerate(PLANETS):
            a = self._t / period * math.tau
            x = int(round(CX + radius * math.cos(a)))
            y = int(round(CY + radius * math.sin(a)))
            tr = self._trails[i]
            if not tr or tr[-1] != (x, y):
                tr.append((x, y))
                if len(tr) > TRAIL_LEN:
                    tr.pop(0)

    def render(self) -> Frame:
        f = Frame.black()
        # Orbit rings — very dim, helps depth perception.
        for _, radius, _, _, _ in PLANETS:
            for k in range(64):
                a = k / 64 * math.tau
                rx = int(round(CX + radius * math.cos(a)))
                ry = int(round(CY + radius * math.sin(a)))
                if 0 <= rx < WIDTH and 0 <= ry < HEIGHT:
                    f.set(rx, ry, (12, 12, 22))
        # Sun (3x3 + rim).
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                f.set(int(CX + dx), int(CY + dy), SUN_COLOR)
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            f.set(int(CX + dx), int(CY + dy), (210, 165, 60))
        # Planets with comet-tail trails.
        for i, (_, _, _, color, size) in enumerate(PLANETS):
            tr = self._trails[i]
            n = len(tr)
            for k, (x, y) in enumerate(tr):
                t = (k + 1) / n
                fade = 0.15 + 0.45 * t
                f.set(x, y, (int(color[0] * fade), int(color[1] * fade),
                              int(color[2] * fade)))
            if tr:
                hx, hy = tr[-1]
                if size == 1:
                    f.set(hx, hy, color)
                elif size == 2:
                    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                        f.set(hx + dx, hy + dy, color)
                else:
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            f.set(hx + dx, hy + dy, color)
        return f
