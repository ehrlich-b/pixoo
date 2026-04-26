"""Schelling segregation — two-color agents seek same-colored neighborhoods."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


EMPTY = 0
RED = 1
BLUE = 2
COLORS = ((20, 20, 30), (240, 100, 90), (90, 130, 240))
DENSITY = 0.92          # fraction of cells occupied
RED_FRAC = 0.5          # split among reds vs blues
TOLERANCE = 0.40        # at least this fraction of *occupied* neighbours must match
MOVES_PER_TICK = 280    # how many unhappy moves to attempt per frame
RESET_HAPPY = 0.985     # reset once almost everyone is happy


class Schelling(Program):
    DESCRIPTION = "Schelling segregation — agents seek same-color neighbours"

    def setup(self) -> None:
        self._reset()

    def _reset(self) -> None:
        cells: list[int] = []
        for _ in range(WIDTH * HEIGHT):
            r = random.random()
            if r > DENSITY:
                cells.append(EMPTY)
            elif r > DENSITY * (1 - RED_FRAC):
                cells.append(RED)
            else:
                cells.append(BLUE)
        random.shuffle(cells)
        self._grid = [cells[y * WIDTH:(y + 1) * WIDTH] for y in range(HEIGHT)]
        self._steps = 0

    def _is_unhappy(self, x: int, y: int) -> bool:
        c = self._grid[y][x]
        if c == EMPTY:
            return False
        same = 0
        occupied = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < WIDTH and 0 <= ny < HEIGHT:
                    nc = self._grid[ny][nx]
                    if nc != EMPTY:
                        occupied += 1
                        if nc == c:
                            same += 1
        if occupied == 0:
            return False
        return (same / occupied) < TOLERANCE

    def _happy_fraction(self) -> float:
        occ = 0; happy = 0
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self._grid[y][x] != EMPTY:
                    occ += 1
                    if not self._is_unhappy(x, y):
                        happy += 1
        return 1.0 if occ == 0 else happy / occ

    def update(self, dt: float, events) -> None:
        moved = 0
        attempts = 0
        empties = [(x, y) for y in range(HEIGHT) for x in range(WIDTH)
                   if self._grid[y][x] == EMPTY]
        while moved < MOVES_PER_TICK and attempts < MOVES_PER_TICK * 4 and empties:
            attempts += 1
            x = random.randrange(WIDTH)
            y = random.randrange(HEIGHT)
            if self._grid[y][x] == EMPTY:
                continue
            if not self._is_unhappy(x, y):
                continue
            ei = random.randrange(len(empties))
            ex, ey = empties[ei]
            # Move
            self._grid[ey][ex] = self._grid[y][x]
            self._grid[y][x] = EMPTY
            empties[ei] = (x, y)
            moved += 1
        self._steps += 1
        if self._steps % 80 == 0 and self._happy_fraction() > RESET_HAPPY:
            self._reset()

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._grid[y]
            for x in range(WIDTH):
                f.set(x, y, COLORS[row[x]])
        return f
