"""Flow field — particles drift along a slowly-evolving sine field."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_PARTICLES = 110
FADE = 7
SPEED = 18.0


def _hsv_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    if i == 0:   r, g, b = v, t, p
    elif i == 1: r, g, b = q, v, p
    elif i == 2: r, g, b = p, v, t
    elif i == 3: r, g, b = p, q, v
    elif i == 4: r, g, b = t, p, v
    else:         r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


class FlowField(Program):
    DESCRIPTION = "Flow field — particles trace a sine-noise vector field"

    def setup(self) -> None:
        self._t = 0.0
        self._particles: list[list[float]] = [
            [random.uniform(0, WIDTH), random.uniform(0, HEIGHT)]
            for _ in range(N_PARTICLES)
        ]
        self._buf = bytearray(WIDTH * HEIGHT * 3)

    def update(self, dt: float, events) -> None:
        self._t += dt
        t = self._t
        buf = self._buf
        # Fade existing pixels in place.
        for i in range(0, len(buf), 3):
            if buf[i] or buf[i + 1] or buf[i + 2]:
                buf[i] = max(0, buf[i] - FADE)
                buf[i + 1] = max(0, buf[i + 1] - FADE)
                buf[i + 2] = max(0, buf[i + 2] - FADE)
        # Advance particles
        for p in self._particles:
            x, y = p
            a = (math.sin(x * 0.13 + t * 0.4)
                 + math.sin(y * 0.16 + t * 0.5)
                 + math.sin((x + y) * 0.08 + t * 0.25)) * 1.05
            x += math.cos(a) * SPEED * dt
            y += math.sin(a) * SPEED * dt
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                ix = int(x); iy = int(y)
                hue = ((a / math.tau) + 0.5) % 1.0
                r, g, b = _hsv_rgb(hue, 0.85, 1.0)
                idx = (iy * WIDTH + ix) * 3
                buf[idx] = r
                buf[idx + 1] = g
                buf[idx + 2] = b
                p[0] = x; p[1] = y
            else:
                p[0] = random.uniform(0, WIDTH)
                p[1] = random.uniform(0, HEIGHT)

    def render(self) -> Frame:
        f = Frame.black()
        f.pixels[:] = self._buf
        return f
