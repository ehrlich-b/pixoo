"""TSP — 2-opt detangler on random cities, restarts when near-optimal."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_CITIES = 22
RESET_NEAR = 1.04   # reset once tour is within 4% of best-found per run
SWAPS_PER_FRAME = 600


def _line(f: Frame, x0: int, y0: int, x1: int, y1: int,
          color: tuple[int, int, int]) -> None:
    dx = abs(x1 - x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0); sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        f.set(x0, y0, color)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy


class TSP(Program):
    DESCRIPTION = "TSP — 2-opt swap detangler, restarts on convergence"

    def setup(self) -> None:
        self._begin()

    def _begin(self) -> None:
        self._cities = [(random.uniform(2, WIDTH - 2), random.uniform(2, HEIGHT - 2))
                        for _ in range(N_CITIES)]
        self._tour = list(range(N_CITIES))
        random.shuffle(self._tour)
        self._cur_len = self._length()
        self._best_len = self._cur_len
        self._stagnant = 0

    def _seg(self, i: int, j: int) -> float:
        a = self._cities[self._tour[i]]
        b = self._cities[self._tour[j % N_CITIES]]
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _length(self) -> float:
        return sum(self._seg(i, i + 1) for i in range(N_CITIES))

    def update(self, dt: float, events) -> None:
        improved = False
        for _ in range(SWAPS_PER_FRAME):
            i = random.randrange(N_CITIES - 1)
            j = random.randrange(i + 1, N_CITIES)
            # Compute delta of reversing tour[i..j].
            a = self._tour[(i - 1) % N_CITIES]
            b = self._tour[i]
            c = self._tour[j]
            d = self._tour[(j + 1) % N_CITIES]
            ca = self._cities[a]; cb = self._cities[b]
            cc = self._cities[c]; cd = self._cities[d]
            old = (math.hypot(ca[0] - cb[0], ca[1] - cb[1])
                   + math.hypot(cc[0] - cd[0], cc[1] - cd[1]))
            new = (math.hypot(ca[0] - cc[0], ca[1] - cc[1])
                   + math.hypot(cb[0] - cd[0], cb[1] - cd[1]))
            if new < old:
                self._tour[i:j + 1] = reversed(self._tour[i:j + 1])
                self._cur_len += new - old
                improved = True
                if self._cur_len < self._best_len:
                    self._best_len = self._cur_len
        if not improved:
            self._stagnant += 1
            if self._stagnant > 30:
                self._begin()
        else:
            self._stagnant = 0

    def render(self) -> Frame:
        f = Frame.black()
        for i in range(N_CITIES):
            a = self._cities[self._tour[i]]
            b = self._cities[self._tour[(i + 1) % N_CITIES]]
            _line(f, int(a[0]), int(a[1]), int(b[0]), int(b[1]),
                  (60, 130, 200))
        for cx, cy in self._cities:
            f.set(int(cx), int(cy), (255, 220, 110))
        return f
