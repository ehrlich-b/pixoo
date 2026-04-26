"""Worm — segmented snake-like body wanders a toroidal field with hue trail."""
from __future__ import annotations

import math
import random
from collections import deque

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_SEG = 24
SPEED = 22.0


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


class Worm(Program):
    DESCRIPTION = "Worm — segmented body curves around the toroidal screen"

    def setup(self) -> None:
        self._head_x = WIDTH / 2
        self._head_y = HEIGHT / 2
        self._head_a = 0.0
        self._target_a = 0.0
        self._dir_dt = 0.0
        self._body: deque[tuple[float, float]] = deque(maxlen=N_SEG)
        for _ in range(N_SEG):
            self._body.append((self._head_x, self._head_y))
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt
        self._dir_dt -= dt
        if self._dir_dt <= 0:
            self._dir_dt = random.uniform(0.35, 1.0)
            self._target_a = self._head_a + random.uniform(-1.2, 1.2)
        # Smooth heading interpolation.
        diff = (self._target_a - self._head_a + math.pi) % (2 * math.pi) - math.pi
        self._head_a += diff * 3.2 * dt
        self._head_x = (self._head_x + math.cos(self._head_a) * SPEED * dt) % WIDTH
        self._head_y = (self._head_y + math.sin(self._head_a) * SPEED * dt) % HEIGHT
        self._body.append((self._head_x, self._head_y))

    def render(self) -> Frame:
        f = Frame.black()
        n = len(self._body)
        for i, (x, y) in enumerate(self._body):
            hue = ((i / n) * 0.85 + self._t * 0.07) % 1.0
            # Brightness rises toward the head.
            val = 0.55 + 0.45 * (i / n)
            col = _hsv(hue, 0.85, val)
            xi = int(x); yi = int(y)
            f.set(xi, yi, col)
            # Soft glow around segments.
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                xx = (xi + dx) % WIDTH
                yy = (yi + dy) % HEIGHT
                cur = f.get(xx, yy)
                f.set(xx, yy, (max(cur[0], col[0] // 3),
                               max(cur[1], col[1] // 3),
                               max(cur[2], col[2] // 3)))
        # Head highlight.
        hx = int(self._head_x); hy = int(self._head_y)
        f.set(hx, hy, (255, 255, 255))
        return f
