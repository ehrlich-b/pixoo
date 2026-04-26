"""Heat equation — hotspots diffuse and decay; iron-glow palette."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


DIFFUSION = 0.12
COOLING = 0.012


def _palette() -> tuple[tuple[int, int, int], ...]:
    out = [(0, 0, 0)]
    # Iron palette: black → red → orange → yellow → white
    for i in range(1, 256):
        s = i / 255.0
        if s < 0.25:
            r = int(s * 4 * 255); g = 0; b = 0
        elif s < 0.55:
            r = 255; g = int((s - 0.25) / 0.30 * 200); b = 0
        elif s < 0.85:
            r = 255; g = int(200 + (s - 0.55) / 0.30 * 55); b = int((s - 0.55) / 0.30 * 120)
        else:
            r = 255; g = 255; b = int(120 + (s - 0.85) / 0.15 * 135)
        out.append((min(255, r), min(255, g), min(255, b)))
    return tuple(out)


_PAL = _palette()


class Heat(Program):
    DESCRIPTION = "Heat equation — diffusing hotspots in iron-glow"

    def setup(self) -> None:
        self._t = [[0.0] * WIDTH for _ in range(HEIGHT)]
        self._spawn_t = 0.0

    def update(self, dt: float, events) -> None:
        cur = self._t
        new = [row[:] for row in cur]
        for y in range(1, HEIGHT - 1):
            row = cur[y]
            ur = cur[y - 1]; dr = cur[y + 1]
            new_row = new[y]
            for x in range(1, WIDTH - 1):
                lap = ur[x] + dr[x] + row[x - 1] + row[x + 1] - 4 * row[x]
                v = row[x] + DIFFUSION * lap - COOLING
                new_row[x] = 0.0 if v < 0 else v
        self._t = new
        self._spawn_t -= dt
        if self._spawn_t <= 0:
            self._spawn_t = random.uniform(0.6, 1.6)
            cx = random.randrange(8, WIDTH - 8)
            cy = random.randrange(8, HEIGHT - 8)
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    if dx * dx + dy * dy <= 9:
                        self._t[cy + dy][cx + dx] = 200.0

    def render(self) -> Frame:
        f = Frame.black()
        for y in range(HEIGHT):
            row = self._t[y]
            for x in range(WIDTH):
                v = row[x]
                if v > 0.5:
                    idx = min(255, int(v * 1.4))
                    f.set(x, y, _PAL[idx])
        return f
