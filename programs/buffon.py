"""Buffon's needle — drop needles, color by line crossing, count π estimate."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


LINE_SPACING = 8
NEEDLE_LEN = 8
LINE_COLOR = (45, 50, 70)
HIT_COLOR = (255, 230, 110)
MISS_COLOR = (110, 200, 240)
PROGRESS_COLOR = (90, 220, 130)
NEEDLES_PER_FRAME = 4
DISPLAY_LIMIT = 220


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


class Buffon(Program):
    DESCRIPTION = "Buffon's needle — π estimate emerges as needles drop"

    def setup(self) -> None:
        self._needles: list[tuple[int, int, int, int, bool]] = []
        self._hits = 0
        self._total = 0

    def update(self, dt: float, events) -> None:
        for _ in range(NEEDLES_PER_FRAME):
            cx = random.uniform(2, WIDTH - 2)
            cy = random.uniform(2, HEIGHT - 2)
            angle = random.uniform(0, math.pi)
            x0 = cx - NEEDLE_LEN / 2 * math.cos(angle)
            y0 = cy - NEEDLE_LEN / 2 * math.sin(angle)
            x1 = cx + NEEDLE_LEN / 2 * math.cos(angle)
            y1 = cy + NEEDLE_LEN / 2 * math.sin(angle)
            l0 = int(y0) // LINE_SPACING
            l1 = int(y1) // LINE_SPACING
            crossed = l0 != l1
            self._needles.append((int(x0), int(y0), int(x1), int(y1), crossed))
            if len(self._needles) > DISPLAY_LIMIT:
                self._needles.pop(0)
            self._total += 1
            if crossed:
                self._hits += 1

    def render(self) -> Frame:
        f = Frame.black()
        # Floorboards.
        for y in range(0, HEIGHT, LINE_SPACING):
            for x in range(WIDTH):
                f.set(x, y, LINE_COLOR)
        # Drawn needles.
        for x0, y0, x1, y1, crossed in self._needles:
            _line(f, x0, y0, x1, y1, HIT_COLOR if crossed else MISS_COLOR)
        # Top-row progress bar showing ratio of π estimate vs true π.
        # estimate = 2 * total / hits (for needle_len == line_spacing)
        if self._hits > 0:
            est = 2.0 * self._total / self._hits
            err = abs(est - math.pi) / math.pi
            bar = max(0, min(WIDTH, int(WIDTH * (1.0 - min(1.0, err * 4)))))
            for x in range(bar):
                f.set(x, 0, PROGRESS_COLOR)
        return f
