"""Defrag — scrambled rainbow tile grid sorted by selection sort with R/W heads."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


TILE = 4
COLS = WIDTH // TILE   # 16
ROWS = HEIGHT // TILE  # 16
N = COLS * ROWS         # 256
STEPS_PER_FRAME = 70


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


_PAL = [_hsv(i / N, 0.9, 0.95) for i in range(N)]


class Defrag(Program):
    DESCRIPTION = "Defragmenter — scrambled rainbow tiles sort with R/W heads"

    def setup(self) -> None:
        self._reset()

    def _reset(self) -> None:
        self._tiles = list(range(N))
        random.shuffle(self._tiles)
        self._pos = 0
        self._read = 0
        self._best = 0
        self._done = False
        self._hold = 0.0

    def update(self, dt: float, events) -> None:
        if self._done:
            self._hold -= dt
            if self._hold <= 0:
                self._reset()
            return
        for _ in range(STEPS_PER_FRAME):
            if self._pos >= N - 1:
                self._done = True
                self._hold = 1.8
                return
            if self._read >= N:
                # Pass over: swap min into pos, advance.
                if self._best != self._pos:
                    self._tiles[self._pos], self._tiles[self._best] = (
                        self._tiles[self._best], self._tiles[self._pos])
                self._pos += 1
                self._read = self._pos
                self._best = self._pos
            else:
                if self._tiles[self._read] < self._tiles[self._best]:
                    self._best = self._read
                self._read += 1

    def render(self) -> Frame:
        f = Frame.black()
        # Paint tile body.
        for r in range(ROWS):
            base_y = r * TILE
            for c in range(COLS):
                idx = r * COLS + c
                col = _PAL[self._tiles[idx]]
                base_x = c * TILE
                for yy in range(base_y, base_y + TILE):
                    for xx in range(base_x, base_x + TILE):
                        f.set(xx, yy, col)
        # Outline highlights — drawn on top.
        def _outline(idx: int, color: tuple[int, int, int]) -> None:
            if not 0 <= idx < N:
                return
            c = idx % COLS
            r = idx // COLS
            x0 = c * TILE
            y0 = r * TILE
            for x in range(x0, x0 + TILE):
                f.set(x, y0, color)
                f.set(x, y0 + TILE - 1, color)
            for y in range(y0, y0 + TILE):
                f.set(x0, y, color)
                f.set(x0 + TILE - 1, y, color)
        # Sorted boundary (orange), best-so-far (green), read head (white).
        if not self._done:
            _outline(self._pos, (255, 170, 30))
            if self._best != self._pos:
                _outline(self._best, (90, 230, 110))
            if self._read < N and self._read != self._pos and self._read != self._best:
                _outline(self._read, (240, 240, 240))
        return f
