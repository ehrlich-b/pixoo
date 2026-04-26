"""Galton board — beads fall through pegs, pile Gaussian in bottom bins.

Params:
  rate=FLOAT     beads spawned per second (default 8)
  max_beads=INT  live beads capped at this (default 40)
"""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

# Layout — everything in pixels.
TOP_Y = 4              # bead spawn row
PEG_START_Y = 10       # first peg row y
PEG_ROWS = 10          # number of peg rows
PEG_DY = 4             # vertical spacing between peg rows
PEG_DX = 4             # horizontal spacing between pegs in a row
BIN_TOP_Y = 52         # top of the collection bins
BIN_FLOOR_Y = 62       # bottom of the display we'll stack into

GRAVITY = 220.0        # px/s²  (sim-time; time-scaled at update())
TIME_SCALE = 0.7

# A bead is basically a 2x2 blob. Peg bounce is a binary left/right choice
# with a tiny velocity kick — full physics is overkill at 64px wide.
PEG_HIT_RADIUS = 1.3


def _blend(f: Frame, x: int, y: int, rgb, w: float) -> None:
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        return
    if w <= 0:
        return
    if w > 1.0:
        w = 1.0
    i = (y * WIDTH + x) * 3
    px = f.pixels
    r = int(rgb[0] * w); g = int(rgb[1] * w); b = int(rgb[2] * w)
    if r > px[i]: px[i] = r
    if g > px[i + 1]: px[i + 1] = g
    if b > px[i + 2]: px[i + 2] = b


def _plot_aa(f: Frame, fx: float, fy: float, rgb) -> None:
    ix = int(math.floor(fx)); iy = int(math.floor(fy))
    dx = fx - ix; dy = fy - iy
    _blend(f, ix, iy, rgb, (1 - dx) * (1 - dy))
    _blend(f, ix + 1, iy, rgb, dx * (1 - dy))
    _blend(f, ix, iy + 1, rgb, (1 - dx) * dy)
    _blend(f, ix + 1, iy + 1, rgb, dx * dy)


def _build_pegs() -> list[tuple[float, float]]:
    """Triangular peg grid, row i has i+1 pegs centered on WIDTH/2."""
    pegs = []
    cx = (WIDTH - 1) / 2
    for row in range(PEG_ROWS):
        y = PEG_START_Y + row * PEG_DY
        for col in range(row + 1):
            x = cx + (col - row / 2) * PEG_DX
            pegs.append((x, y))
    return pegs


PEGS = _build_pegs()
NUM_BINS = PEG_ROWS + 1
BIN_WIDTH = PEG_DX  # each bin catches beads from a fall column


