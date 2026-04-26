"""Galaxy — slowly rotating spiral arms with thousands of pixel-stars."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_STARS = 280
ARMS = 3
ARM_SPREAD = 0.45


class Galaxy(Program):
    DESCRIPTION = "Galaxy — slowly rotating 3-arm spiral of stars"

    def setup(self) -> None:
        self._t = 0.0
        rng = random.Random(0)
        self._stars: list[tuple[float, float, float]] = []
        for _ in range(N_STARS):
            # Bias r toward small values so the bulge is dense.
            r = rng.uniform(0.0, 1.0) ** 1.6 * 30.0 + 1.0
            arm = rng.randint(0, ARMS - 1)
            base_a = arm * 2 * math.pi / ARMS + rng.uniform(-ARM_SPREAD, ARM_SPREAD)
            brt = rng.uniform(0.55, 1.0)
            self._stars.append((r, base_a, brt))

    def update(self, dt: float, events) -> None:
        self._t += dt

    def render(self) -> Frame:
        f = Frame.black()
        cx = WIDTH / 2 - 0.5
        cy = HEIGHT / 2 - 0.5
        # Bright bulge.
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                d = dx * dx + dy * dy
                if d <= 9:
                    s = 1.0 - d / 9.0
                    r = int(255 * s + 25)
                    g = int(220 * s + 30)
                    b = int(120 * s + 40)
                    f.set(int(cx) + dx, int(cy) + dy, (min(255, r), min(255, g), min(255, b)))
        # Stars on a logarithmic spiral; angular velocity decreases with r.
        for r, base_a, brt in self._stars:
            spiral = 0.55 * math.log(r + 0.6)
            rot_speed = 0.55 / (1 + r * 0.04)
            ang = base_a + spiral + self._t * rot_speed
            x = cx + r * math.cos(ang)
            y = cy + r * math.sin(ang)
            xi = int(round(x)); yi = int(round(y))
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                t = min(1.0, r / 30.0)
                rc = int((230 - 30 * t) * brt)
                gc = int((215 - 50 * t) * brt)
                bc = int((180 + 70 * t) * brt)
                cur = f.get(xi, yi)
                f.set(xi, yi, (max(cur[0], rc), max(cur[1], gc), max(cur[2], bc)))
        return f
