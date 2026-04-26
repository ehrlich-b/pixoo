"""3D starfield — classic demoscene effect, stars fly out from center."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

NUM_STARS = 220
SPEED = 14.0       # z units per second
Z_MAX = 28.0       # spawn depth — shallower than realistic so motion is visible
Z_MIN = 0.6        # respawn when nearer than this
FOCAL = 40.0       # projection scale — higher = tighter FOV
SPREAD = 48.0      # x/y spawn half-extent
TAIL_Z = 2.0       # "previous frame" z-offset for tails — higher = longer streak

# Star tints — mostly white with scattered blue/yellow/red giants.
TINTS = (
    (255, 255, 255), (255, 255, 255), (255, 255, 255), (255, 255, 255),
    (200, 220, 255),  # blue
    (255, 240, 200),  # yellow
    (255, 200, 180),  # red
)


def _spawn() -> list[float]:
    return [
        random.uniform(-SPREAD, SPREAD),
        random.uniform(-SPREAD, SPREAD),
        random.uniform(Z_MIN, Z_MAX),
    ]


class Starfield(Program):
    DESCRIPTION = "3D starfield — flying forward through space"

    def setup(self) -> None:
        self.stars: list[list[float]] = [_spawn() for _ in range(NUM_STARS)]
        self.tints: list[tuple[int, int, int]] = [random.choice(TINTS) for _ in self.stars]

    def update(self, dt: float, events) -> None:
        dz = SPEED * dt
        for i, s in enumerate(self.stars):
            s[2] -= dz
            if s[2] <= Z_MIN:
                # respawn at far plane
                s[0] = random.uniform(-SPREAD, SPREAD)
                s[1] = random.uniform(-SPREAD, SPREAD)
                s[2] = Z_MAX
                self.tints[i] = random.choice(TINTS)

    def render(self) -> Frame:
        f = Frame.black()
        cx, cy = WIDTH / 2, HEIGHT / 2
        for (x, y, z), tint in zip(self.stars, self.tints):
            sx = x * FOCAL / z + cx
            sy = y * FOCAL / z + cy
            # Stretched "previous position" for a visible streak. Not physically
            # accurate per-frame — just a constant-z lookback that gives ~3 frames
            # of motion blur as a static line.
            pz = z + TAIL_Z
            psx = x * FOCAL / pz + cx
            psy = y * FOCAL / pz + cy
            # Perception floor so far stars stay visible; steep ramp up as z shrinks.
            b = min(1.0, max(0.55, 1.0 - z / 24.0))
            head = (int(tint[0] * b), int(tint[1] * b), int(tint[2] * b))
            tail_b = b * 0.45
            tail = (int(tint[0] * tail_b), int(tint[1] * tail_b), int(tint[2] * tail_b))
            # Bresenham-ish line from (psx,psy) → (sx,sy); tail dim, head bright.
            steps = max(1, int(max(abs(sx - psx), abs(sy - psy))) + 1)
            for i in range(steps):
                t = i / steps  # 0 = tail, 1 = head
                ix = int(psx + (sx - psx) * t)
                iy = int(psy + (sy - psy) * t)
                if 0 <= ix < WIDTH and 0 <= iy < HEIGHT:
                    f.set(ix, iy, tail if t < 0.6 else head)
            # Near stars get a cross so they read as chunky.
            if z < 5.0 and 0 <= int(sx) < WIDTH and 0 <= int(sy) < HEIGHT:
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    f.set(int(sx) + dx, int(sy) + dy, head)
        return f
