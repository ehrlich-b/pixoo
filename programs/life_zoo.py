"""Life zoo — cycle curated Game of Life patterns (Gosper gun, pulsar, acorn)."""
from __future__ import annotations

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


def _parse(rows: list[str]) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c == "X":
                cells.append((x, y))
    return cells


GLIDER_GUN = _parse([
    "........................X...........",
    "......................X.X...........",
    "............XX......XX............XX",
    "...........X...X....XX............XX",
    "XX........X.....X...XX..............",
    "XX........X...X.XX....X.X...........",
    "..........X.....X.......X...........",
    "...........X...X....................",
    "............XX......................",
])

PULSAR = _parse([
    "..XXX...XXX..",
    ".............",
    "X....X.X....X",
    "X....X.X....X",
    "X....X.X....X",
    "..XXX...XXX..",
    ".............",
    "..XXX...XXX..",
    "X....X.X....X",
    "X....X.X....X",
    "X....X.X....X",
    ".............",
    "..XXX...XXX..",
])

R_PENTOMINO = _parse([
    ".XX",
    "XX.",
    ".X.",
])

ACORN = _parse([
    ".X.....",
    "...X...",
    "XX..XXX",
])

DIEHARD = _parse([
    "......X.",
    "XX......",
    ".X...XXX",
])

LWSS = _parse([  # lightweight spaceship
    ".X..X",
    "X....",
    "X...X",
    "XXXX.",
])

PATTERNS = [
    ("gun",     GLIDER_GUN, 12, 26, 16.0),
    ("pulsar",  PULSAR,     25, 26, 12.0),
    ("acorn",   ACORN,      28, 30, 18.0),
    ("R-pent",  R_PENTOMINO, 30, 30, 16.0),
    ("diehard", DIEHARD,    28, 30, 14.0),
    ("LWSS",    LWSS,        2, 30, 10.0),
]

TICK_HZ = 15
ALIVE_AGE_MAX = 24
GHOST_AGE_MAX = 14


class LifeZoo(Program):
    DESCRIPTION = "Game of Life — gun, pulsar, acorn, R-pent, diehard, LWSS"

    def setup(self) -> None:
        self._idx = 0
        self._tick_dt = 0.0
        self._phase_t = 0.0
        self._grid = [[0] * WIDTH for _ in range(HEIGHT)]
        self._age = [[0] * WIDTH for _ in range(HEIGHT)]
        self._ghost = [[0] * WIDTH for _ in range(HEIGHT)]
        self._load(self._idx)

    def _load(self, idx: int) -> None:
        _, pattern, ox, oy, _ = PATTERNS[idx]
        self._grid = [[0] * WIDTH for _ in range(HEIGHT)]
        self._age = [[0] * WIDTH for _ in range(HEIGHT)]
        self._ghost = [[0] * WIDTH for _ in range(HEIGHT)]
        for x, y in pattern:
            xx = ox + x
            yy = oy + y
            if 0 <= xx < WIDTH and 0 <= yy < HEIGHT:
                self._grid[yy][xx] = 1
                self._age[yy][xx] = 1
        self._tick_dt = 0.0
        self._phase_t = 0.0

    def update(self, dt: float, events) -> None:
        self._phase_t += dt
        phase_len = PATTERNS[self._idx][4]
        if self._phase_t > phase_len:
            self._idx = (self._idx + 1) % len(PATTERNS)
            self._load(self._idx)
            return
        self._tick_dt += dt
        if self._tick_dt < 1.0 / TICK_HZ:
            return
        self._tick_dt = 0
        new_grid = [[0] * WIDTH for _ in range(HEIGHT)]
        for y in range(HEIGHT):
            ym = (y - 1) % HEIGHT
            yp = (y + 1) % HEIGHT
            row_m = self._grid[ym]
            row = self._grid[y]
            row_p = self._grid[yp]
            new_row = new_grid[y]
            for x in range(WIDTH):
                xm = (x - 1) % WIDTH
                xp = (x + 1) % WIDTH
                n = (row_m[xm] + row_m[x] + row_m[xp]
                     + row[xm] + row[xp]
                     + row_p[xm] + row_p[x] + row_p[xp])
                if row[x]:
                    if n == 2 or n == 3:
                        new_row[x] = 1
                else:
                    if n == 3:
                        new_row[x] = 1
        # Update age + ghost arrays.
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if new_grid[y][x]:
                    self._age[y][x] = min(ALIVE_AGE_MAX, self._age[y][x] + 1)
                    self._ghost[y][x] = GHOST_AGE_MAX
                else:
                    self._age[y][x] = 0
                    if self._ghost[y][x] > 0:
                        self._ghost[y][x] -= 1
        self._grid = new_grid

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self._grid[y][x]:
                    a = self._age[y][x] / ALIVE_AGE_MAX
                    r = int(160 + 95 * a)
                    g = int(255 - 80 * a)
                    b = int(120 + 60 * (1 - a))
                    f.set(x, y, (r, g, b))
                elif self._ghost[y][x] > 0:
                    s = self._ghost[y][x] / GHOST_AGE_MAX
                    r = int(60 * s)
                    g = int(40 * s)
                    b = int(110 * s)
                    f.set(x, y, (r, g, b))
        return f
