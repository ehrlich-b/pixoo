"""IFS — chaos game accumulating Barnsley fern and Sierpinski triangle."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


# Each preset is (name, params, render-color).
# params is either a Barnsley-style transform list OR a list of vertices for
# the random-vertex chaos game. We tag with kind="ifs" or "vertex".
FERN_TRANSFORMS = (
    (0.00, 0.00, 0.00, 0.16, 0.0, 0.00, 0.01),
    (0.85, 0.04, -0.04, 0.85, 0.0, 1.60, 0.85),
    (0.20, -0.26, 0.23, 0.22, 0.0, 1.60, 0.07),
    (-0.15, 0.28, 0.26, 0.24, 0.0, 0.44, 0.07),
)
SIERPINSKI_VERTS = ((0.5, 0.0), (0.0, 1.0), (1.0, 1.0))

PRESETS = (
    ("fern", "ifs", FERN_TRANSFORMS, (-2.5, 2.7, 0.0, 10.5), (60, 220, 90)),
    ("sierpinski", "vertex", SIERPINSKI_VERTS, (0.0, 1.0, 0.0, 1.0), (240, 200, 100)),
)
ITERS_PER_FRAME = 2200
HOLD_FRAMES = 240
RAMP_FRAMES = 60   # accumulate density for this many frames per cycle


class IFS(Program):
    DESCRIPTION = "IFS chaos game — Barnsley fern + Sierpinski triangle"

    def setup(self) -> None:
        self._idx = 0
        self._begin()

    def _begin(self) -> None:
        self._frames = 0
        self._x = 0.0
        self._y = 0.0
        self._counts = [bytearray(WIDTH) for _ in range(HEIGHT)]

    def _iterate_fern(self, n: int) -> None:
        x, y = self._x, self._y
        bounds = PRESETS[0][3]
        minx, maxx, miny, maxy = bounds
        sx = (WIDTH - 2) / (maxx - minx)
        sy = (HEIGHT - 2) / (maxy - miny)
        ox = -minx * sx + 1
        oy = -miny * sy + 1
        for _ in range(n):
            r = random.random()
            cum = 0.0
            a = b = c = d = e = ff = 0.0
            for ta, tb, tc, td, te, tf, tp in FERN_TRANSFORMS:
                cum += tp
                if r < cum:
                    a, b, c, d, e, ff = ta, tb, tc, td, te, tf
                    break
            x, y = a * x + b * y + e, c * x + d * y + ff
            ix = int(x * sx + ox)
            iy = HEIGHT - 1 - int(y * sy + oy)  # flip math-Y to screen-Y
            if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                v = self._counts[iy][ix]
                if v < 255:
                    self._counts[iy][ix] = v + 1
        self._x, self._y = x, y

    def _iterate_vertex(self, n: int) -> None:
        x, y = self._x, self._y
        bounds = PRESETS[self._idx][3]
        minx, maxx, miny, maxy = bounds
        sx = (WIDTH - 2) / (maxx - minx)
        sy = (HEIGHT - 2) / (maxy - miny)
        ox = -minx * sx + 1
        oy = -miny * sy + 1
        verts = PRESETS[self._idx][2]
        for _ in range(n):
            vx, vy = random.choice(verts)
            x = (x + vx) * 0.5
            y = (y + vy) * 0.5
            ix = int(x * sx + ox)
            iy = HEIGHT - 1 - int(y * sy + oy)
            if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                v = self._counts[iy][ix]
                if v < 255:
                    self._counts[iy][ix] = v + 1
        self._x, self._y = x, y

    def update(self, dt: float, events) -> None:
        kind = PRESETS[self._idx][1]
        if self._frames < RAMP_FRAMES:
            if kind == "ifs":
                self._iterate_fern(ITERS_PER_FRAME)
            else:
                self._iterate_vertex(ITERS_PER_FRAME)
        self._frames += 1
        if self._frames > HOLD_FRAMES:
            self._idx = (self._idx + 1) % len(PRESETS)
            self._begin()

    def render(self) -> Frame:
        f = Frame.black()
        col = PRESETS[self._idx][4]
        for y in range(HEIGHT):
            row = self._counts[y]
            for x in range(WIDTH):
                c = row[x]
                if c == 0:
                    continue
                t = min(1.0, c / 12.0)
                r = int(col[0] * (0.4 + 0.6 * t))
                g = int(col[1] * (0.4 + 0.6 * t))
                b = int(col[2] * (0.4 + 0.6 * t))
                f.set(x, y, (r, g, b))
        return f
