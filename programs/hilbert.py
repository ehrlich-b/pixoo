"""Hilbert — order-6 Hilbert space-filling curve drawn in rainbow over time."""
from __future__ import annotations

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


ORDER = 6
N_POINTS = 4 ** ORDER  # 4096
GROW_PER_FRAME = 28
HOLD_FRAMES = 70


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


def _d2xy(n: int, d: int) -> tuple[int, int]:
    """Convert 1D distance d on a Hilbert curve of side n to (x, y)."""
    rx = ry = 0
    x = y = 0
    s = 1
    t = d
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


class Hilbert(Program):
    DESCRIPTION = "Hilbert — order-6 space-filling curve drawn in rainbow"

    def setup(self) -> None:
        self._points = [_d2xy(WIDTH, i) for i in range(N_POINTS)]
        self._n = 0
        self._hold = 0

    def update(self, dt: float, events) -> None:
        if self._n >= N_POINTS:
            self._hold += 1
            if self._hold > HOLD_FRAMES:
                self._n = 0
                self._hold = 0
            return
        self._n = min(N_POINTS, self._n + GROW_PER_FRAME)

    def render(self) -> Frame:
        f = Frame.black()
        n = self._n
        for i in range(n):
            x, y = self._points[i]
            hue = (i / N_POINTS) % 1.0
            f.set(x, y, _hsv(hue, 0.85, 0.95))
        # Highlight the leading "pen tip" so the growth is visible.
        if n > 0 and n < N_POINTS:
            x, y = self._points[n - 1]
            f.set(x, y, (255, 255, 255))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                xi = x + dx; yi = y + dy
                if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                    f.set(xi, yi, (220, 220, 240))
        return f
