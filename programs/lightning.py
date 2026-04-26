"""Lightning — recursive bolts strike from sky to ground with afterglow."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


STRIKE_INTERVAL = (0.7, 1.6)
BOLT_FADE = 0.92
RAIN_DROPS = 28


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


class Lightning(Program):
    DESCRIPTION = "Lightning — bolts split through stormy sky"

    def setup(self) -> None:
        self._buf = [[(0, 0, 0)] * WIDTH for _ in range(HEIGHT)]
        self._strike_dt = random.uniform(*STRIKE_INTERVAL)
        self._flash = 0.0
        self._rain: list[list[float]] = []
        for _ in range(RAIN_DROPS):
            self._rain.append([random.uniform(0, WIDTH),
                               random.uniform(0, HEIGHT),
                               random.uniform(40, 70)])

    def _make_bolt(self, x0: int, y0: int, x1: int, y1: int,
                   depth: int, points: list[tuple[int, int, int]]) -> None:
        # Recursively split a segment with a midpoint perpendicular jitter.
        if depth == 0 or (abs(x1 - x0) < 2 and abs(y1 - y0) < 2):
            points.append((x0, y0, depth))
            points.append((x1, y1, depth))
            return
        mx = (x0 + x1) / 2
        my = (y0 + y1) / 2
        # Perpendicular displacement.
        nx = -(y1 - y0)
        ny = (x1 - x0)
        nl = math.hypot(nx, ny) or 1.0
        nx /= nl; ny /= nl
        amp = max(1.0, math.hypot(x1 - x0, y1 - y0) * 0.18)
        d = random.uniform(-amp, amp)
        mx += nx * d; my += ny * d
        self._make_bolt(x0, y0, int(mx), int(my), depth - 1, points)
        self._make_bolt(int(mx), int(my), x1, y1, depth - 1, points)
        # Branch occasionally.
        if depth >= 3 and random.random() < 0.45:
            bx = int(mx + (x1 - x0) * 0.3 + random.uniform(-6, 6))
            by = int(my + (y1 - y0) * 0.5)
            self._make_bolt(int(mx), int(my), bx, by, depth - 2, points)

    def _strike(self) -> None:
        x_top = random.randint(8, WIDTH - 8)
        x_bot = x_top + random.randint(-12, 12)
        x_bot = max(2, min(WIDTH - 3, x_bot))
        pts: list[tuple[int, int, int]] = []
        self._make_bolt(x_top, 0, x_bot, HEIGHT - 1, 5, pts)
        # Plot using Bresenham between each consecutive pair from the same depth pass.
        for i in range(0, len(pts) - 1, 2):
            x0, y0, _d = pts[i]
            x1, y1, _ = pts[i + 1]
            self._line(x0, y0, x1, y1, (250, 245, 255))
        self._flash = 1.0

    def _line(self, x0: int, y0: int, x1: int, y1: int,
              color: tuple[int, int, int]) -> None:
        dx = abs(x1 - x0); sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0); sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < WIDTH and 0 <= y0 < HEIGHT:
                self._buf[y0][x0] = color
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy: err += dy; x0 += sx
            if e2 <= dx: err += dx; y0 += sy

    def update(self, dt: float, events) -> None:
        self._strike_dt -= dt
        if self._strike_dt <= 0:
            self._strike()
            self._strike_dt = random.uniform(*STRIKE_INTERVAL)
        self._flash *= 0.82
        for d in self._rain:
            d[1] += d[2] * dt
            if d[1] >= HEIGHT:
                d[1] = -2
                d[0] = random.uniform(0, WIDTH)
                d[2] = random.uniform(40, 70)
        for y in range(HEIGHT):
            row = self._buf[y]
            for x in range(WIDTH):
                r, g, b = row[x]
                row[x] = (int(r * BOLT_FADE), int(g * BOLT_FADE),
                          int(b * BOLT_FADE))

    def render(self) -> Frame:
        f = Frame.black()
        # Stormy gradient sky.
        flash = self._flash
        for y in range(HEIGHT):
            t = y / HEIGHT
            base = (10 + 25 * (1 - t), 12 + 22 * (1 - t), 28 + 50 * (1 - t))
            if flash > 0.05:
                tint = flash * (1 - t * 0.6)
                base = (base[0] + 90 * tint, base[1] + 90 * tint,
                        base[2] + 110 * tint)
            r = int(min(255, base[0]))
            g = int(min(255, base[1]))
            b = int(min(255, base[2]))
            for x in range(WIDTH):
                f.set(x, y, (r, g, b))
        # Rain.
        for d in self._rain:
            xi = int(d[0]); yi = int(d[1])
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                f.set(xi, yi, (160, 180, 220))
                if yi + 1 < HEIGHT:
                    f.set(xi, yi + 1, (110, 140, 200))
        # Bolt + afterglow.
        for y in range(HEIGHT):
            row = self._buf[y]
            for x in range(WIDTH):
                r, g, b = row[x]
                if r > 8 or g > 8 or b > 8:
                    f.set(x, y, (r, g, b))
        return f
