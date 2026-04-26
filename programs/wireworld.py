"""Wireworld — concentric copper squares with electron pulses orbiting."""
from __future__ import annotations

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


EMPTY = 0
COPPER = 1
HEAD = 2
TAIL = 3
COLORS = ((10, 10, 18), (180, 110, 60), (120, 220, 255), (255, 130, 50))
TICK_HZ = 6.5


def _build() -> list[list[int]]:
    grid = [[EMPTY] * WIDTH for _ in range(HEIGHT)]
    cx, cy = WIDTH // 2, HEIGHT // 2
    # Three concentric square rings.
    for r in (6, 14, 22):
        for x in range(cx - r, cx + r + 1):
            if 0 <= x < WIDTH:
                if 0 <= cy - r < HEIGHT:
                    grid[cy - r][x] = COPPER
                if 0 <= cy + r < HEIGHT:
                    grid[cy + r][x] = COPPER
        for y in range(cy - r, cy + r + 1):
            if 0 <= y < HEIGHT:
                if 0 <= cx - r < WIDTH:
                    grid[y][cx - r] = COPPER
                if 0 <= cx + r < WIDTH:
                    grid[y][cx + r] = COPPER
    # Drop electrons going clockwise on each ring (head + tail pair).
    for r in (6, 14, 22):
        # Head at top-middle going right; tail behind it (one cell left).
        if 0 <= cy - r < HEIGHT and cx + 1 < WIDTH:
            grid[cy - r][cx] = TAIL
            grid[cy - r][cx + 1] = HEAD
    return grid


def _step(cur: list[list[int]]) -> list[list[int]]:
    nxt = [row[:] for row in cur]
    for y in range(HEIGHT):
        row = cur[y]
        for x in range(WIDTH):
            v = row[x]
            if v == EMPTY or v == COPPER:
                if v == COPPER:
                    heads = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if (0 <= nx < WIDTH and 0 <= ny < HEIGHT
                                    and cur[ny][nx] == HEAD):
                                heads += 1
                    if 1 <= heads <= 2:
                        nxt[y][x] = HEAD
            elif v == HEAD:
                nxt[y][x] = TAIL
            elif v == TAIL:
                nxt[y][x] = COPPER
    return nxt


class Wireworld(Program):
    DESCRIPTION = "Wireworld — copper squares with electron pulses orbiting"

    def setup(self) -> None:
        self._grid = _build()
        self._tick_acc = 0.0
        self._tick = 0

    def update(self, dt: float, events) -> None:
        self._tick_acc += dt * TICK_HZ
        while self._tick_acc >= 1.0:
            self._tick_acc -= 1.0
            self._grid = _step(self._grid)
            self._tick += 1
            # Periodic re-injection if all electrons have died (failure mode
            # from Wireworld's strict 1-or-2 head rule on intersections).
            if self._tick % 200 == 0:
                self._grid = _build()

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._grid[y]
            for x in range(WIDTH):
                v = row[x]
                if v:
                    f.set(x, y, COLORS[v])
        return f
