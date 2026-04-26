"""Newton's cradle — Verlet + position-based constraints.

Physics are real (positions + rod-length + ball-ball overlap constraints,
Verlet integration). The render is a slow-motion projection of a faster
sim, so momentum-transfer artifacts don't show up at the device's ~5fps.

Params:
  n=INT  number of balls (default 5). Works for n >= 2.
"""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

ROD_LEN = 26.0
BOB_RADIUS = 2.3
PIVOT_Y = 5.0
GRAVITY = 60.0

# Physics runs at 1 kHz — enough iterations for rod constraints + pairwise
# overlap correction to converge cleanly.
SIM_HZ = 1000.0
SIM_DT = 1.0 / SIM_HZ

# Constraint relaxation iterations per physics step.
CONSTRAINT_ITERS = 6

# Per-physics-step linear damping. At SIM_HZ=1000, (1-DAMP)^N decays over
# T seconds. 5e-6 → half-life ≈ 130 s, which pairs with the reset watchdog.
DAMP = 5e-6

# Slow-mo so 5fps device rendering still shows visible motion.
TIME_SCALE = 0.35

KICK_ANGLE = 1.1

RESET_SPEED_FRAC = 0.18
WARMUP_S = 6.0
HARD_CAP_S = 150.0


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


def _line_aa(f: Frame, fx0: float, fy0: float, fx1: float, fy1: float, rgb) -> None:
    dx = fx1 - fx0; dy = fy1 - fy0
    steps = int(max(abs(dx), abs(dy)) * 2) + 2
    for i in range(steps + 1):
        t = i / steps
        _plot_aa(f, fx0 + dx * t, fy0 + dy * t, rgb)


def _blit_disk(f: Frame, fx: float, fy: float, rgb, radius: float) -> None:
    ix = int(math.floor(fx)); iy = int(math.floor(fy))
    r_ceil = int(math.ceil(radius)) + 1
    for oy in range(-r_ceil, r_ceil + 1):
        for ox in range(-r_ceil, r_ceil + 1):
            px = ix + ox; py = iy + oy
            d = math.hypot((px + 0.5) - (fx + 0.5), (py + 0.5) - (fy + 0.5))
            if d >= radius + 0.5:
                continue
            w = 1.0 if d <= radius - 0.5 else (radius + 0.5 - d)
            _blend(f, px, py, rgb, w)


