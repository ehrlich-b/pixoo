"""Ising — 2D Ising model cycles between disordered and ordered phases."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


PHASE_T = 28.0
T_HOT = 4.2
T_COLD = 1.5
ITERS_PER_FRAME = 5500
J = 1.0


class Ising(Program):
    DESCRIPTION = "Ising model — cooling from disorder to magnetic domains"

    def setup(self) -> None:
        self._grid = bytearray(WIDTH * HEIGHT)
        for i in range(len(self._grid)):
            self._grid[i] = 1 if random.random() < 0.5 else 0  # 1 = up, 0 = down
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt
        cycle = (self._t % PHASE_T) / PHASE_T
        # Slow cool with a sudden re-heat at phase boundary.
        if cycle < 0.85:
            T = T_HOT - (T_HOT - T_COLD) * (cycle / 0.85)
        else:
            T = T_HOT
        beta = 1.0 / max(0.1, T)
        grid = self._grid
        rand = random.random
        randint = random.randrange
        exp = math.exp
        for _ in range(ITERS_PER_FRAME):
            x = randint(WIDTH)
            y = randint(HEIGHT)
            i = y * WIDTH + x
            s = 1 if grid[i] else -1
            n = ((1 if grid[((y - 1) % HEIGHT) * WIDTH + x] else -1)
                 + (1 if grid[((y + 1) % HEIGHT) * WIDTH + x] else -1)
                 + (1 if grid[y * WIDTH + (x - 1) % WIDTH] else -1)
                 + (1 if grid[y * WIDTH + (x + 1) % WIDTH] else -1))
            dE = 2 * J * s * n
            if dE <= 0 or rand() < exp(-beta * dE):
                grid[i] = 0 if grid[i] else 1

    def render(self) -> Frame:
        f = Frame.black()
        grid = self._grid
        px = f.pixels
        # Up = warm yellow, down = cool blue.
        for y in range(HEIGHT):
            for x in range(WIDTH):
                i = y * WIDTH + x
                pi = i * 3
                if grid[i]:
                    px[pi] = 240; px[pi + 1] = 195; px[pi + 2] = 95
                else:
                    px[pi] = 50; px[pi + 1] = 65; px[pi + 2] = 145
        # Phase indicator: thin progress bar at top.
        cycle = (self._t % PHASE_T) / PHASE_T
        bar_len = int(cycle * WIDTH)
        for x in range(bar_len):
            pi = (0 * WIDTH + x) * 3
            px[pi] = max(px[pi], 200)
            px[pi + 1] = max(px[pi + 1], 200)
            px[pi + 2] = max(px[pi + 2], 200)
        return f
