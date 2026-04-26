"""Attractors — Lorenz system traced in 2D with rotating viewpoint."""
from __future__ import annotations

import math
from collections import deque

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


SIGMA = 10.0
RHO = 28.0
BETA = 8.0 / 3.0
DT = 0.006
STEPS_PER_FRAME = 18
TRAIL_LEN = 320
SCALE = 1.25
ROT_RATE = 0.22


class Attractors(Program):
    DESCRIPTION = "Lorenz attractor — phase trail with rotating viewpoint"

    def setup(self) -> None:
        self._x = 0.1
        self._y = 0.0
        self._z = 0.0
        self._trail: deque[tuple[float, float, float]] = deque(maxlen=TRAIL_LEN)
        self._rot_t = 0.0

    def update(self, dt: float, events) -> None:
        self._rot_t += dt * ROT_RATE
        x, y, z = self._x, self._y, self._z
        for _ in range(STEPS_PER_FRAME):
            dx = SIGMA * (y - x)
            dy = x * (RHO - z) - y
            dz = x * y - BETA * z
            x += dx * DT
            y += dy * DT
            z += dz * DT
            self._trail.append((x, y, z))
        self._x = x
        self._y = y
        self._z = z

    def render(self) -> Frame:
        f = Frame.black()
        cx = WIDTH / 2
        cy = HEIGHT / 2 + 6
        cs = math.cos(self._rot_t)
        sn = math.sin(self._rot_t)
        n = len(self._trail)
        for i, (x, y, z) in enumerate(self._trail):
            xv = x * cs - y * sn
            zv = z - 25
            sx = int(cx + xv * SCALE)
            sy = int(cy - zv * SCALE)
            if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                age = i / n if n else 0
                # Hot trail: dim purple → bright cyan-white at the head.
                r = int(40 + 215 * age * age)
                g = int(60 + 195 * age)
                b = int(140 + 115 * age)
                f.set(sx, sy, (r, g, b))
        return f