class Cradle(Program):
    DESCRIPTION = "Newton's cradle — Verlet chain, 1/2/3 ball kicks"

    def setup(self) -> None:
        self.n = max(2, int(self.params.get("n", 5)))
        spacing = 2 * BOB_RADIUS
        total = (self.n - 1) * spacing
        x0 = WIDTH / 2.0 - total / 2.0
        self.pivots = [(x0 + i * spacing, PIVOT_Y) for i in range(self.n)]
        self._reset()

    def _reset(self) -> None:
        # Place each ball at its pivot's rest position (angle 0), then raise
        # the chosen kickers to KICK_ANGLE on one side.
        self.pos: list[list[float]] = []
        self.prev: list[list[float]] = []
        # Weight 1-ball kicks more common, then 2, then 3.
        kickers = random.choice((1, 1, 1, 2, 2, 3))
        side = random.choice((-1, 1))
        kick = KICK_ANGLE * side
        for i, (pvx, pvy) in enumerate(self.pivots):
            is_kicker = (i < kickers) if side < 0 else (i >= self.n - kickers)
            theta = kick if is_kicker else 0.0
            x = pvx + ROD_LEN * math.sin(theta)
            y = pvy + ROD_LEN * math.cos(theta)
            self.pos.append([x, y])
            self.prev.append([x, y])  # zero initial velocity
        self._accum = 0.0
        self._elapsed = 0.0
        self._peak_speed = 0.0
        self._flash_time = -1.0
        self._flash_pos: tuple[float, float] | None = None

    # ---- physics ----
    def _step(self, dt: float) -> None:
        # Verlet integration. new_pos = pos + (pos - prev)*(1-damp) + g*dt²
        for i in range(self.n):
            x, y = self.pos[i]
            px, py = self.prev[i]
            vx = (x - px) * (1 - DAMP)
            vy = (y - py) * (1 - DAMP)
            self.prev[i] = [x, y]
            self.pos[i] = [x + vx, y + vy + GRAVITY * dt * dt]

        # Rod constraint — project onto circle of radius ROD_LEN around pivot.
        # Iterated a few times for convergence.
        for _ in range(CONSTRAINT_ITERS):
            for i in range(self.n):
                pvx, pvy = self.pivots[i]
                dx = self.pos[i][0] - pvx
                dy = self.pos[i][1] - pvy
                d = math.hypot(dx, dy)
                if d == 0:
                    continue
                k = ROD_LEN / d
                self.pos[i][0] = pvx + dx * k
                self.pos[i][1] = pvy + dy * k

        # Collision resolution: for each overlapping adjacent pair, swap the
        # normal component of their Verlet velocities (via prev-pos adjust)
        # AND push them apart. This gives instantaneous 1D elastic collision
        # on the contact axis — correct cradle momentum propagation.
        for i in range(self.n - 1):
            ax, ay = self.pos[i]
            bx, by = self.pos[i + 1]
            dx = bx - ax; dy = by - ay
            d = math.hypot(dx, dy)
            if d == 0 or d >= 2 * BOB_RADIUS:
                continue
            nx, ny = dx / d, dy / d
            vax = ax - self.prev[i][0]; vay = ay - self.prev[i][1]
            vbx = bx - self.prev[i + 1][0]; vby = by - self.prev[i + 1][1]
            van = vax * nx + vay * ny
            vbn = vbx * nx + vby * ny
            if van - vbn > 0:  # only swap if approaching
                dva = vbn - van
                dvb = van - vbn
                # v = pos - prev; to change v by dv without moving pos, subtract
                # dv from prev (along the normal).
                self.prev[i][0] -= dva * nx
                self.prev[i][1] -= dva * ny
                self.prev[i + 1][0] -= dvb * nx
                self.prev[i + 1][1] -= dvb * ny
                self._flash_pos = ((ax + bx) / 2, (ay + by) / 2)
                self._flash_time = self._elapsed
            # De-overlap regardless of approach, so resting contacts stay non-
            # penetrating through rounding drift.
            overlap = 2 * BOB_RADIUS - d
            self.pos[i][0] -= nx * overlap / 2
            self.pos[i][1] -= ny * overlap / 2
            self.pos[i + 1][0] += nx * overlap / 2
            self.pos[i + 1][1] += ny * overlap / 2

    def update(self, dt: float, events) -> None:
        scaled = min(dt, 0.5) * TIME_SCALE
        self._accum += scaled
        while self._accum >= SIM_DT:
            self._step(SIM_DT)
            self._accum -= SIM_DT

        self._elapsed += scaled

        # Track total speed (sum of |pos - prev|) to drive the reset watchdog.
        speed = 0.0
        for p, q in zip(self.pos, self.prev):
            speed += math.hypot(p[0] - q[0], p[1] - q[1])
        if speed > self._peak_speed:
            self._peak_speed = speed

        if (self._elapsed >= WARMUP_S
                and speed < self._peak_speed * RESET_SPEED_FRAC):
            self._reset()
            return
        if self._elapsed >= HARD_CAP_S:
            self._reset()

    # ---- render ----
    def render(self) -> Frame:
        f = Frame.black()

        rail_y = int(PIVOT_Y - 2)
        rail_rgb = (70, 70, 80)
        if self.pivots:
            x_lo = int(self.pivots[0][0] - BOB_RADIUS)
            x_hi = int(self.pivots[-1][0] + BOB_RADIUS)
            for x in range(max(0, x_lo), min(WIDTH, x_hi + 1)):
                _blend(f, x, rail_y, rail_rgb, 1.0)

        for i, (pvx, pvy) in enumerate(self.pivots):
            bx, by = self.pos[i]
            _line_aa(f, pvx, pvy, bx, by, (90, 70, 50))
            _blend(f, int(pvx), rail_y, (200, 200, 210), 1.0)
            _blend(f, int(pvx), rail_y + 1, (180, 180, 190), 1.0)
            _blit_disk(f, bx, by, (90, 70, 50), BOB_RADIUS)
            _blit_disk(f, bx, by, (200, 180, 140), BOB_RADIUS - 0.5)
            _blit_disk(f, bx - 0.5, by - 0.5, (255, 230, 180), 0.7)

        if self._flash_pos is not None:
            age = self._elapsed - self._flash_time
            if age < 0.15:
                k = max(0.0, 1.0 - age / 0.15)
                fx, fy = self._flash_pos
                _blit_disk(f, fx, fy, (int(180 * k), int(230 * k), int(255 * k)), 1.8)
        return f
