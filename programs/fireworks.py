"""Fireworks — rockets ascend, burst into colored particle showers."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


GRAVITY = 28.0
PARTICLE_COUNT = 42
PARTICLE_SPEED = 22.0
PARTICLE_FADE = 0.85
TRAIL_FADE = 0.78


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


class Fireworks(Program):
    DESCRIPTION = "Fireworks — rockets ascend and burst into showers"

    def setup(self) -> None:
        self._rockets: list[list[float]] = []
        self._sparks: list[list[float]] = []
        self._spawn_dt = 0.0
        self._buf = [[(0, 0, 0)] * WIDTH for _ in range(HEIGHT)]

    def _add_rocket(self) -> None:
        x = random.uniform(8, WIDTH - 8)
        target_y = random.uniform(8, 28)
        # Time of flight ~ 0.9s; vy0 chosen so rocket peaks near target_y.
        flight = random.uniform(0.85, 1.15)
        vy = -((HEIGHT - target_y) / flight + GRAVITY * flight / 2)
        hue = random.random()
        self._rockets.append([x, HEIGHT - 1, 0.0, vy, hue, target_y])

    def _burst(self, x: float, y: float, hue: float) -> None:
        for i in range(PARTICLE_COUNT):
            ang = i / PARTICLE_COUNT * 2 * math.pi + random.uniform(-0.05, 0.05)
            speed = PARTICLE_SPEED * random.uniform(0.55, 1.0)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            life = random.uniform(1.4, 2.2)
            ph = (hue + random.uniform(-0.06, 0.06)) % 1.0
            self._sparks.append([x, y, vx, vy, life, ph])

    def update(self, dt: float, events) -> None:
        self._spawn_dt -= dt
        if self._spawn_dt <= 0:
            self._spawn_dt = random.uniform(0.35, 1.1)
            self._add_rocket()
        for r in self._rockets:
            r[0] += r[2] * dt
            r[1] += r[3] * dt
            r[3] += GRAVITY * dt
        # Burst when peak reached or descent starts.
        bursting: list[list[float]] = []
        for r in list(self._rockets):
            if r[3] >= 0 or r[1] <= r[5]:
                bursting.append(r)
                self._rockets.remove(r)
        for r in bursting:
            self._burst(r[0], r[1], r[4])
        for s in self._sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += GRAVITY * dt * 0.7
            s[2] *= 0.985
            s[4] -= dt
        self._sparks = [s for s in self._sparks if s[4] > 0
                        and 0 <= s[0] < WIDTH and s[1] < HEIGHT]
        # Fade backbuffer for trail effect.
        for y in range(HEIGHT):
            row = self._buf[y]
            for x in range(WIDTH):
                r, g, b = row[x]
                row[x] = (int(r * TRAIL_FADE), int(g * TRAIL_FADE),
                          int(b * TRAIL_FADE))

    def render(self) -> Frame:
        f = Frame.black()
        # Rockets: bright trail.
        for r in self._rockets:
            xi = int(r[0]); yi = int(r[1])
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                self._buf[yi][xi] = (255, 240, 180)
        # Sparks: colored.
        for s in self._sparks:
            xi = int(s[0]); yi = int(s[1])
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                bright = max(0.0, min(1.0, s[4] / 1.6))
                col = _hsv(s[5], 0.85, bright)
                self._buf[yi][xi] = col
        for y in range(HEIGHT):
            row = self._buf[y]
            for x in range(WIDTH):
                r, g, b = row[x]
                if r or g or b:
                    f.set(x, y, (r, g, b))
        return f
