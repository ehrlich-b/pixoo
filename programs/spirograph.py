"""Spirograph — hypotrochoid curves traced as inner circle rolls inside outer."""
from __future__ import annotations

import math
import random
from collections import deque

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


TRAIL_LEN = 600
STEPS_PER_FRAME = 14
DT = 0.04
PHASE_T = 16.0


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


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


class Spirograph(Program):
    DESCRIPTION = "Spirograph — hypotrochoid curves; reseeds R/r each phase"

    def setup(self) -> None:
        self._t = 0.0
        self._phase_t = 0.0
        self._trail: deque[tuple[int, int, float]] = deque(maxlen=TRAIL_LEN)
        self._reseed()

    def _reseed(self) -> None:
        # Pick R, r so the curve closes within phase but isn't trivial.
        candidates = [(11, 4), (13, 5), (9, 4), (11, 3), (15, 6), (13, 3),
                      (17, 7), (12, 5), (10, 3), (16, 5)]
        R, r = random.choice(candidates)
        self._R = R
        self._r = r
        # d: pen offset from inner circle center.
        self._d = random.uniform(r * 0.55, r * 1.0)
        # Display scale.
        self._scale = (HEIGHT / 2 - 3) / (R - r + self._d + 0.5)
        self._trail.clear()
        self._t = 0.0
        self._phase_t = 0.0
        self._hue_base = random.random()

    def update(self, dt: float, events) -> None:
        self._phase_t += dt
        if self._phase_t > PHASE_T:
            self._reseed()
            return
        cx = WIDTH / 2
        cy = HEIGHT / 2
        R = self._R
        r = self._r
        d = self._d
        scl = self._scale
        for _ in range(STEPS_PER_FRAME):
            self._t += DT
            # Hypotrochoid equations.
            ang = self._t
            x = (R - r) * math.cos(ang) + d * math.cos((R - r) / r * ang)
            y = (R - r) * math.sin(ang) - d * math.sin((R - r) / r * ang)
            xi = int(round(cx + x * scl))
            yi = int(round(cy + y * scl))
            self._trail.append((xi, yi, self._t))

    def render(self) -> Frame:
        f = Frame.black()
        for xi, yi, t in self._trail:
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                hue = (self._hue_base + t * 0.03) % 1.0
                col = _hsv(hue, 0.82, 0.95)
                cur = f.get(xi, yi)
                f.set(xi, yi, (min(255, cur[0] + col[0] // 2),
                               min(255, cur[1] + col[1] // 2),
                               min(255, cur[2] + col[2] // 2)))
        return f
