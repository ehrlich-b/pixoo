"""Pathfind — A* search visualization with frontier expansion + final path."""
from __future__ import annotations

import heapq
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


WALL = 1
START_C = (110, 240, 110)
GOAL_C = (255, 110, 130)
WALL_C = (40, 50, 70)
OPEN_C = (60, 100, 160)
CLOSED_C = (40, 60, 90)
PATH_C = (255, 230, 110)
WALL_DENSITY = 0.27
HOLD_FRAMES = 50


def _heur(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Pathfind(Program):
    DESCRIPTION = "Pathfind — A* expansion + path, fresh map every cycle"

    def setup(self) -> None:
        self._begin()

    def _begin(self) -> None:
        while True:
            self._grid = [[1 if random.random() < WALL_DENSITY else 0
                           for _ in range(WIDTH)] for _ in range(HEIGHT)]
            self._start = (1, HEIGHT // 2)
            self._goal = (WIDTH - 2, HEIGHT // 2)
            self._grid[self._start[1]][self._start[0]] = 0
            self._grid[self._goal[1]][self._goal[0]] = 0
            if self._reachable():
                break
        self._open: list[tuple[int, int, tuple[int, int]]] = []
        self._g: dict[tuple[int, int], int] = {self._start: 0}
        self._closed: set[tuple[int, int]] = set()
        self._came: dict[tuple[int, int], tuple[int, int] | None] = {self._start: None}
        heapq.heappush(self._open, (_heur(self._start, self._goal), 0, self._start))
        self._path: list[tuple[int, int]] | None = None
        self._path_idx = 0
        self._hold = 0

    def _reachable(self) -> bool:
        # quick BFS to ensure goal is reachable
        from collections import deque
        seen = {self._start}
        q = deque([self._start])
        while q:
            cx, cy = q.popleft()
            if (cx, cy) == self._goal:
                return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < WIDTH and 0 <= ny < HEIGHT
                        and not self._grid[ny][nx]
                        and (nx, ny) not in seen):
                    seen.add((nx, ny))
                    q.append((nx, ny))
        return False

    def _step(self) -> None:
        if not self._open:
            self._path = []  # no path (shouldn't happen — guarded by _reachable)
            return
        for _ in range(40):
            if not self._open:
                return
            _, gcur, cur = heapq.heappop(self._open)
            if cur in self._closed:
                continue
            self._closed.add(cur)
            if cur == self._goal:
                # Reconstruct path
                path: list[tuple[int, int]] = []
                node: tuple[int, int] | None = cur
                while node is not None:
                    path.append(node)
                    node = self._came[node]
                path.reverse()
                self._path = path
                return
            cx, cy = cur
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < WIDTH and 0 <= ny < HEIGHT
                        and not self._grid[ny][nx]
                        and (nx, ny) not in self._closed):
                    ng = gcur + 1
                    if ng < self._g.get((nx, ny), 1 << 30):
                        self._g[(nx, ny)] = ng
                        self._came[(nx, ny)] = cur
                        f = ng + _heur((nx, ny), self._goal)
                        heapq.heappush(self._open, (f, ng, (nx, ny)))

    def update(self, dt: float, events) -> None:
        if self._path is None:
            self._step()
            return
        if self._path_idx < len(self._path):
            self._path_idx = min(len(self._path), self._path_idx + 2)
        else:
            self._hold += 1
            if self._hold >= HOLD_FRAMES:
                self._begin()

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if self._grid[y][x]:
                    f.set(x, y, WALL_C)
        for (x, y) in self._closed:
            if (x, y) == self._start or (x, y) == self._goal:
                continue
            f.set(x, y, CLOSED_C)
        for (_, _, (x, y)) in self._open:
            if (x, y) == self._start or (x, y) == self._goal:
                continue
            f.set(x, y, OPEN_C)
        if self._path is not None:
            for (x, y) in self._path[: self._path_idx]:
                if (x, y) != self._start and (x, y) != self._goal:
                    f.set(x, y, PATH_C)
        f.set(*self._start, START_C)
        f.set(*self._goal, GOAL_C)
        return f
