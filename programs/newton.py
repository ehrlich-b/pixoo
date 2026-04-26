"""Newton basins — z^3 - 1 attractor coloring with a drifting offset."""
from __future__ import annotations

import math

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


MAX_ITER = 22
ROOT_COLORS = (
    (255, 95, 110),
    (110, 220, 130),
    (110, 150, 255),
)
SQRT3_2 = math.sqrt(3) / 2


class Newton(Program):
    DESCRIPTION = "Newton basins — z^3-1 with drifting view"

    def setup(self) -> None:
        self._t = 0.0

    def update(self, dt: float, events) -> None:
        self._t += dt * 0.18

    def render(self) -> Frame:
        f = Frame.black()
        # Drift the view: zoom slowly + rotate.
        scale_base = 1.5
        zoom = scale_base * (1.0 + 0.3 * math.sin(self._t * 0.7))
        ca = math.cos(self._t * 0.4)
        sa = math.sin(self._t * 0.4)
        # Three roots of unity for z^3 = 1
        roots = ((1.0, 0.0), (-0.5, SQRT3_2), (-0.5, -SQRT3_2))
        for py in range(HEIGHT):
            yn = (py - HEIGHT / 2) / (HEIGHT / 2) * zoom
            for px in range(WIDTH):
                xn = (px - WIDTH / 2) / (WIDTH / 2) * zoom
                # Rotate the input coords for slow swirl.
                zx = ca * xn - sa * yn
                zy = sa * xn + ca * yn
                hit = -1
                it = 0
                while it < MAX_ITER:
                    # f(z) = z^3 - 1; f'(z) = 3 z^2
                    # z' = z - (z^3 - 1)/(3 z^2)
                    zx2 = zx * zx; zy2 = zy * zy
                    denom = 3.0 * (zx2 * zx2 + 2 * zx2 * zy2 + zy2 * zy2)
                    if denom < 1e-10:
                        break
                    # Numerator: (z^3 - 1) where z^3 = (zx + i zy)^3
                    cube_re = zx * (zx2 - 3 * zy2)
                    cube_im = zy * (3 * zx2 - zy2)
                    num_re = cube_re - 1.0
                    num_im = cube_im
                    # Divide num/(3 z^2)
                    sq_re = zx2 - zy2
                    sq_im = 2.0 * zx * zy
                    # 3 z^2 = (3 sq_re, 3 sq_im); inverse magnitude
                    d2 = 3.0 * (sq_re * sq_re + sq_im * sq_im) * 3.0  # |3z^2|^2 ≠ 9|z^2|^2; redo
                    # easier: use complex math by factoring
                    inv_re = (3 * sq_re) / (9.0 * (sq_re * sq_re + sq_im * sq_im))
                    inv_im = -(3 * sq_im) / (9.0 * (sq_re * sq_re + sq_im * sq_im))
                    # ratio = num * inv
                    rat_re = num_re * inv_re - num_im * inv_im
                    rat_im = num_re * inv_im + num_im * inv_re
                    zx -= rat_re
                    zy -= rat_im
                    # Check convergence
                    for ri, (rr, ri_im) in enumerate(roots):
                        dx = zx - rr
                        dy = zy - ri_im
                        if dx * dx + dy * dy < 1e-3:
                            hit = ri
                            break
                    if hit >= 0:
                        break
                    it += 1
                if hit >= 0:
                    col = ROOT_COLORS[hit]
                    fade = 1.0 - it / MAX_ITER * 0.7
                    f.set(px, py, (int(col[0] * fade),
                                    int(col[1] * fade),
                                    int(col[2] * fade)))
        return f
