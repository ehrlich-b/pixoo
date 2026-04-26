"""Abelian sandpile — drop grains at the center, watch a fractal grow."""
from __future__ import annotations

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
        self._grid: list[list[int]] = [[0] * WIDTH for _ in range(HEIGHT)]
        self._dropped = 0

    def update(self, dt: float, events) -> None:
        grid = self._grid
        q: deque[tuple[int, int]] = deque()
        for _ in range(DROPS_PER_FRAME):
            grid[CY][CX] += 1
            if grid[CY][CX] >= 4:
                q.append((CX, CY))
        while q:
            x, y = q.popleft()
            if grid[y][x] < 4:
                continue
            grid[y][x] -= 4
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                    grid[ny][nx] += 1
                    if grid[ny][nx] >= 4:
                        q.append((nx, ny))
        self._dropped += DROPS_PER_FRAME
        if self._dropped >= RESET_AT:
            self._grid = [[0] * WIDTH for _ in range(HEIGHT)]
            self._dropped = 0

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._grid[y]
            for x in range(WIDTH):
                v = row[x]
                if v:
                    f.set(x, y, COLORS[v if v < 4 else 3])
        return f
