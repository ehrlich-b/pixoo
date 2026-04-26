"""Falling sand — gravity pulls grains into piles, multi-color layers."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


# Color streams; each spawn picks one. Layers form as colors stop arriving.
SAND_COLORS = (
    (235, 200, 130),
    (220, 130, 90),
    (110, 175, 220),
    (180, 140, 220),
    (130, 200, 150),
)
EMPTY = 0  # cell 0 is empty
SPAWN_PER_FRAME = 6
RESET_AT = 2400  # total grains before clearing


class Sand(Program):
    DESCRIPTION = "Falling sand — gravity-driven piles in shifting colors"

    def setup(self) -> None:
        self._grid: list[list[int]] = [[EMPTY] * WIDTH for _ in range(HEIGHT)]
        self._stream_idx = 0
        self._stream_t = 0.0
        self._count = 0

    def _step_physics(self) -> None:
        g = self._grid
        for y in range(HEIGHT - 2, -1, -1):
            row = g[y]
            below = g[y + 1]
            for x in range(WIDTH):
                v = row[x]
                if v == EMPTY:
                    continue
                if below[x] == EMPTY:
                    row[x] = EMPTY
                    below[x] = v
                    continue
                left_open = x > 0 and below[x - 1] == EMPTY
                right_open = x < WIDTH - 1 and below[x + 1] == EMPTY
                if left_open and right_open:
                    if random.random() < 0.5:
                        below[x - 1] = v
                    else:
                        below[x + 1] = v
                    row[x] = EMPTY
                elif left_open:
                    below[x - 1] = v
                    row[x] = EMPTY
                elif right_open:
                    below[x + 1] = v
                    row[x] = EMPTY

    def update(self, dt: float, events) -> None:
        self._step_physics()
        # Stream switches every ~3 seconds.
        self._stream_t += dt
        if self._stream_t > 3.0:
            self._stream_t = 0.0
            self._stream_idx = (self._stream_idx + 1) % len(SAND_COLORS)
        # Spawn grains in a narrow column near the centre that wanders slightly.
        col_center = WIDTH // 2 + int(8 * (self._stream_idx - 2))
        for _ in range(SPAWN_PER_FRAME):
            x = col_center + random.randint(-3, 3)
            if 0 <= x < WIDTH and self._grid[0][x] == EMPTY:
                self._grid[0][x] = self._stream_idx + 1   # 1-indexed
                self._count += 1
        if self._count >= RESET_AT:
            self._grid = [[EMPTY] * WIDTH for _ in range(HEIGHT)]
            self._count = 0

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._grid[y]
            for x in range(WIDTH):
                v = row[x]
                if v:
                    f.set(x, y, SAND_COLORS[v - 1])
        return f
