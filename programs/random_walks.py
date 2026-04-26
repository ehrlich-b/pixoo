"""Random walks — many 1D walkers; histogram converges to a Gaussian."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_WALKERS = 64
RESET_STEPS = 700
WALKER_ROW = 4
HIST_BOTTOM = HEIGHT - 1
HIST_TOP = 8


class RandomWalks(Program):
    DESCRIPTION = "1D random walks — histogram of positions becomes Gaussian"

    def setup(self) -> None:
        self._reset()

    def _reset(self) -> None:
        cx = WIDTH // 2
        self._walkers = [cx] * N_WALKERS
        self._hist = [0] * WIDTH
        self._steps = 0

    def update(self, dt: float, events) -> None:
        for i in range(N_WALKERS):
            v = self._walkers[i] + (1 if random.random() < 0.5 else -1)
            if v < 0: v = 0
            elif v >= WIDTH: v = WIDTH - 1
            self._walkers[i] = v
            self._hist[v] += 1
        self._steps += 1
        if self._steps >= RESET_STEPS:
            self._reset()

    def render(self) -> Frame:
        f = Frame.black()
        peak = max(self._hist) if self._hist else 1
        if peak == 0:
            peak = 1
        avail = HIST_BOTTOM - HIST_TOP
        for x in range(WIDTH):
            h = int(self._hist[x] / peak * avail)
            for y in range(HIST_BOTTOM - h, HIST_BOTTOM + 1):
                t = (y - (HIST_BOTTOM - h)) / max(1, h)
                r = int(60 + 80 * t)
                g = int(160 + 80 * (1 - t))
                b = int(220)
                f.set(x, y, (r, g, b))
        for w in self._walkers:
            f.set(w, WALKER_ROW, (255, 220, 110))
        # Centerline reference dots.
        cx = WIDTH // 2
        for y in range(HIST_TOP, HIST_BOTTOM, 4):
            f.set(cx, y, (60, 70, 90))
        return f
