"""Rotozoom — rotating, zooming colorful texture."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


TEX_SIZE = 32  # power of two for cheap wrap


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


class Rotozoom(Program):
    DESCRIPTION = "Rotozoom — spinning, zooming colorful texture"

    def setup(self) -> None:
        # Texture: 4 big colored quadrants (16×16 each) with a 4-pixel star ring
        # in the middle so rotation reads clearly.
        self._tex: list[tuple[int, int, int]] = [(0, 0, 0)] * (TEX_SIZE * TEX_SIZE)
        cx = TEX_SIZE / 2 - 0.5
        cy = TEX_SIZE / 2 - 0.5
        for v in range(TEX_SIZE):
            for u in range(TEX_SIZE):
                dx = u - cx
                dy = v - cy
                r = math.hypot(dx, dy)
                # 1-pixel mortar between quadrants.
                if u == TEX_SIZE // 2 or v == TEX_SIZE // 2:
                    self._tex[v * TEX_SIZE + u] = (24, 18, 36)
                    continue
                quad = (1 if u >= TEX_SIZE // 2 else 0) + (2 if v >= TEX_SIZE // 2 else 0)
                hue = (quad / 4.0 + 0.04) % 1.0
                # Center star: 8-spoke wheel within radius 6.
                if r < 6.5:
                    ang = math.atan2(dy, dx)
                    spoke = int((ang / math.pi + 1) * 4) & 7
                    hue = (spoke / 8.0) % 1.0
                    val = 0.95
                elif r < 7.5:
                    val = 0.35  # ring around the star
                    hue = 0.0
                else:
                    # Soft diagonal sub-stripe so the quadrant body isn't flat.
                    val = 0.65 + 0.30 * (((u + v) >> 1) & 1)
                self._tex[v * TEX_SIZE + u] = _hsv(hue, 0.85, val)
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        cx = WIDTH / 2 - 0.5
        cy = HEIGHT / 2 - 0.5
        angle = self._t * 0.45
        zoom = 0.55 + 0.4 * math.sin(self._t * 0.6)
        cs = math.cos(angle) / zoom
        sn = math.sin(angle) / zoom
        ox = self._t * 4.0
        oy = self._t * 3.2
        mask = TEX_SIZE - 1
        tex = self._tex
        px = f.pixels
        for y in range(HEIGHT):
            dy = y - cy
            base_u = -dy * sn + ox
            base_v = dy * cs + oy
            for x in range(WIDTH):
                dx = x - cx
                u = int(base_u + dx * cs) & mask
                v = int(base_v + dx * sn) & mask
                col = tex[v * TEX_SIZE + u]
                pi = (y * WIDTH + x) * 3
                px[pi] = col[0]
                px[pi + 1] = col[1]
                px[pi + 2] = col[2]
        return f