class Galton(Program):
    DESCRIPTION = "Galton board — beads bounce through pegs into Gaussian pile"

    def setup(self) -> None:
        self.rate = float(self.params.get("rate", 8.0))
        self.max_beads = int(self.params.get("max_beads", 40))
        # Each live bead: [x, y, vx, vy]
        self.beads: list[list[float]] = []
        # Current pile column heights (in beads, not pixels).
        self.bins = [0] * NUM_BINS
        self._spawn_accum = 0.0
        self._total_dropped = 0

    def _spawn(self) -> None:
        cx = (WIDTH - 1) / 2
        # Tiny horizontal jitter so beads don't all enter the same peg.
        self.beads.append([cx + random.uniform(-0.4, 0.4), TOP_Y, 0.0, 0.0])

    def _bin_index(self, x: float) -> int:
        cx = (WIDTH - 1) / 2
        # Bin 0 is leftmost. Distance from leftmost peg column.
        leftmost_x = cx - (PEG_ROWS / 2) * PEG_DX
        idx = int(round((x - leftmost_x) / BIN_WIDTH))
        return max(0, min(NUM_BINS - 1, idx))

    def _bin_floor_y(self, idx: int) -> int:
        # Stack beads upward from floor. Each bead is 1 pixel tall.
        return BIN_FLOOR_Y - self.bins[idx]

    def _reset_if_full(self) -> None:
        # When any bin reaches the top of the bin area, clear and restart.
        if any(b >= (BIN_FLOOR_Y - BIN_TOP_Y) for b in self.bins):
            self.bins = [0] * NUM_BINS
            self.beads = []
            self._total_dropped = 0

    def update(self, dt: float, events) -> None:
        scaled = min(dt, 0.1) * TIME_SCALE

        # Spawn.
        self._spawn_accum += scaled * self.rate
        while self._spawn_accum >= 1.0 and len(self.beads) < self.max_beads:
            self._spawn()
            self._spawn_accum -= 1.0
            self._total_dropped += 1

        # Step beads. A bead is done when y reaches its bin's current floor.
        surviving = []
        for b in self.beads:
            b[3] += GRAVITY * scaled
            b[0] += b[2] * scaled
            b[1] += b[3] * scaled

            # Damp horizontal velocity — beads shouldn't slide forever.
            b[2] *= 0.92

            # Peg collision: if within radius of any peg, kick sideways and
            # nudge below so we don't re-trigger next tick.
            for (px, py) in PEGS:
                dx = b[0] - px; dy = b[1] - py
                if dx * dx + dy * dy < PEG_HIT_RADIUS * PEG_HIT_RADIUS:
                    # Random left/right with small bias for slightly offset hits.
                    bias = 0.5 + 0.3 * (1 if dx > 0 else -1)
                    direction = -1 if random.random() > bias else 1
                    b[2] = direction * 8.0 + random.uniform(-1.0, 1.0)
                    b[3] = max(b[3] * 0.5, 4.0)   # preserve some downward vel
                    b[1] = py + PEG_HIT_RADIUS + 0.5
                    break

            # Keep in horizontal bounds (reflect off walls, weak).
            if b[0] < 1:
                b[0] = 1; b[2] = abs(b[2]) * 0.5
            elif b[0] > WIDTH - 2:
                b[0] = WIDTH - 2; b[2] = -abs(b[2]) * 0.5

            # Did we reach the collection zone?
            if b[1] >= BIN_TOP_Y:
                idx = self._bin_index(b[0])
                floor_y = self._bin_floor_y(idx)
                if b[1] >= floor_y:
                    self.bins[idx] += 1
                    continue  # bead absorbed
            surviving.append(b)
        self.beads = surviving
        self._reset_if_full()

    def render(self) -> Frame:
        f = Frame.black()

        # Funnel walls — two diagonals from the top hopper to the peg field.
        cx = (WIDTH - 1) / 2
        wall = (50, 50, 60)
        for y in range(TOP_Y, PEG_START_Y):
            span = (y - TOP_Y) + 2
            _blend(f, int(cx - span), y, wall, 1.0)
            _blend(f, int(cx + span), y, wall, 1.0)

        # Pegs — dim grey dots.
        peg_rgb = (120, 120, 140)
        for (px, py) in PEGS:
            _plot_aa(f, px, py, peg_rgb)

        # Bin dividers — short vertical lines between columns, dim.
        divider = (40, 40, 50)
        leftmost_x = cx - (NUM_BINS / 2) * BIN_WIDTH
        for i in range(NUM_BINS + 1):
            x = int(round(leftmost_x + i * BIN_WIDTH))
            for y in range(BIN_TOP_Y - 1, BIN_FLOOR_Y + 1):
                _blend(f, x, y, divider, 1.0)

        # Piles — warm gradient from bottom (deep red) to top (yellow)
        # so taller stacks read as "hotter" bins.
        for i, count in enumerate(self.bins):
            if count == 0:
                continue
            col_x = int(round(leftmost_x + i * BIN_WIDTH + BIN_WIDTH / 2))
            for h in range(count):
                y = BIN_FLOOR_Y - h
                # height ratio 0..1 → red→orange→yellow
                t = h / max(1, (BIN_FLOOR_Y - BIN_TOP_Y))
                r = 200 + int(55 * t)
                g = int(80 + 140 * t)
                bl = int(30 + 40 * t)
                _blend(f, col_x, y, (r, g, bl), 1.0)
                # Widen the pile so stacks are visible against the 4px bin.
                _blend(f, col_x - 1, y, (r * 3 // 5, g * 3 // 5, bl * 3 // 5), 1.0)
                _blend(f, col_x + 1, y, (r * 3 // 5, g * 3 // 5, bl * 3 // 5), 1.0)

        # Live beads — bright white, slight motion-blur via aa.
        for (bx, by, _, _) in self.beads:
            _plot_aa(f, bx, by, (255, 255, 255))
            _plot_aa(f, bx, by - 0.4, (140, 140, 180))  # faint tail
        return f
