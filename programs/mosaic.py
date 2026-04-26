"""Mosaic — 8×8 grid of tiles whose hues drift slowly with sparkle highlights."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


TILE = 8
COLS = WIDTH // TILE  # 8
ROWS = HEIGHT // TILE  # 8


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


class Mosaic(Program):
    DESCRIPTION = "Mosaic — drifting tile colors with sparkle highlights"

    def setup(self) -> None:
        self._t = 0.0
        # Each tile gets a base hue + per-tile drift speed.
        self._hue0 = [[random.random() for _ in range(COLS)]
                      for _ in range(ROWS)]
        self._hue_speed = [[random.uniform(0.04, 0.14) for _ in range(COLS)]
                           for _ in range(ROWS)]
        self._sparkle: list[list[float]] = [[0.0] * COLS for _ in range(ROWS)]
        self._spark_dt = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt
        for r in range(ROWS):
            for c in range(COLS):
                if self._sparkle[r][c] > 0:
                    self._sparkle[r][c] -= dt * 1.7
                    if self._sparkle[r][c] < 0:
                        self._sparkle[r][c] = 0.0
        self._spark_dt -= dt
        if self._spark_dt <= 0:
            self._spark_dt = random.uniform(0.06, 0.18)
            r = random.randrange(ROWS)
            c = random.randrange(COLS)
            self._sparkle[r][c] = 1.0

    def render(self) -> Frame:
        f = Frame.black()
        for r in range(ROWS):
            for c in range(COLS):
                hue = (self._hue0[r][c] + self._t * self._hue_speed[r][c]) % 1.0
                spark = self._sparkle[r][c]
                val = 0.55 + 0.30 * math.sin(self._t * 0.6 + (r + c) * 0.4)
                if spark > 0:
                    val = min(1.0, val + spark * 0.65)
                col = _hsv(hue, 0.78, val)
                # 1-pixel mortar between tiles.
                ox = c * TILE
                oy = r * TILE
                for yy in range(oy, oy + TILE):
                    for xx in range(ox, ox + TILE):
                        if (xx == ox or yy == oy):
                            f.set(xx, yy, (18, 16, 30))
                        else:
                            f.set(xx, yy, col)
                # Subtle inner brighter pixel for "shine".
                f.set(ox + 1, oy + 1, (min(255, col[0] + 60),
                                      min(255, col[1] + 60),
                                      min(255, col[2] + 60)))
                if spark > 0.5:
                    cx_ = ox + TILE // 2
                    cy_ = oy + TILE // 2
                    f.set(cx_, cy_, (255, 255, 255))
                    f.set(cx_ + 1, cy_, (220, 220, 240))
                    f.set(cx_, cy_ + 1, (220, 220, 240))
        return f
