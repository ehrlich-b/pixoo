"""Spring mesh — pinned 12x12 cloth grid jiggles under gravity and wind."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


GRID_W = 11
GRID_H = 11
SPACING = 4.5
GRAVITY = 130.0
DAMP = 0.93
RELAX_ITERS = 16
WIND_MAG = 0.18    # px/s² peak-to-peak — barely visible flutter


def _line(f: Frame, x0: int, y0: int, x1: int, y1: int,
          color: tuple[int, int, int]) -> None:
    dx = abs(x1 - x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0); sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        if 0 <= x0 < WIDTH and 0 <= y0 < HEIGHT:
            f.set(x0, y0, color)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy


class SpringMesh(Program):
    DESCRIPTION = "Spring mesh — pinned cloth grid jiggles under gravity"

    def setup(self) -> None:
        ox = (WIDTH - (GRID_W - 1) * SPACING) / 2
        oy = 4
        self._nodes: list[list[list[float]]] = []
        for j in range(GRID_H):
            row = []
            for i in range(GRID_W):
                x = ox + i * SPACING
                y = oy + j * SPACING
                row.append([x, y, x, y])
            self._nodes.append(row)
        self._pin: set[tuple[int, int]] = {(0, 0), (GRID_W - 1, 0),
                                           (GRID_W // 2, 0)}
        self._wind_t = 0.0

    def update(self, dt: float, events) -> None:
        self._wind_t += dt
        wind_a = (math.sin(self._wind_t * 0.6)
                  + 0.4 * math.sin(self._wind_t * 1.9)) * WIND_MAG
        for j in range(GRID_H):
            for i in range(GRID_W):
                if (i, j) in self._pin:
                    continue
                n = self._nodes[j][i]
                vx = (n[0] - n[2]) * DAMP
                vy = (n[1] - n[3]) * DAMP
                n[2] = n[0]; n[3] = n[1]
                n[0] += vx + wind_a * dt
                n[1] += vy + GRAVITY * dt * dt
        for _ in range(RELAX_ITERS):
            for j in range(GRID_H):
                for i in range(GRID_W):
                    if i < GRID_W - 1:
                        self._relax(i, j, i + 1, j)
                    if j < GRID_H - 1:
                        self._relax(i, j, i, j + 1)

    def _relax(self, i0: int, j0: int, i1: int, j1: int) -> None:
        a = self._nodes[j0][i0]
        b = self._nodes[j1][i1]
        dx = b[0] - a[0]; dy = b[1] - a[1]
        d = math.hypot(dx, dy)
        if d == 0:
            return
        diff = (d - SPACING) / d * 0.5
        if (i0, j0) not in self._pin:
            a[0] += dx * diff; a[1] += dy * diff
        if (i1, j1) not in self._pin:
            b[0] -= dx * diff; b[1] -= dy * diff

    def render(self) -> Frame:
        f = Frame.black()
        for j in range(GRID_H):
            for i in range(GRID_W):
                a = self._nodes[j][i]
                ax = int(round(a[0])); ay = int(round(a[1]))
                if i < GRID_W - 1:
                    b = self._nodes[j][i + 1]
                    _line(f, ax, ay, int(round(b[0])), int(round(b[1])),
                          (90, 160, 220))
                if j < GRID_H - 1:
                    b = self._nodes[j + 1][i]
                    _line(f, ax, ay, int(round(b[0])), int(round(b[1])),
                          (110, 180, 230))
        for (i, j) in self._pin:
            a = self._nodes[j][i]
            f.set(int(round(a[0])), int(round(a[1])), (255, 200, 100))
        return f
