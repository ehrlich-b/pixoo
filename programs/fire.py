"""Doom-style fire effect — bottom row maxed, propagate up with decay + jitter."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

# Doom's 37-entry fire palette. Black at 0, progressing through dark red,
# orange, yellow, to white at index 36.
PALETTE = [
    (7, 7, 7), (31, 7, 7), (47, 15, 7), (71, 15, 7), (87, 23, 7),
    (103, 31, 7), (119, 31, 7), (143, 39, 7), (159, 47, 7), (175, 63, 7),
    (191, 71, 7), (199, 71, 7), (223, 79, 7), (223, 87, 7), (223, 87, 7),
    (215, 95, 7), (215, 95, 7), (215, 103, 15), (207, 111, 15), (207, 119, 15),
    (207, 127, 15), (207, 135, 23), (199, 135, 23), (199, 143, 23),
    (199, 151, 31), (191, 159, 31), (191, 159, 31), (191, 167, 39),
    (191, 167, 39), (191, 175, 47), (183, 175, 47), (183, 183, 47),
    (183, 183, 55), (207, 207, 111), (223, 223, 159), (239, 239, 199),
    (255, 255, 255),
]
MAX_HEAT = len(PALETTE) - 1  # 36


class Fire(Program):
    DESCRIPTION = "classic Doom fire — bottom row ignites, flames lick upward"

    def setup(self) -> None:
        self.heat = bytearray(WIDTH * HEIGHT)
        self._reignite_base()

    def _reignite_base(self) -> None:
        # Flicker the bottom row each frame so the base doesn't look like a
        # solid white bar. Values near MAX_HEAT but jittered.
        bot = (HEIGHT - 1) * WIDTH
        for x in range(WIDTH):
            self.heat[bot + x] = random.randint(MAX_HEAT - 6, MAX_HEAT)

    def update(self, dt: float, events) -> None:
        self._reignite_base()
        h = self.heat
        # propagate bottom → top. Symmetric x-shift, stronger decay so the
        # fire cools out in the upper half instead of reaching the top.
        for y in range(HEIGHT - 1, 0, -1):
            base_below = y * WIDTH
            base_above = (y - 1) * WIDTH
            for x in range(WIDTH):
                shift = random.randint(-1, 1)
                sx = x + shift
                if sx < 0:
                    sx = 0
                elif sx >= WIDTH:
                    sx = WIDTH - 1
                decay = random.randint(0, 2)
                src = h[base_below + sx]
                h[base_above + x] = src - decay if src > decay else 0

    def render(self) -> Frame:
        f = Frame.black()
        h = self.heat
        for y in range(HEIGHT):
            base = y * WIDTH
            for x in range(WIDTH):
                v = h[base + x]
                if v:
                    f.set(x, y, PALETTE[v])
        return f
