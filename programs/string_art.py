"""String art — N points on a circle, connect each i to int(i*k); k drifts."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_POINTS = 96
RADIUS = 29


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


class StringArt(Program):
    DESCRIPTION = "String art — modular i→i*k connections; k drifts cardioid → nephroid"

    def setup(self) -> None:
        cx = WIDTH / 2
        cy = HEIGHT / 2
        self._pts: list[tuple[int, int]] = []
        for i in range(N_POINTS):
            ang = i / N_POINTS * 2 * math.pi
            self._pts.append((int(round(cx + RADIUS * math.cos(ang))),
                              int(round(cy + RADIUS * math.sin(ang)))))
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        k = 2.0 + 6.0 * (math.sin(self._t * 0.07) * 0.5 + 0.5)  # 2..8 over ~90s
        hue_base = (self._t * 0.04) % 1.0
        for i in range(N_POINTS):
            j = int(i * k) % N_POINTS
            x0, y0 = self._pts[i]
            x1, y1 = self._pts[j]
            hue = (hue_base + i / N_POINTS) % 1.0
            self._line(f, x0, y0, x1, y1, _hsv(hue, 0.78, 0.85))
        # Faint perimeter dots.
        for x, y in self._pts:
            f.set(x, y, (240, 240, 250))
        return f

    def _line(self, f: Frame, x0: int, y0: int, x1: int, y1: int,
              color: tuple[int, int, int]) -> None:
        dx = abs(x1 - x0); sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0); sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < WIDTH and 0 <= y0 < HEIGHT:
                cur = f.get(x0, y0)
                # Additive blend so overlaps brighten.
                f.set(x0, y0, (min(255, cur[0] + color[0] // 3),
                               min(255, cur[1] + color[1] // 3),
                               min(255, cur[2] + color[2] // 3)))
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy: err += dy; x0 += sx
            if e2 <= dx: err += dx; y0 += sy
