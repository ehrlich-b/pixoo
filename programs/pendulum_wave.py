"""Pendulum wave — array of detuned pendulums create rolling wave patterns."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_PEND = 14
WAVE_PERIOD = 60.0          # full re-sync every 60s
SWINGS_BASE = 50            # pendulum 0 makes 50 swings in WAVE_PERIOD
ANG_MAX = math.pi / 3.2     # max swing angle


def _hsv(h: float, s: float, v: float) -> tuple[int, int, int]:
    h6 = h * 6.0
    i = int(h6) % 6
    f = h6 - int(h6)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    if i == 0: r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else: r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


class PendulumWave(Program):
    DESCRIPTION = "Pendulum wave — detuned pendulums drift in/out of phase"

    def setup(self) -> None:
        spacing = (WIDTH - 4) / (N_PEND - 1)
        self._anchors = [int(round(2 + i * spacing)) for i in range(N_PEND)]
        self._t = 0.0
        self._anchor_y = 1
        self._length = HEIGHT - 6

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        # Anchor bar.
        for x in range(WIDTH):
            f.set(x, 0, (90, 80, 60))
            f.set(x, 1, (140, 120, 90))
        for i, ax in enumerate(self._anchors):
            n_swings = SWINGS_BASE + i
            phase = (self._t / WAVE_PERIOD) * n_swings * 2 * math.pi
            ang = ANG_MAX * math.cos(phase)
            ex = ax + math.sin(ang) * self._length
            ey = self._anchor_y + math.cos(ang) * self._length
            self._line(f, ax, self._anchor_y, int(round(ex)), int(round(ey)),
                       (110, 110, 130))
            # Bob: 3x3 colored disc.
            hue = (i / N_PEND + 0.05) % 1.0
            col = _hsv(hue, 0.85, 0.95)
            ex_i = int(round(ex))
            ey_i = int(round(ey))
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    f.set(ex_i + dx, ey_i + dy, col)
        return f

    def _line(self, f: Frame, x0: int, y0: int, x1: int, y1: int,
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
