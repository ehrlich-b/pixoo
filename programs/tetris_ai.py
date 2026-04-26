"""Tetris AI — Dellacherie heuristic places its own pieces forever."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


COLS = 10
ROWS = 20
CELL = 3
FIELD_X = 2
FIELD_Y = 2
FIELD_W = COLS * CELL  # 30
FIELD_H = ROWS * CELL  # 60

SIDE_X = 36
NEXT_X = SIDE_X + 2
NEXT_Y = 6
NEXT_CELL = 3
LINES_BAR_X = SIDE_X + 4
LINES_BAR_TOP = NEXT_Y + 4 * NEXT_CELL + 4
LINES_BAR_H = HEIGHT - LINES_BAR_TOP - 3
LINES_BAR_W = 18


SHAPES: dict[str, list[list[tuple[int, int]]]] = {
    "I": [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
    ] * 2,
    "O": [[(1, 0), (2, 0), (1, 1), (2, 1)]] * 4,
    "T": [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
    ] * 2,
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
    ] * 2,
    "J": [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    "L": [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}

PIECE_COLOR = {
    "I": (90, 230, 240),
    "O": (240, 220, 70),
    "T": (200, 90, 240),
    "S": (90, 220, 100),
    "Z": (240, 90, 100),
    "J": (90, 130, 240),
    "L": (240, 160, 70),
}

UNIQUE_ROT = {"O": 1, "I": 2, "S": 2, "Z": 2, "T": 4, "J": 4, "L": 4}

# Dellacherie weights (Pierre Dellacherie's hand-tuned values).
W_LAND = -4.500
W_CLEAR = 3.418
W_RTRANS = -3.218
W_CTRANS = -9.349
W_HOLES = -7.899
W_WELLS = -3.386


def _drop(grid: list[list[str]], shape: list[tuple[int, int]],
          col: int, color: str):
    """Drop piece in column `col`. Return (new_grid, landing_height, cleared, y_final) or None."""
    for x_, y_ in shape:
        cx = col + x_
        if cx < 0 or cx >= COLS:
            return None
    # Find the deepest y_try the piece can occupy.
    for y_try in range(ROWS + 1):
        for x_, y_ in shape:
            cx = col + x_
            cy = y_try + y_
            if cy >= ROWS:
                break
            if cy >= 0 and grid[cy][cx] != ".":
                break
        else:
            continue
        break
    y_final = y_try - 1
    if y_final < 0:
        return None
    new_grid = [row[:] for row in grid]
    for x_, y_ in shape:
        cx = col + x_
        cy = y_final + y_
        if cy < 0:
            return None
        new_grid[cy][cx] = color
    bottom_y = y_final + max(y_ for _, y_ in shape)
    landing_height = ROWS - bottom_y - 1
    cleared = 0
    out_rows: list[list[str]] = []
    for r in range(ROWS):
        if all(new_grid[r][c] != "." for c in range(COLS)):
            cleared += 1
        else:
            out_rows.append(new_grid[r])
    while len(out_rows) < ROWS:
        out_rows.insert(0, ["."] * COLS)
    return out_rows, landing_height, cleared, y_final


def _heuristic(grid: list[list[str]], landing_height: int, cleared: int) -> float:
    rtrans = 0
    for r in range(ROWS):
        prev_filled = True  # left wall counts as filled
        for c in range(COLS):
            cur_filled = grid[r][c] != "."
            if cur_filled != prev_filled:
                rtrans += 1
            prev_filled = cur_filled
        if not prev_filled:
            rtrans += 1
    ctrans = 0
    heights = [0] * COLS
    for c in range(COLS):
        prev_filled = True
        for r in range(ROWS):
            cur_filled = grid[r][c] != "."
            if cur_filled != prev_filled:
                ctrans += 1
            prev_filled = cur_filled
            if cur_filled and heights[c] == 0:
                heights[c] = ROWS - r
        if not prev_filled:
            ctrans += 1
    holes = 0
    for c in range(COLS):
        seen_top = False
        for r in range(ROWS):
            if grid[r][c] != ".":
                seen_top = True
            elif seen_top:
                holes += 1
    well_sum = 0
    for c in range(COLS):
        left = heights[c - 1] if c > 0 else ROWS
        right = heights[c + 1] if c < COLS - 1 else ROWS
        if heights[c] < left and heights[c] < right:
            depth = min(left, right) - heights[c]
            well_sum += depth * (depth + 1) // 2
    return (W_LAND * landing_height + W_CLEAR * cleared
            + W_RTRANS * rtrans + W_CTRANS * ctrans
            + W_HOLES * holes + W_WELLS * well_sum)


class TetrisAI(Program):
    DESCRIPTION = "Tetris AI — Dellacherie heuristic plays itself"

    def setup(self) -> None:
        self._fall_dt = 0.0
        self._reset()

    def _reset(self) -> None:
        self._grid = [["."] * COLS for _ in range(ROWS)]
        self._bag: list[str] = []
        self._cur = self._take()
        self._next = self._take()
        self._lines = 0
        self._gameover_hold = 0.0
        self._plan()

    def _take(self) -> str:
        if not self._bag:
            self._bag = list("IOTSZJL")
            random.shuffle(self._bag)
        return self._bag.pop()

    def _plan(self) -> None:
        best_score = -1e18
        best_rot = 0
        best_col = 3
        best_y = 0
        n_rot = UNIQUE_ROT[self._cur]
        for rot in range(n_rot):
            shape = SHAPES[self._cur][rot]
            for col in range(-2, COLS + 2):
                res = _drop(self._grid, shape, col, self._cur)
                if res is None:
                    continue
                new_grid, lh, cleared, y_final = res
                score = _heuristic(new_grid, lh, cleared)
                if score > best_score:
                    best_score = score
                    best_rot = rot
                    best_col = col
                    best_y = y_final
        if best_score == -1e18:
            self._gameover_hold = 1.6
            return
        self._cur_rot = best_rot
        self._cur_col = best_col
        self._cur_y = 0
        self._cur_target = best_y

    def update(self, dt: float, events) -> None:
        if self._gameover_hold > 0:
            self._gameover_hold -= dt
            if self._gameover_hold <= 0:
                self._reset()
            return
        self._fall_dt += dt
        if self._fall_dt < 0.045:
            return
        self._fall_dt = 0
        if self._cur_y < self._cur_target:
            self._cur_y += 1
            return
        # Lock + clear.
        shape = SHAPES[self._cur][self._cur_rot]
        for dx, dy in shape:
            cx = self._cur_col + dx
            cy = self._cur_y + dy
            if 0 <= cx < COLS and 0 <= cy < ROWS:
                self._grid[cy][cx] = self._cur
        cleared = 0
        kept: list[list[str]] = []
        for r in range(ROWS):
            if all(self._grid[r][c] != "." for c in range(COLS)):
                cleared += 1
            else:
                kept.append(self._grid[r])
        while len(kept) < ROWS:
            kept.insert(0, ["."] * COLS)
        self._grid = kept
        self._lines += cleared
        self._cur = self._next
        self._next = self._take()
        self._plan()

    def render(self) -> Frame:
        f = Frame.black()
        # Field border + dim background.
        for y in range(FIELD_Y - 1, FIELD_Y + FIELD_H + 1):
            for x in range(FIELD_X - 1, FIELD_X + FIELD_W + 1):
                if (x in (FIELD_X - 1, FIELD_X + FIELD_W)
                        or y in (FIELD_Y - 1, FIELD_Y + FIELD_H)):
                    f.set(x, y, (60, 60, 78))
                else:
                    f.set(x, y, (8, 8, 14))
        # Locked grid.
        for r in range(ROWS):
            for c in range(COLS):
                v = self._grid[r][c]
                if v != ".":
                    self._cell(f, c, r, PIECE_COLOR[v])
        # Falling piece.
        if self._gameover_hold <= 0:
            shape = SHAPES[self._cur][self._cur_rot]
            color = PIECE_COLOR[self._cur]
            for dx, dy in shape:
                cx = self._cur_col + dx
                cy = self._cur_y + dy
                if 0 <= cx < COLS and 0 <= cy < ROWS:
                    self._cell(f, cx, cy, color)
        # Next-piece preview frame.
        for y in range(NEXT_Y - 1, NEXT_Y + 4 * NEXT_CELL + 1):
            for x in range(NEXT_X - 1, NEXT_X + 4 * NEXT_CELL + 1):
                if (x in (NEXT_X - 1, NEXT_X + 4 * NEXT_CELL)
                        or y in (NEXT_Y - 1, NEXT_Y + 4 * NEXT_CELL)):
                    f.set(x, y, (50, 50, 70))
        nshape = SHAPES[self._next][0]
        ncolor = PIECE_COLOR[self._next]
        for dx, dy in nshape:
            x0 = NEXT_X + dx * NEXT_CELL
            y0 = NEXT_Y + dy * NEXT_CELL
            for yy in range(y0, y0 + NEXT_CELL):
                for xx in range(x0, x0 + NEXT_CELL):
                    f.set(xx, yy, ncolor)
        # Lines bar (right side, fills with cleared lines).
        fill = min(LINES_BAR_H, self._lines)
        for y in range(LINES_BAR_TOP, LINES_BAR_TOP + LINES_BAR_H):
            for x in range(LINES_BAR_X, LINES_BAR_X + LINES_BAR_W):
                if y >= LINES_BAR_TOP + LINES_BAR_H - fill:
                    t = (y - (LINES_BAR_TOP + LINES_BAR_H - fill)) / max(1, fill)
                    r = int(60 + 180 * t)
                    g = int(180 + 60 * (1 - t))
                    b = int(220 - 100 * t)
                    f.set(x, y, (r, g, b))
                else:
                    f.set(x, y, (18, 18, 28))
        return f

    def _cell(self, f: Frame, c: int, r: int,
              color: tuple[int, int, int]) -> None:
        x0 = FIELD_X + c * CELL
        y0 = FIELD_Y + r * CELL
        for yy in range(y0, y0 + CELL):
            for xx in range(x0, x0 + CELL):
                f.set(xx, yy, color)
        f.set(x0, y0, (min(255, color[0] + 60),
                      min(255, color[1] + 60),
                      min(255, color[2] + 60)))
