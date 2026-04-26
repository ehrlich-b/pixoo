"""Truchet — quarter-arc tiles flip occasionally; curves snake across the grid."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


CELL = 8
GRID = WIDTH // CELL  # 8
R = CELL // 2          # arc radius
ARC_W = 1.0
FLIP_HZ = 6.0
FLIPS_PER_TICK = 3


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


class Truchet(Program):
    DESCRIPTION = "Truchet tiles — quarter-arc curves flowing across the grid"

    def setup(self) -> None:
        self._cells = [[random.randint(0, 1) for _ in range(GRID)]
                       for _ in range(GRID)]
        # Per-cell arc mask: bytearray of CELL*CELL entries (0 = bg, 1 = arc).
        self._mask_a = self._build_mask(0)
        self._mask_b = self._build_mask(1)
        self._t = 0.0
        self._flip_dt = 0.0

    @staticmethod
    def _build_mask(ttype: int) -> bytearray:
        mask = bytearray(CELL * CELL)
        for dy in range(CELL):
            for dx in range(CELL):
                hit = False
                if ttype == 0:
                    # Arc 1: center (CELL, 0), r=R, in NE corner.
                    d = math.hypot(dx - CELL, dy)
                    if abs(d - R) <= ARC_W and dx >= R and dy <= R:
                        hit = True
                    # Arc 2: center (0, CELL), r=R, in SW corner.
                    d = math.hypot(dx, dy - CELL)
                    if abs(d - R) <= ARC_W and dx <= R and dy >= R:
                        hit = True
                else:
                    # Arc 1: center (0, 0), r=R.
                    d = math.hypot(dx, dy)
                    if abs(d - R) <= ARC_W and dx <= R and dy <= R:
                        hit = True
                    # Arc 2: center (CELL, CELL), r=R.
                    d = math.hypot(dx - CELL, dy - CELL)
                    if abs(d - R) <= ARC_W and dx >= R and dy >= R:
                        hit = True
                mask[dy * CELL + dx] = 1 if hit else 0
        return mask

    def update(self, dt: float, events) -> None:
        self._t += dt
        self._flip_dt += dt
        period = 1.0 / FLIP_HZ
        while self._flip_dt >= period:
            self._flip_dt -= period
            for _ in range(FLIPS_PER_TICK):
                cx = random.randrange(GRID)
                cy = random.randrange(GRID)
                self._cells[cy][cx] ^= 1

    def render(self) -> Frame:
        f = Frame.black()
        # Background — subtle teal->purple gradient by row.
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(18 + 22 * (1 - t))
            g = int(14 + 18 * (1 - t))
            b = int(40 + 30 * t)
            for x in range(WIDTH):
                f.set(x, y, (r, g, b))
        arc_color = _hsv((self._t * 0.07) % 1.0, 0.78, 0.96)
        for cy in range(GRID):
            for cx in range(GRID):
                mask = self._mask_a if self._cells[cy][cx] == 0 else self._mask_b
                ox = cx * CELL
                oy = cy * CELL
                for dy in range(CELL):
                    for dx in range(CELL):
                        if mask[dy * CELL + dx]:
                            f.set(ox + dx, oy + dy, arc_color)
        return f
