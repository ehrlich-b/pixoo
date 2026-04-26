"""Harmonograph — coupled-pendulum traces; fade, then redraw with new params."""
from __future__ import annotations

import math
import random
from collections import deque

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


PHASE_T = 14.0
TRAIL_LEN = 600
STEPS_PER_FRAME = 8
DT = 0.04
DECAY = 0.012


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


class Harmonograph(Program):
    DESCRIPTION = "Harmonograph — coupled pendulums trace patterns, then reseed"

    def setup(self) -> None:
        self._t = 0.0
        self._phase_t = 0.0
        self._reseed()
        self._trail: deque[tuple[int, int, float]] = deque(maxlen=TRAIL_LEN)

    def _reseed(self) -> None:
        # Two pendulum components per axis with slight detuning so beats emerge.
        def comp() -> tuple[float, float, float]:
            f = random.uniform(0.7, 2.4)
            phi = random.uniform(0, 2 * math.pi)
            a = random.uniform(0.65, 1.0)
            return f, phi, a
        self._cx = (comp(), comp())
        self._cy = (comp(), comp())
        self._t = 0.0
        if hasattr(self, '_trail'):
            self._trail.clear()
        self._hue_base = random.random()

    def update(self, dt: float, events) -> None:
        self._phase_t += dt
        if self._phase_t > PHASE_T:
            self._phase_t = 0.0
            self._reseed()
        scale_x = WIDTH / 2 - 4
        scale_y = HEIGHT / 2 - 4
        cx0 = WIDTH / 2
        cy0 = HEIGHT / 2
        for _ in range(STEPS_PER_FRAME):
            self._t += DT
            damp = math.exp(-DECAY * self._t)
            x = damp * sum(c[2] * math.sin(c[0] * self._t + c[1])
                           for c in self._cx)
            y = damp * sum(c[2] * math.sin(c[0] * self._t + c[1])
                           for c in self._cy)
            xi = int(round(cx0 + x * scale_x * 0.46))
            yi = int(round(cy0 + y * scale_y * 0.46))
            self._trail.append((xi, yi, self._t))

    def render(self) -> Frame:
        f = Frame.black()
        for xi, yi, t in self._trail:
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                hue = (self._hue_base + t * 0.04) % 1.0
                col = _hsv(hue, 0.78, 0.95)
                f.set(xi, yi, col)
        return f
