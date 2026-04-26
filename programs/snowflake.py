"""Snowflake — 6-fold symmetric ice crystal grows from center, then reseeds."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


GROW_PER_FRAME = 12
HOLD_FRAMES = 70
MAX_RADIUS = 28


class Snowflake(Program):
    DESCRIPTION = "Snowflake — 6-fold symmetric crystal grows; reset when full"

    def setup(self) -> None:
        self._reset()

    def _reset(self) -> None:
        self._grid = bytearray(WIDTH * HEIGHT)
        self._cx = WIDTH // 2
        self._cy = HEIGHT // 2
        self._set_sym(0, 0)
        self._radius = 1.0
        self._hold = 0
        self._sym = self._build_sym()

    @staticmethod
    def _build_sym() -> list[tuple[float, float, float, float]]:
        out: list[tuple[float, float, float, float]] = []
        for k in range(6):
            ang = k * math.pi / 3
            cs = math.cos(ang); sn = math.sin(ang)
            out.append((cs, sn, 1.0, 0.0))   # rotation only
            out.append((cs, sn, -1.0, 0.0))  # flipped
        return out

    def _set_sym(self, dx: int, dy: int) -> None:
        for k in range(6):
            ang = k * math.pi / 3
            cs = math.cos(ang); sn = math.sin(ang)
            for mirror in (1, -1):
                rx = dx * cs - (dy * mirror) * sn
                ry = dx * sn + (dy * mirror) * cs
                xi = self._cx + int(round(rx))
                yi = self._cy + int(round(ry))
                if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                    self._grid[yi * WIDTH + xi] = 1

    def update(self, dt: float, events) -> None:
        if self._hold > 0:
            self._hold -= 1
            if self._hold <= 0:
                self._reset()
            return
        for _ in range(GROW_PER_FRAME):
            r = random.uniform(0.5, min(self._radius + 2, MAX_RADIUS))
            # Wedge [0, pi/3], biased toward small theta so axes grow.
            theta = random.uniform(0, math.pi / 3)
            if random.random() < 0.40:
                theta = random.uniform(0, math.pi / 12)
            dx = int(round(r * math.cos(theta)))
            dy = int(round(r * math.sin(theta)))
            xi = self._cx + dx; yi = self._cy + dy
            if not (0 <= xi < WIDTH and 0 <= yi < HEIGHT):
                continue
            if self._grid[yi * WIDTH + xi]:
                continue
            adjacent = False
            for ddy in (-1, 0, 1):
                for ddx in (-1, 0, 1):
                    if ddx == 0 and ddy == 0:
                        continue
                    nx = xi + ddx; ny = yi + ddy
                    if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                        if self._grid[ny * WIDTH + nx]:
                            adjacent = True
                            break
                if adjacent:
                    break
            if adjacent:
                self._set_sym(dx, dy)
                rd = math.hypot(dx, dy)
                if rd > self._radius:
                    self._radius = rd
        if self._radius >= MAX_RADIUS - 1:
            self._hold = HOLD_FRAMES

    def render(self) -> Frame:
        f = Frame.black()
        # Subtle background gradient.
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(8 + 12 * (1 - t))
            g = int(12 + 18 * (1 - t))
            b = int(32 + 28 * (1 - t))
            for x in range(WIDTH):
                f.set(x, y, (r, g, b))
        cx = self._cx; cy = self._cy
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self._grid[y * WIDTH + x]:
                    dx = x - cx; dy = y - cy
                    rd = math.hypot(dx, dy)
                    t = max(0.0, 1 - rd / MAX_RADIUS)
                    r = int(180 + 70 * t)
                    g = int(225 + 30 * t)
                    b = 255
                    f.set(x, y, (min(255, r), min(255, g), b))
        return f
