"""Langton's ant — many steps per frame, edges wrap, resets after highway.

Optional params (all deterministic; defaults reproduce classic center-start):
    seed             int — starting ant (x, y, dir) drawn from random.Random(seed)
    steps            int — pre-advance this many ant steps in setup()
    steps_per_frame  int — ant steps per update() (default STEPS_PER_FRAME)
"""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

STEPS_PER_FRAME = 100
RESET_STEPS = 25_000

# direction index: 0=up 1=right 2=down 3=left
DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)


class Langton(Program):
    DESCRIPTION = "Langton's ant — highway emerges after ~11k steps, then resets"

    def setup(self) -> None:
        self._seed = int(self.params["seed"]) if "seed" in self.params else None
        self._spf = int(self.params.get("steps_per_frame", STEPS_PER_FRAME))
        self._reset(self._seed)
        self._advance(int(self.params.get("steps", 0) or 0))

    def _reset(self, seed: int | None) -> None:
        self.cells = bytearray(WIDTH * HEIGHT)  # 0 = off, 1 = on
        if seed is None:
            self.ax, self.ay = WIDTH // 2, HEIGHT // 2
            self.adir = 0
        else:
            rng = random.Random(seed)
            self.ax, self.ay = rng.randrange(WIDTH), rng.randrange(HEIGHT)
            self.adir = rng.randrange(4)
        self.steps = 0

    def _advance(self, n: int) -> None:
        for _ in range(n):
            i = self.ay * WIDTH + self.ax
            if self.cells[i]:
                # on → turn left, flip off, step
                self.adir = (self.adir - 1) % 4
                self.cells[i] = 0
            else:
                # off → turn right, flip on, step
                self.adir = (self.adir + 1) % 4
                self.cells[i] = 1
            self.ax = (self.ax + DX[self.adir]) % WIDTH
            self.ay = (self.ay + DY[self.adir]) % HEIGHT
            self.steps += 1

    def update(self, dt: float, events) -> None:
        self._advance(self._spf)
        if self.steps >= RESET_STEPS:
            self._reset(self._seed)

    def render(self) -> Frame:
        f = Frame.black()
        on = (220, 220, 220)
        for y in range(HEIGHT):
            row = y * WIDTH
            for x in range(WIDTH):
                if self.cells[row + x]:
                    f.set(x, y, on)
        f.set(self.ax, self.ay, (255, 40, 40))
        return f
