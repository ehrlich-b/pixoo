"""Tunnel — texture-mapped corridor with rotation and depth fade."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


TEX_W = 64
TEX_H = 64


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


class Tunnel(Program):
    DESCRIPTION = "Texture-mapped tunnel — depth fade + rotation"

    def setup(self) -> None:
        cx = WIDTH / 2 - 0.5
        cy = HEIGHT / 2 - 0.5
        n = WIDTH * HEIGHT
        self._u_base = [0.0] * n
        self._v_base = [0.0] * n
        self._fade = [0.0] * n
        for y in range(HEIGHT):
            for x in range(WIDTH):
                dx = x - cx
                dy = y - cy
                r = math.sqrt(dx * dx + dy * dy)
                if r < 0.6:
                    r = 0.6
                idx = y * WIDTH + x
                self._u_base[idx] = (math.atan2(dy, dx) / (2 * math.pi)) * TEX_W
                self._v_base[idx] = 28.0 / r
                self._fade[idx] = min(1.0, r / 28.0)
        # Texture: hue rotates by angle (u); depth bands (v) alternate bright/dim.
        self._tex = bytearray(TEX_W * TEX_H)
        for v in range(TEX_H):
            dim_band = (v // 4) & 1
            for u in range(TEX_W):
                hue_lo = (u * 4) & 127  # 0..127 hue index
                self._tex[v * TEX_W + u] = hue_lo + (0 if dim_band else 128)
        # Palette: 0..127 dim, 128..255 bright — same hue cycle in each half.
        self._pal: list[tuple[int, int, int]] = []
        for i in range(256):
            h = ((i & 127) / 128.0) % 1.0
            val = 0.42 if i < 128 else 0.95
            self._pal.append(_hsv(h, 0.85, val))
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        depth_off = self._t * 24.0
        rot_off = self._t * 14.0
        u_base = self._u_base
        v_base = self._v_base
        fade = self._fade
        tex = self._tex
        pal = self._pal
        umask = TEX_W - 1
        vmask = TEX_H - 1
        px = f.pixels
        for y in range(HEIGHT):
            ybase = y * WIDTH
            for x in range(WIDTH):
                idx = ybase + x
                u = int(u_base[idx] + rot_off) & umask
                v = int(v_base[idx] + depth_off) & vmask
                t = tex[v * TEX_W + u]
                fa = fade[idx]
                col = pal[t]
                pi = idx * 3
                px[pi] = int(col[0] * fa)
                px[pi + 1] = int(col[1] * fa)
                px[pi + 2] = int(col[2] * fa)
        return f
