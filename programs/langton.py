"""Langton's ant — many steps per frame, edges wrap, resets after highway."""
from __future__ import annotations

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
        self._reset()

    def _reset(self) -> None:
        self.cells = bytearray(WIDTH * HEIGHT)  # 0 = off, 1 = on
        self.ax, self.ay = WIDTH // 2, HEIGHT // 2
        self.adir = 0
        self.steps = 0

    def update(self, dt: float, events) -> None:
        for _ in range(STEPS_PER_FRAME):
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
        if self.steps >= RESET_STEPS:
            self._reset()

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
