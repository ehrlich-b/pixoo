"""Magnet pendulum — color each pixel by which of three magnets attracts it."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


MAGNET_COLORS = (
    (255, 90, 110),
    (110, 220, 130),
    (110, 150, 255),
)
GRAVITY_K = 0.5    # restoring spring toward origin
FRICTION = 0.18
MAGNET_K = 0.5
DT = 0.07
MAX_STEPS = 90
EPS = 0.18


def _compute(magnets: list[tuple[float, float]], px: float, py: float) -> tuple[int, float]:
    vx = vy = 0.0
    x, y = px, py
    for step in range(MAX_STEPS):
        # Spring + magnets + friction
        ax = -GRAVITY_K * x - FRICTION * vx
        ay = -GRAVITY_K * y - FRICTION * vy
        for mx, my in magnets:
            dx = mx - x
            dy = my - y
            d2 = dx * dx + dy * dy + 0.18
            inv = 1.0 / d2
            ax += MAGNET_K * dx * inv
            ay += MAGNET_K * dy * inv
        vx += ax * DT
        vy += ay * DT
        x += vx * DT
        y += vy * DT
        # Snap to nearest magnet?
        for i, (mx, my) in enumerate(magnets):
            dx = mx - x
            dy = my - y
            if dx * dx + dy * dy < EPS * EPS and vx * vx + vy * vy < 0.06:
                return i, step / MAX_STEPS
    # No convergence — pick nearest magnet.
    best_i = 0
    best_d2 = 1e9
    for i, (mx, my) in enumerate(magnets):
        d2 = (mx - x) ** 2 + (my - y) ** 2
        if d2 < best_d2:
            best_d2 = d2
            best_i = i
    return best_i, 1.0


class MagnetPendulum(Program):
    DESCRIPTION = "Magnet pendulum — basin coloring of which magnet wins"

    def setup(self) -> None:
        self._t = 0.0
        # Three magnets at vertices of an equilateral triangle.
        self._refresh_magnets()
        # Render is computed progressively — `_field[y][x]` holds (basin, fade).
        self._field: list[list[tuple[int, float] | None]] = [
            [None] * WIDTH for _ in range(HEIGHT)
        ]
        self._cur_y = 0
        self._cur_x = 0
        self._cycle_done = False

    def _refresh_magnets(self) -> None:
        # Slight rotation so the basin map shifts every cycle.
        a0 = self._t * 0.4
        r = 0.85
        self._magnets = [
            (r * math.cos(a0), r * math.sin(a0)),
            (r * math.cos(a0 + math.tau / 3), r * math.sin(a0 + math.tau / 3)),
            (r * math.cos(a0 - math.tau / 3), r * math.sin(a0 - math.tau / 3)),
        ]

    def update(self, dt: float, events) -> None:
        self._t += dt
        if self._cycle_done:
            # Hold for a beat then refresh magnets and re-render.
            return
        # Compute up to ~700 pixels per frame (2 rows on a 64-wide panel).
        budget = WIDTH * 2
        magnets = self._magnets
        while budget > 0 and not self._cycle_done:
            scale = 1.5 / (WIDTH / 2)
            wx = (self._cur_x - WIDTH / 2) * scale
            wy = (self._cur_y - HEIGHT / 2) * scale
            self._field[self._cur_y][self._cur_x] = _compute(magnets, wx, wy)
            self._cur_x += 1
            if self._cur_x >= WIDTH:
                self._cur_x = 0
                self._cur_y += 1
                if self._cur_y >= HEIGHT:
                    self._cycle_done = True
                    self._hold = 60
                    return
            budget -= 1
        if self._cycle_done:
            self._hold -= 1
            if self._hold <= 0:
                self._refresh_magnets()
                self._cycle_done = False
                self._cur_x = 0
                self._cur_y = 0

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._field[y]
            for x in range(WIDTH):
                cell = row[x]
                if cell is None:
                    continue
                idx, fade = cell
                col = MAGNET_COLORS[idx]
                k = 1.0 - 0.55 * fade
                f.set(x, y, (int(col[0] * k), int(col[1] * k), int(col[2] * k)))
        return f
