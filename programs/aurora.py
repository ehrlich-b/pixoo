"""Aurora — green/magenta curtains shimmer in a night sky."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_CURTAINS = 5
CURTAIN_HALFW = 8.0


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


class Aurora(Program):
    DESCRIPTION = "Aurora — green/magenta curtains shimmer in night sky"

    def setup(self) -> None:
        self._t = 0.0
        self._sky: list[tuple[int, int, int]] = []
        for y in range(HEIGHT):
            t = y / HEIGHT
            shade = 1 - t * 0.55
            r = int(8 * shade)
            g = int(8 * shade)
            b = int(28 * shade + 4)
            self._sky.append((r, g, b))
        # Curtain params: cx, vx, freq_x, freq_t, hue_base
        self._curtains: list[list[float]] = []
        for _ in range(N_CURTAINS):
            self._curtains.append([
                random.uniform(0, WIDTH),
                random.uniform(-2.2, 2.2),
                random.uniform(0.05, 0.11),
                random.uniform(0.4, 1.1),
                random.uniform(0.28, 0.45),
            ])
        # 8 small stars dotted in the sky.
        self._stars = [(random.randint(0, WIDTH - 1),
                        random.randint(0, HEIGHT // 2 - 2)) for _ in range(8)]

    def update(self, dt: float, events) -> None:
        self._t += dt
        for c in self._curtains:
            c[0] += c[1] * dt
            if c[0] < -12:
                c[0] = WIDTH + 4
            elif c[0] > WIDTH + 12:
                c[0] = -4

    def render(self) -> Frame:
        f = Frame.black()
        px = f.pixels
        # Sky
        for y in range(HEIGHT):
            r, g, b = self._sky[y]
            for x in range(WIDTH):
                i = (y * WIDTH + x) * 3
                px[i] = r; px[i + 1] = g; px[i + 2] = b
        # Stars (twinkle).
        twinkle = 0.65 + 0.35 * math.sin(self._t * 2.7)
        for sx, sy in self._stars:
            i = (sy * WIDTH + sx) * 3
            v = int(180 * twinkle)
            px[i] = max(px[i], v); px[i + 1] = max(px[i + 1], v); px[i + 2] = max(px[i + 2], v)
        # Curtains — additive blend.
        sin = math.sin
        for c in self._curtains:
            cx, _vx, fx, ft, hue = c
            for x in range(WIDTH):
                eff = cx + sin(x * fx + self._t * ft) * 9.0
                d = abs(x - eff)
                if d >= CURTAIN_HALFW:
                    continue
                strength = (1 - d / CURTAIN_HALFW) ** 2
                for y in range(HEIGHT):
                    ydim = max(0.0, 1 - y / HEIGHT * 0.85)
                    wave = sin(y * 0.18 - self._t * 1.6 + cx * 0.04) * 0.28 + 0.78
                    s = strength * ydim * wave
                    local_hue = (hue + y / HEIGHT * 0.5) % 1.0
                    cr, cg, cb = _hsv(local_hue, 0.86, s * 0.95)
                    i = (y * WIDTH + x) * 3
                    nr = px[i] + cr
                    ng = px[i + 1] + cg
                    nb = px[i + 2] + cb
                    px[i] = nr if nr < 256 else 255
                    px[i + 1] = ng if ng < 256 else 255
                    px[i + 2] = nb if nb < 256 else 255
        return f
