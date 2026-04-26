"""Forest-fire CA — trees grow, lightning ignites, fire spreads."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


EMPTY = 0
TREE = 1
FIRE = 2
COLORS = ((30, 25, 18), (60, 160, 80), (255, 130, 40))
EMBER = (200, 70, 30)
GROWTH_P = 0.012
LIGHTNING_P = 0.00012


class ForestFire(Program):
    DESCRIPTION = "Forest fire CA — trees grow, lightning strikes, fire spreads"

    def setup(self) -> None:
        self._grid = [[TREE if random.random() < 0.3 else EMPTY
                       for _ in range(WIDTH)] for _ in range(HEIGHT)]

    def update(self, dt: float, events) -> None:
        cur = self._grid
        nxt = [row[:] for row in cur]
        for y in range(HEIGHT):
            row = cur[y]
            nrow = nxt[y]
            for x in range(WIDTH):
                v = row[x]
                if v == FIRE:
                    nrow[x] = EMPTY
                    continue
                if v == TREE:
                    burning = False
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                                if cur[ny][nx] == FIRE:
                                    burning = True
                                    break
                        if burning:
                            break
                    if burning:
                        nrow[x] = FIRE
                    elif random.random() < LIGHTNING_P:
                        nrow[x] = FIRE
                else:  # EMPTY
                    if random.random() < GROWTH_P:
                        nrow[x] = TREE
        self._grid = nxt

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._grid[y]
            for x in range(WIDTH):
                v = row[x]
                if v:
                    f.set(x, y, COLORS[v])
        return f
