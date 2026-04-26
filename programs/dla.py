"""DLA — random walkers stick on contact, growing a coral/snowflake."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


CX, CY = WIDTH // 2, HEIGHT // 2
RESET_AT = 1100
WALKERS_PER_FRAME = 1800
MAX_STEPS = 600


class DLA(Program):
    DESCRIPTION = "Diffusion-limited aggregation — walkers grow a fractal"

    def setup(self) -> None:
        self._aggr: set[tuple[int, int]] = {(CX, CY)}
        self._max_r: float = 1.0

    def update(self, dt: float, events) -> None:
        aggr = self._aggr
        for _ in range(WALKERS_PER_FRAME):
            spawn_r = self._max_r + 4.0
            kill_r2 = (self._max_r + 12.0) ** 2
            a = random.random() * math.tau
            x = int(round(CX + spawn_r * math.cos(a))) % WIDTH
            y = int(round(CY + spawn_r * math.sin(a))) % HEIGHT
            for _step in range(MAX_STEPS):
                d = random.randrange(4)
                if d == 0: x = (x + 1) % WIDTH
                elif d == 1: x = (x - 1) % WIDTH
                elif d == 2: y = (y + 1) % HEIGHT
                else: y = (y - 1) % HEIGHT
                if ((x + 1, y) in aggr or (x - 1, y) in aggr
                        or (x, y + 1) in aggr or (x, y - 1) in aggr):
                    aggr.add((x, y))
                    dx = x - CX
                    dy = y - CY
                    r = math.hypot(dx, dy)
                    if r > self._max_r:
                        self._max_r = r
                    break
                dx = x - CX
                dy = y - CY
                if dx * dx + dy * dy > kill_r2:
                    break
        if len(aggr) > RESET_AT:
            self._aggr = {(CX, CY)}
            self._max_r = 1.0

    def render(self) -> Frame:
        f = Frame.black()
        for (x, y) in self._aggr:
            dx = x - CX
            dy = y - CY
            r = math.hypot(dx, dy)
            t = min(1.0, r / max(1.0, self._max_r))
            r8 = int(80 + 175 * t)
            g8 = int(150 + 80 * (1 - t))
            b8 = int(220 - 60 * t)
            f.set(x, y, (r8, g8, b8))
        return f
