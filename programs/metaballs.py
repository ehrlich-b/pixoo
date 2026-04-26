"""Metaballs — three drifting circles summed by inverse-square field."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_BALLS = 4
THRESHOLD = 1.0


def _ball_init(rng_seed: int) -> list[list[float]]:
    import random
    r = random.Random(rng_seed)
    out: list[list[float]] = []
    for _ in range(N_BALLS):
        out.append([
            r.uniform(10, WIDTH - 10), r.uniform(10, HEIGHT - 10),
            r.uniform(-12, 12), r.uniform(-12, 12),
            r.uniform(60.0, 120.0),
        ])
    return out


class Metaballs(Program):
    DESCRIPTION = "Metaballs — drifting blobs join into amoeba shapes"

    def setup(self) -> None:
        self._balls = _ball_init(0xBA11)
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt
        for b in self._balls:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            if b[0] < 4: b[0] = 4; b[2] = abs(b[2])
            if b[0] > WIDTH - 5: b[0] = WIDTH - 5; b[2] = -abs(b[2])
            if b[1] < 4: b[1] = 4; b[3] = abs(b[3])
            if b[1] > HEIGHT - 5: b[1] = HEIGHT - 5; b[3] = -abs(b[3])

    def render(self) -> Frame:
        f = Frame.black()
        balls = self._balls
        # Pre-extract for speed
        bx = [b[0] for b in balls]
        by = [b[1] for b in balls]
        bw = [b[4] for b in balls]
        for y in range(HEIGHT):
            for x in range(WIDTH):
                v = 0.0
                for i in range(N_BALLS):
                    dx = x - bx[i]
                    dy = y - by[i]
                    d2 = dx * dx + dy * dy + 1.0
                    v += bw[i] / d2
                if v < 0.4:
                    continue
                if v < THRESHOLD:
                    # Outer rim — dim cyan glow.
                    g = int((v - 0.4) * 200)
                    f.set(x, y, (10, g, g + 30))
                else:
                    # Inside — bright body, hue shifts with magnitude.
                    s = min(1.0, (v - THRESHOLD) * 0.6)
                    r8 = int(80 + 170 * s)
                    g8 = int(180 + 60 * s)
                    b8 = int(240 - 80 * s)
                    f.set(x, y, (r8, g8, b8))
        return f
