"""Matrix code rain — green glyph streams cascade with fading trails."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


HEAD = (180, 255, 200)
BRIGHT = (40, 255, 80)
DIM = (10, 120, 30)


class Matrix(Program):
    DESCRIPTION = "Matrix code rain — green glyph streams down the panel"

    def setup(self) -> None:
        # Per-column drop state: (head_y, sub_step, speed_cells_per_sec) or None.
        self._drops: list[tuple[float, float] | None] = [None] * WIDTH
        # Per-pixel brightness 0..255 — we fade each tick.
        self._bri = [bytearray(HEIGHT) for _ in range(WIDTH)]
        self._spawn_acc = 0.0

    def update(self, dt: float, events) -> None:
        for x in range(WIDTH):
            d = self._drops[x]
            if d is None:
                continue
            y, speed = d
            y += speed * dt
            iy = int(y)
            if 0 <= iy < HEIGHT:
                self._bri[x][iy] = 255
            if y > HEIGHT + 6:
                self._drops[x] = None
            else:
                self._drops[x] = (y, speed)
        self._spawn_acc += dt * 7.0
        while self._spawn_acc >= 1.0:
            self._spawn_acc -= 1.0
            x = random.randrange(WIDTH)
            if self._drops[x] is None:
                self._drops[x] = (-1.0, random.uniform(10.0, 26.0))
        # Fade trails.
        fade = max(1, int(dt * 220))
        for x in range(WIDTH):
            col = self._bri[x]
            for y in range(HEIGHT):
                v = col[y]
                if v:
                    col[y] = max(0, v - fade)

    def render(self) -> Frame:
        f = Frame.black()
        for x in range(WIDTH):
            col = self._bri[x]
            d = self._drops[x]
            head_y = int(d[0]) if d is not None else -999
            for y in range(HEIGHT):
                b = col[y]
                if b == 0:
                    continue
                if y == head_y:
                    f.set(x, y, HEAD)
                elif b > 180:
                    f.set(x, y, BRIGHT)
                elif b > 60:
                    s = b
                    f.set(x, y, (s // 8, s, s // 4))
                else:
                    s = b
                    f.set(x, y, (0, s // 2, s // 6))
        return f
