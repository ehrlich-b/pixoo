"""L-systems — Koch / plant / dragon, drawn segment-by-segment then cycled."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


# Each preset: (axiom, rules, angle_deg, iterations, start_angle, color)
PRESETS = (
    ("plant", "X",
     {"X": "F+[[X]-X]-F[-FX]+X", "F": "FF"}, 25.0, 5, 65.0, (140, 220, 110)),
    ("dragon", "FX",
     {"X": "X+YF+", "Y": "-FX-Y"}, 90.0, 11, 0.0, (240, 170, 90)),
    ("koch-snowflake", "F--F--F",
     {"F": "F+F--F+F"}, 60.0, 4, 0.0, (200, 230, 255)),
    ("sierpinski", "F-G-G",
     {"F": "F-G+F+G-F", "G": "GG"}, 120.0, 5, 0.0, (240, 200, 100)),
)
HOLD_FRAMES = 110     # how many frames to hold each fully-drawn pattern
GROW_PER_FRAME = 28   # segments revealed per frame while drawing


def _expand(axiom: str, rules: dict[str, str], n: int) -> str:
    s = axiom
    for _ in range(n):
        s = "".join(rules.get(c, c) for c in s)
    return s


def _segments(s: str, angle_deg: float, start_angle: float, step: float
              ) -> list[tuple[float, float, float, float]]:
    pts: list[tuple[float, float, float, float]] = []
    x = y = 0.0
    a = math.radians(start_angle)
    da = math.radians(angle_deg)
    stack: list[tuple[float, float, float]] = []
    for c in s:
        if c == "F" or c == "G":
            nx = x + step * math.cos(a)
            ny = y + step * math.sin(a)
            pts.append((x, y, nx, ny))
            x, y = nx, ny
        elif c == "+":
            a += da
        elif c == "-":
            a -= da
        elif c == "[":
            stack.append((x, y, a))
        elif c == "]":
            x, y, a = stack.pop()
    return pts


def _fit(pts: list[tuple[float, float, float, float]]
         ) -> list[tuple[int, int, int, int]]:
    if not pts:
        return []
    xs = [p[0] for p in pts] + [p[2] for p in pts]
    ys = [p[1] for p in pts] + [p[3] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span = max(maxx - minx, maxy - miny, 1e-6)
    margin = 2
    scale = (min(WIDTH, HEIGHT) - 2 * margin) / span
    ox = margin + (WIDTH - 2 * margin - (maxx - minx) * scale) / 2 - minx * scale
    oy = margin + (HEIGHT - 2 * margin - (maxy - miny) * scale) / 2 - miny * scale
    out: list[tuple[int, int, int, int]] = []
    for x0, y0, x1, y1 in pts:
        out.append((int(round(x0 * scale + ox)), int(round(y0 * scale + oy)),
                    int(round(x1 * scale + ox)), int(round(y1 * scale + oy))))
    return out


def _line(f: Frame, x0: int, y0: int, x1: int, y1: int,
          color: tuple[int, int, int]) -> None:
    dx = abs(x1 - x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0); sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        f.set(x0, y0, color)
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy


class LSystem(Program):
    DESCRIPTION = "L-systems — Koch, plant, dragon, Sierpinski"

    def setup(self) -> None:
        self._idx = 0
        self._load(0)

    def _load(self, i: int) -> None:
        name, axiom, rules, ang, iters, start, color = PRESETS[i]
        s = _expand(axiom, rules, iters)
        self._segs = _fit(_segments(s, ang, start, 1.0))
        self._color = color
        self._drawn = 0
        self._hold = 0

    def update(self, dt: float, events) -> None:
        if self._drawn < len(self._segs):
            self._drawn = min(len(self._segs), self._drawn + GROW_PER_FRAME)
        else:
            self._hold += 1
            if self._hold >= HOLD_FRAMES:
                self._idx = (self._idx + 1) % len(PRESETS)
                self._load(self._idx)

    def render(self) -> Frame:
        f = Frame.black()
        for i in range(self._drawn):
            x0, y0, x1, y1 = self._segs[i]
            _line(f, x0, y0, x1, y1, self._color)
        return f
