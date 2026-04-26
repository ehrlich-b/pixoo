"""Maze — DFS generator + BFS solver, repeats forever."""
from __future__ import annotations

import random
from collections import deque

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


GRID_W = 63
GRID_H = 63
WALL_COLOR = (40, 60, 95)
BG_COLOR = (12, 16, 26)
SOLVE_COLOR = (240, 220, 110)
HEAD_COLOR = (255, 90, 110)
GEN_PER_TICK = 8
SOLVE_PER_TICK = 4
SOLVE_HOLD = 60


class Maze(Program):
    DESCRIPTION = "Maze — DFS generator → BFS solver, on repeat"

    def setup(self) -> None:
        self._begin()

    def _begin(self) -> None:
        self._wall = [[True] * GRID_W for _ in range(GRID_H)]
        self._wall[1][1] = False
        self._stack: list[tuple[int, int]] = [(1, 1)]
        self._visited: set[tuple[int, int]] = {(1, 1)}
        self._gen_done = False
        self._solve_path: list[tuple[int, int]] | None = None
        self._solve_idx = 0
        self._hold = 0

    def _carve(self) -> None:
        if not self._stack:
            self._gen_done = True
            return
        x, y = self._stack[-1]
        choices: list[tuple[int, int, int, int]] = []
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nx, ny = x + dx, y + dy
            if (1 <= nx < GRID_W - 1 and 1 <= ny < GRID_H - 1
                    and (nx, ny) not in self._visited):
                choices.append((nx, ny, dx, dy))
        if choices:
            nx, ny, dx, dy = random.choice(choices)
            self._wall[ny][nx] = False
            self._wall[y + dy // 2][x + dx // 2] = False
            self._visited.add((nx, ny))
            self._stack.append((nx, ny))
        else:
            self._stack.pop()

    def _build_solve(self) -> None:
        start = (1, 1)
        end = (GRID_W - 2, GRID_H - 2)
        prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        q: deque[tuple[int, int]] = deque([start])
        while q:
            cx, cy = q.popleft()
            if (cx, cy) == end:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < GRID_W and 0 <= ny < GRID_H
                        and not self._wall[ny][nx]
                        and (nx, ny) not in prev):
                    prev[(nx, ny)] = (cx, cy)
                    q.append((nx, ny))
        path: list[tuple[int, int]] = []
        cur: tuple[int, int] | None = end
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        self._solve_path = path
        self._solve_idx = 0

    def update(self, dt: float, events) -> None:
        if not self._gen_done:
            for _ in range(GEN_PER_TICK):
                self._carve()
                if self._gen_done:
                    self._build_solve()
                    break
            return
        if self._solve_path is not None:
            if self._solve_idx < len(self._solve_path):
                self._solve_idx = min(len(self._solve_path),
                                      self._solve_idx + SOLVE_PER_TICK)
            else:
                self._hold += 1
                if self._hold >= SOLVE_HOLD:
                    self._begin()

    def render(self) -> Frame:
        f = Frame.black()
        ox = (WIDTH - GRID_W) // 2
        oy = (HEIGHT - GRID_H) // 2
        for y in range(GRID_H):
            row = self._wall[y]
            py = y + oy
            for x in range(GRID_W):
                f.set(x + ox, py, WALL_COLOR if row[x] else BG_COLOR)
        # Active carve cursor (red dot in last stack pos)
        if not self._gen_done and self._stack:
            sx, sy = self._stack[-1]
            f.set(sx + ox, sy + oy, HEAD_COLOR)
        if self._solve_path is not None and self._solve_idx > 0:
            for i in range(self._solve_idx):
                cx, cy = self._solve_path[i]
                f.set(cx + ox, cy + oy, SOLVE_COLOR)
        return f
