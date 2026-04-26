"""Boids — separation/alignment/cohesion flocking with toroidal world."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_BOIDS = 36
SIGHT = 8.0
SIGHT_SQ = SIGHT * SIGHT
SEP_RADIUS = 3.0
SEP_RADIUS_SQ = SEP_RADIUS * SEP_RADIUS
MAX_SPEED = 18.0
MIN_SPEED = 8.0
W_SEP = 0.65
W_ALI = 0.16
W_COH = 0.05


def _wrap(v: float, lim: float) -> float:
    if v < 0: return v + lim
    if v >= lim: return v - lim
    return v


def _toroidal_delta(a: float, b: float, lim: float) -> float:
    d = a - b
    half = lim / 2.0
    if d > half: return d - lim
    if d < -half: return d + lim
    return d


class Boids(Program):
    DESCRIPTION = "Flocking boids — separation, alignment, cohesion"

    def setup(self) -> None:
        random.seed()
        self._boids: list[list[float]] = []
        for _ in range(N_BOIDS):
            a = random.random() * math.tau
            self._boids.append([
                random.uniform(0, WIDTH), random.uniform(0, HEIGHT),
                MAX_SPEED * 0.6 * math.cos(a), MAX_SPEED * 0.6 * math.sin(a),
            ])

    def update(self, dt: float, events) -> None:
        b = self._boids
        n = len(b)
        new_v: list[tuple[float, float]] = [(0.0, 0.0)] * n
        for i in range(n):
            xi, yi, vxi, vyi = b[i]
            sep_x = sep_y = 0.0
            ali_x = ali_y = 0.0
            coh_x = coh_y = 0.0
            cnt = 0
            for j in range(n):
                if i == j:
                    continue
                xj, yj, vxj, vyj = b[j]
                dx = _toroidal_delta(xj, xi, WIDTH)
                dy = _toroidal_delta(yj, yi, HEIGHT)
                d2 = dx * dx + dy * dy
                if d2 > SIGHT_SQ:
                    continue
                cnt += 1
                ali_x += vxj; ali_y += vyj
                coh_x += dx; coh_y += dy
                if d2 < SEP_RADIUS_SQ and d2 > 0:
                    inv = 1.0 / d2
                    sep_x -= dx * inv
                    sep_y -= dy * inv
            if cnt:
                ali_x /= cnt; ali_y /= cnt
                coh_x /= cnt; coh_y /= cnt
            ax = W_SEP * sep_x + W_ALI * (ali_x - vxi) + W_COH * coh_x
            ay = W_SEP * sep_y + W_ALI * (ali_y - vyi) + W_COH * coh_y
            new_v[i] = (vxi + ax, vyi + ay)
        for i in range(n):
            xi, yi, _, _ = b[i]
            vx, vy = new_v[i]
            sp = math.hypot(vx, vy)
            if sp > MAX_SPEED:
                vx *= MAX_SPEED / sp; vy *= MAX_SPEED / sp
            elif sp < MIN_SPEED and sp > 0:
                vx *= MIN_SPEED / sp; vy *= MIN_SPEED / sp
            xi = _wrap(xi + vx * dt, WIDTH)
            yi = _wrap(yi + vy * dt, HEIGHT)
            b[i] = [xi, yi, vx, vy]

    def render(self) -> Frame:
        f = Frame.black()
        for x, y, vx, vy in self._boids:
            ix = int(x) % WIDTH
            iy = int(y) % HEIGHT
            sp = math.hypot(vx, vy) / MAX_SPEED
            r = int(120 + 130 * sp)
            g = int(200 - 60 * sp)
            f.set(ix, iy, (r, g, 240))
            ax = math.atan2(vy, vx)
            tx = (ix - int(round(math.cos(ax) * 1.5))) % WIDTH
            ty = (iy - int(round(math.sin(ax) * 1.5))) % HEIGHT
            f.set(tx, ty, (60, 80, 160))
        return f
