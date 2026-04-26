"""Tron — two AI light cycles snake until one boxes itself in; reset."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


DIRS = [(0, -1), (1, 0), (0, 1), (-1, 0)]
STEP_HZ = 28
LOOK_AHEAD = 14


class Tron(Program):
    DESCRIPTION = "Tron — two AI light cycles play to the death"

    def setup(self) -> None:
        self._step_dt = 0.0
        self._reset()

    def _reset(self) -> None:
        self._grid = bytearray(WIDTH * HEIGHT)
        self._cycles = [
            {"x": 6, "y": HEIGHT // 2, "dir": 1, "id": 1, "alive": True},
            {"x": WIDTH - 7, "y": HEIGHT // 2, "dir": 3, "id": 2, "alive": True},
        ]
        for c in self._cycles:
            self._grid[c["y"] * WIDTH + c["x"]] = c["id"]
        self._hold = 0.0

    def _dist(self, x: int, y: int, d: int) -> int:
        dx, dy = DIRS[d]
        for k in range(1, LOOK_AHEAD + 1):
            tx = x + dx * k
            ty = y + dy * k
            if tx < 0 or tx >= WIDTH or ty < 0 or ty >= HEIGHT:
                return k - 1
            if self._grid[ty * WIDTH + tx]:
                return k - 1
        return LOOK_AHEAD

    def _choose(self, c) -> int:
        x = c["x"]; y = c["y"]; d = c["dir"]
        options = []
        for new_d in (d, (d + 1) % 4, (d - 1) % 4):
            options.append((self._dist(x, y, new_d), new_d))
        options.sort(reverse=True)
        if len(options) > 1 and random.random() < 0.12 and options[1][0] >= 3:
            return options[1][1]
        return options[0][1]

    def update(self, dt: float, events) -> None:
        if self._hold > 0:
            self._hold -= dt
            if self._hold <= 0:
                self._reset()
            return
        self._step_dt += dt
        if self._step_dt < 1.0 / STEP_HZ:
            return
        self._step_dt = 0
        for c in self._cycles:
            if not c["alive"]:
                continue
            c["dir"] = self._choose(c)
            dx, dy = DIRS[c["dir"]]
            nx = c["x"] + dx
            ny = c["y"] + dy
            if nx < 0 or nx >= WIDTH or ny < 0 or ny >= HEIGHT:
                c["alive"] = False
                continue
            if self._grid[ny * WIDTH + nx]:
                c["alive"] = False
                continue
            c["x"] = nx; c["y"] = ny
            self._grid[ny * WIDTH + nx] = c["id"]
        alive = sum(1 for c in self._cycles if c["alive"])
        if alive <= 1:
            self._hold = 1.6

    def render(self) -> Frame:
        f = Frame.black()
        # Faint border.
        for x in range(WIDTH):
            f.set(x, 0, (40, 40, 50))
            f.set(x, HEIGHT - 1, (40, 40, 50))
        for y in range(HEIGHT):
            f.set(0, y, (40, 40, 50))
            f.set(WIDTH - 1, y, (40, 40, 50))
        # Trails.
        for y in range(HEIGHT):
            for x in range(WIDTH):
                v = self._grid[y * WIDTH + x]
                if v == 1:
                    f.set(x, y, (220, 70, 70))
                elif v == 2:
                    f.set(x, y, (70, 170, 230))
        # Heads (white pulse).
        for c in self._cycles:
            if c["alive"]:
                f.set(c["x"], c["y"], (255, 255, 255))
                # Tiny halo.
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    xi = c["x"] + dx; yi = c["y"] + dy
                    if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                        cur = f.get(xi, yi)
                        f.set(xi, yi, (min(255, cur[0] + 60),
                                       min(255, cur[1] + 60),
                                       min(255, cur[2] + 60)))
        return f
