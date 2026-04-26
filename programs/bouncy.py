"""Bouncy — N colored balls under gravity with elastic ball-ball collisions."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_BALLS = 11
GRAVITY = 32.0
WALL_BOUNCE = 0.92
FLOOR_BOUNCE = 0.85
FLOOR_FRICTION = 0.97


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


class Bouncy(Program):
    DESCRIPTION = "Bouncy — N balls under gravity with elastic collisions"

    def setup(self) -> None:
        self._balls: list[list[float]] = []
        for i in range(N_BALLS):
            r = random.choice([2, 2, 3, 3, 4])
            x = random.uniform(r + 1, WIDTH - r - 1)
            y = random.uniform(r + 1, HEIGHT / 2)
            ang = random.uniform(-1.0, 1.0)
            speed = random.uniform(14, 24)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed
            hue = (i / N_BALLS + 0.07) % 1.0
            col = _hsv(hue, 0.82, 0.96)
            self._balls.append([x, y, vx, vy, float(r), col[0], col[1], col[2]])

    def update(self, dt: float, events) -> None:
        for b in self._balls:
            b[3] += GRAVITY * dt
            b[0] += b[2] * dt
            b[1] += b[3] * dt
            r = b[4]
            if b[0] - r < 0:
                b[0] = r; b[2] = -b[2] * WALL_BOUNCE
            elif b[0] + r >= WIDTH:
                b[0] = WIDTH - 1 - r; b[2] = -b[2] * WALL_BOUNCE
            if b[1] - r < 0:
                b[1] = r; b[3] = -b[3] * WALL_BOUNCE
            elif b[1] + r >= HEIGHT:
                b[1] = HEIGHT - 1 - r
                b[3] = -b[3] * FLOOR_BOUNCE
                b[2] *= FLOOR_FRICTION
        # Ball-ball elastic collisions (equal mass).
        n = len(self._balls)
        for i in range(n):
            for j in range(i + 1, n):
                a = self._balls[i]; c = self._balls[j]
                dx = c[0] - a[0]
                dy = c[1] - a[1]
                d2 = dx * dx + dy * dy
                rsum = a[4] + c[4]
                if d2 == 0 or d2 >= rsum * rsum:
                    continue
                d = math.sqrt(d2)
                nx = dx / d; ny = dy / d
                overlap = (rsum - d) * 0.5
                a[0] -= nx * overlap; a[1] -= ny * overlap
                c[0] += nx * overlap; c[1] += ny * overlap
                rvx = c[2] - a[2]
                rvy = c[3] - a[3]
                impulse = rvx * nx + rvy * ny
                if impulse >= 0:
                    continue
                jval = -1.92 * impulse / 2
                a[2] -= jval * nx; a[3] -= jval * ny
                c[2] += jval * nx; c[3] += jval * ny
        # Re-energize lazy balls.
        for b in self._balls:
            speed = math.hypot(b[2], b[3])
            if speed < 4:
                ang = random.uniform(-math.pi, math.pi)
                b[2] += math.cos(ang) * 8
                b[3] -= 14

    def render(self) -> Frame:
        f = Frame.black()
        # Floor + walls hint.
        for x in range(WIDTH):
            f.set(x, HEIGHT - 1, (60, 55, 60))
        for b in self._balls:
            x = int(round(b[0])); y = int(round(b[1]))
            r = int(b[4])
            col = (int(b[5]), int(b[6]), int(b[7]))
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r:
                        xi = x + dx; yi = y + dy
                        if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                            f.set(xi, yi, col)
            # Highlight pixel for shape definition.
            xi = x - max(1, r // 2); yi = y - max(1, r // 2)
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                f.set(xi, yi, (min(255, col[0] + 80),
                              min(255, col[1] + 80),
                              min(255, col[2] + 80)))
        return f
