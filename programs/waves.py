"""2D wave equation — ripples spread, interfere, fade slowly."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


DAMP = 0.9965
C2 = 0.4   # propagation speed
DROP_AMP = 18.0


class Waves(Program):
    DESCRIPTION = "2D wave equation — ripples spread, interfere, decay"

    def setup(self) -> None:
        self._u = [[0.0] * WIDTH for _ in range(HEIGHT)]
        self._up = [[0.0] * WIDTH for _ in range(HEIGHT)]
        self._ripple_t = 0.4

    def update(self, dt: float, events) -> None:
        u = self._u
        up = self._up
        new = [row[:] for row in u]
        for y in range(1, HEIGHT - 1):
            row = u[y]
            up_row = up[y]
            ur = u[y - 1]
            dr = u[y + 1]
            new_row = new[y]
            for x in range(1, WIDTH - 1):
                lap = (ur[x] + dr[x] + row[x - 1] + row[x + 1] - 4 * row[x])
                new_row[x] = (2 * row[x] - up_row[x] + C2 * lap) * DAMP
        self._up = u
        self._u = new
        self._ripple_t -= dt
        if self._ripple_t <= 0:
            self._ripple_t = random.uniform(0.6, 2.4)
            cx = random.randrange(8, WIDTH - 8)
            cy = random.randrange(8, HEIGHT - 8)
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    if dx * dx + dy * dy <= 4:
                        self._u[cy + dy][cx + dx] += DROP_AMP

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._u[y]
            for x in range(WIDTH):
                v = row[x]
                if v > 0.4:
                    s = min(1.0, v / 8.0)
                    f.set(x, y, (int(30 * s), int(140 * s), int(255 * s)))
                elif v < -0.4:
                    s = min(1.0, -v / 8.0)
                    f.set(x, y, (int(255 * s), int(70 * s), int(110 * s)))
        return f
