"""Cube3D — rotating wireframe cube with depth-shaded edges."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


VERTS = [
    (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
    (-1, -1, 1),  (1, -1, 1),  (1, 1, 1),  (-1, 1, 1),
]
EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 0),     # back face
    (4, 5), (5, 6), (6, 7), (7, 4),     # front face
    (0, 4), (1, 5), (2, 6), (3, 7),     # connectors
]


class Cube3D(Program):
    DESCRIPTION = "Cube3D — rotating wireframe with depth-shaded edges"

    def setup(self) -> None:
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        a = self._t * 0.6
        b = self._t * 0.43
        c = self._t * 0.81
        cs_a, sn_a = math.cos(a), math.sin(a)
        cs_b, sn_b = math.cos(b), math.sin(b)
        cs_c, sn_c = math.cos(c), math.sin(c)
        cam_z = 3.5
        scale = 32.0
        cx = WIDTH / 2
        cy = HEIGHT / 2
        proj: list[tuple[int, int, float]] = []
        for x, y, z in VERTS:
            # Rotate X.
            y2 = y * cs_a - z * sn_a
            z2 = y * sn_a + z * cs_a
            # Rotate Y.
            x2 = x * cs_b + z2 * sn_b
            z3 = -x * sn_b + z2 * cs_b
            # Rotate Z.
            x3 = x2 * cs_c - y2 * sn_c
            y3 = x2 * sn_c + y2 * cs_c
            zc = z3 + cam_z
            if zc < 0.5:
                zc = 0.5
            sx = cx + x3 / zc * scale
            sy = cy + y3 / zc * scale
            proj.append((int(round(sx)), int(round(sy)), zc))
        for i, j in EDGES:
            x0, y0, z0 = proj[i]
            x1, y1, z1 = proj[j]
            depth = (z0 + z1) * 0.5
            # Closer = brighter.
            t = max(0.0, min(1.0, (cam_z + 1.5 - depth) / 3.0))
            r = int(80 + 175 * t)
            g = int(110 + 145 * t)
            b = int(180 + 70 * t)
            self._line(f, x0, y0, x1, y1, (r, g, b))
        return f

    def _line(self, f: Frame, x0: int, y0: int, x1: int, y1: int,
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
