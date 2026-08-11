"""Abelian sandpile — drop grains at the center, watch a fractal grow.

Optional params (all deterministic; defaults reproduce classic center-drop):
    seed              int — grains drop at random.Random(seed) positions instead
                            of the center (still an abelian sandpile)
    steps             int — pre-drop this many grains in setup()
    drops_per_frame   int — grains dropped per update() (default DROPS_PER_FRAME)
"""
from __future__ import annotations

import random
from collections import deque

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


CX, CY = WIDTH // 2, HEIGHT // 2
COLORS = (
    (0, 0, 0),         # 0 grains — empty
    (60, 90, 170),     # 1
    (200, 90, 60),     # 2
    (240, 220, 110),   # 3
)
DROPS_PER_FRAME = 80
RESET_AT = 4500     # ~total grains, then reset


class Sandpile(Program):
    DESCRIPTION = "Abelian sandpile — center drops topple into a fractal"

    def setup(self) -> None:
        self._seed = int(self.params["seed"]) if "seed" in self.params else None
        self._dpf = int(self.params.get("drops_per_frame", DROPS_PER_FRAME))
        self._rng = random.Random(self._seed) if self._seed is not None else None
        self._reset()
        self._drop_n(int(self.params.get("steps", 0) or 0))

    def _reset(self) -> None:
        self._grid: list[list[int]] = [[0] * WIDTH for _ in range(HEIGHT)]
        self._dropped = 0

    def _drop_one(self) -> None:
        grid = self._grid
        if self._rng is not None:
            x, y = self._rng.randrange(WIDTH), self._rng.randrange(HEIGHT)
        else:
            x, y = CX, CY
        grid[y][x] += 1
        if grid[y][x] >= 4:
            q: deque[tuple[int, int]] = deque([(x, y)])
            while q:
                tx, ty = q.popleft()
                if grid[ty][tx] < 4:
                    continue
                grid[ty][tx] -= 4
                for nx, ny in ((tx - 1, ty), (tx + 1, ty), (tx, ty - 1), (tx, ty + 1)):
                    if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                        grid[ny][nx] += 1
                        if grid[ny][nx] >= 4:
                            q.append((nx, ny))

    def _drop_n(self, n: int) -> None:
        for _ in range(n):
            self._drop_one()
            self._dropped += 1

    def update(self, dt: float, events) -> None:
        self._drop_n(self._dpf)
        if self._dropped >= RESET_AT:
            self._reset()

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._grid[y]
            for x in range(WIDTH):
                v = row[x]
                if v:
                    f.set(x, y, COLORS[v if v < 4 else 3])
        return f
