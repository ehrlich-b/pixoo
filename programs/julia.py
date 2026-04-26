"""Julia set with drifting c — fractal breathes as c walks a circle."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


MAX_ITER = 56
RADIUS = 1.5
C_RADIUS = 0.7885


def _make_palette() -> tuple[tuple[int, int, int], ...]:
    # Smooth rainbow ramp; "in the set" (i = MAX_ITER) is pure black so the
    # interior reads as a silhouette against the colored escape gradient.
    out = []
    for i in range(MAX_ITER + 1):
        if i == MAX_ITER:
            out.append((0, 0, 0))
            continue
        t = i / (MAX_ITER - 1)
        # 6-band hue ramp: deep purple → blue → teal → green → yellow → red
        h = t * 0.85
        # Quick HSV → RGB
        ii = int(h * 6) % 6
        ff = h * 6 - int(h * 6)
        s, v = 0.9, 1.0
        p = v * (1 - s)
        q = v * (1 - ff * s)
        tt = v * (1 - (1 - ff) * s)
        if ii == 0:   r, g, b = v, tt, p
        elif ii == 1: r, g, b = q, v, p
        elif ii == 2: r, g, b = p, v, tt
        elif ii == 3: r, g, b = p, q, v
        elif ii == 4: r, g, b = tt, p, v
        else:          r, g, b = v, p, q
        out.append((int(r * 255), int(g * 255), int(b * 255)))
    return tuple(out)


_PALETTE = _make_palette()


class Julia(Program):
    DESCRIPTION = "Julia set — drifting c parameter, fractal breathes"

    def setup(self) -> None:
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt * 0.25

    def render(self) -> Frame:
        f = Frame.black()
        cr = C_RADIUS * math.cos(self._t)
        ci = C_RADIUS * math.sin(self._t)
        scale = RADIUS / (WIDTH / 2)
        for py in range(HEIGHT):
            zy0 = (py - HEIGHT / 2) * scale
            for px in range(WIDTH):
                zx = (px - WIDTH / 2) * scale
                zy = zy0
                i = 0
                while i < MAX_ITER and zx * zx + zy * zy < 4.0:
                    zx, zy = zx * zx - zy * zy + cr, 2 * zx * zy + ci
                    i += 1
                f.set(px, py, _PALETTE[i])
        return f
