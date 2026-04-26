"""Conway's Game of Life — cycles classic seeds, resets on stasis."""
from __future__ import annotations

import random
from collections import deque

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

GENS_PER_SEC = 10.0
STASIS_GENS = 60   # no changes for this many gens → reset
HISTORY_LEN = 16   # detect short-cycle oscillators by hashing recent states
MAX_GENS = 2000    # hard cap — even long-runners get cycled eventually


# Each seed is a list of (x, y) live cells relative to its origin, plus an
# origin in grid space. Coords lifted from LifeWiki.
def _pattern(cells_str: str) -> list[tuple[int, int]]:
    out = []
    for y, line in enumerate(cells_str.strip("\n").split("\n")):
        for x, c in enumerate(line):
            if c == "#":
                out.append((x, y))
    return out


R_PENTOMINO = _pattern("""
.##
##.
.#.
""")

ACORN = _pattern("""
.#.....
...#...
##..###
""")

DIEHARD = _pattern("""
......#.
##......
.#...###
""")

# Gosper glider gun — 36x9
GLIDER_GUN = _pattern("""
........................#...........
......................#.#...........
............##......##............##
...........#...#....##............##
##........#.....#...##..............
##........#...#.##....#.#...........
..........#.....#.......#...........
...........#...#....................
............##......................
""")

PULSAR = _pattern("""
..###...###..
.............
#....#.#....#
#....#.#....#
#....#.#....#
..###...###..
.............
..###...###..
#....#.#....#
#....#.#....#
#....#.#....#
.............
..###...###..
""")


def _place(cells: list[tuple[int, int]], ox: int, oy: int) -> set[tuple[int, int]]:
    return {(x + ox, y + oy) for x, y in cells}


def _random_soup(density: float = 0.28) -> set[tuple[int, int]]:
    return {(x, y) for y in range(HEIGHT) for x in range(WIDTH)
            if random.random() < density}


SEEDS = [
    ("r-pentomino", lambda: _place(R_PENTOMINO, WIDTH // 2 - 1, HEIGHT // 2 - 1)),
    ("acorn",       lambda: _place(ACORN,       WIDTH // 2 - 3, HEIGHT // 2 - 1)),
    ("diehard",     lambda: _place(DIEHARD,     WIDTH // 2 - 4, HEIGHT // 2 - 1)),
    ("glider-gun",  lambda: _place(GLIDER_GUN,  4,              8)),
    ("pulsar",      lambda: _place(PULSAR,      WIDTH // 2 - 6, HEIGHT // 2 - 6)),
    ("soup",        lambda: _random_soup()),
]


def _step(live: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """One Life generation. Toroidal edges so patterns wrap instead of dying at borders."""
    counts: dict[tuple[int, int], int] = {}
    for (x, y) in live:
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                n = ((x + dx) % WIDTH, (y + dy) % HEIGHT)
                counts[n] = counts.get(n, 0) + 1
    nxt: set[tuple[int, int]] = set()
    for cell, c in counts.items():
        if c == 3 or (c == 2 and cell in live):
            nxt.add(cell)
    # cells with zero neighbors aren't in counts; they just die.
    return nxt


class Life(Program):
    DESCRIPTION = "Conway's Game of Life — cycles classic seeds, resets on stasis"

    def setup(self) -> None:
        self._seed_idx = 0
        self._gen_accum = 0.0
        self._load_seed()

    def _load_seed(self) -> None:
        name, factory = SEEDS[self._seed_idx % len(SEEDS)]
        self._seed_name = name
        self.live = factory()
        self.gen = 0
        self.history: deque[int] = deque(maxlen=HISTORY_LEN)
        self.stasis = 0

    def update(self, dt: float, events) -> None:
        self._gen_accum += dt * GENS_PER_SEC
        while self._gen_accum >= 1.0:
            self._gen_accum -= 1.0
            self._advance()

    def _advance(self) -> None:
        prev = self.live
        self.live = _step(self.live)
        self.gen += 1
        if self.live == prev:
            self.stasis += 1
        else:
            self.stasis = 0
        h = hash(frozenset(self.live))
        if h in self.history and self.gen > HISTORY_LEN:
            # short-period oscillator stuck in a loop; let it breathe a little
            self.stasis = max(self.stasis, STASIS_GENS // 2)
        self.history.append(h)
        if (self.stasis >= STASIS_GENS
                or self.gen >= MAX_GENS
                or not self.live):
            self._seed_idx += 1
            self._load_seed()

    def render(self) -> Frame:
        f = Frame.black()
        for (x, y) in self.live:
            f.set(x, y, (255, 255, 255))
        return f
