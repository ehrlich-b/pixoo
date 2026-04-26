"""Double pendulum — N copies with tiny offsets show chaos divergence.

Params:
  n=INT  how many pendulum copies (default 1). Each gets its own color
         and an added initial-angle perturbation of ~2e-3 * index.
"""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

G = 9.8
L1 = 1.0
L2 = 1.0
M1 = 1.0
M2 = 1.0
# Slow Rayleigh dissipation. Half-life ≈ ln(2)/DAMP ≈ 2 minutes; the reset
# watchdog picks that up and restarts before the pendulum looks dead.
DAMP = 0.006

# Fixed 200Hz physics tick so motion is wall-clock accurate even when the
# device push stalls the render loop (Pixoo is ~5fps synchronous).
SIM_HZ = 200.0
SIM_DT = 1.0 / SIM_HZ
# Slow-mo so per-frame positional delta reads clearly at the Pixoo's ~5fps.
TIME_SCALE = 0.5

TRAIL_LEN = 24   # short trail — anything longer becomes noodle soup on 64x64

# Chaos offset per copy. With N copies, copy i starts at theta1 + i*OFFSET.
CHAOS_OFFSET = 2e-3

# Reset tuning.
WINDOW_S = 15.0
WARMUP_S = 20.0
HARD_CAP_S = 150.0

# Per-copy palette: (bob_bright, bob_dim, rod, trail_base). Cycles if n >
# len(PALETTE), but we don't expect more than ~6 on a 64x64.
PALETTE = [
    ((255, 200, 120), (220, 150, 80),  (130, 90, 40),  (255, 140, 40)),  # orange
    ((160, 230, 255), (80, 170, 210),  (40, 90, 130),  (40, 170, 230)),  # cyan
    ((230, 170, 255), (190, 110, 230), (100, 50, 140), (200, 100, 255)), # violet
    ((170, 255, 180), (100, 220, 130), (40, 130, 60),  (100, 230, 130)), # green
    ((255, 170, 200), (220, 100, 140), (130, 50, 80),  (255, 100, 150)), # pink
    ((255, 245, 140), (230, 200, 80),  (140, 120, 40), (255, 220, 80)),  # yellow
]


def _deriv(s):
    t1, w1, t2, w2 = s
    d = t1 - t2
    cd, sd = math.cos(d), math.sin(d)
    denom = 2 * M1 + M2 - M2 * math.cos(2 * d)
    dw1 = (
        -G * (2 * M1 + M2) * math.sin(t1)
        - M2 * G * math.sin(t1 - 2 * t2)
        - 2 * sd * M2 * (w2 * w2 * L2 + w1 * w1 * L1 * cd)
    ) / (L1 * denom) - DAMP * w1
    dw2 = (
        2 * sd * (
            w1 * w1 * L1 * (M1 + M2)
            + G * (M1 + M2) * math.cos(t1)
            + w2 * w2 * L2 * M2 * cd
        )
    ) / (L2 * denom) - DAMP * w2
    return (w1, dw1, w2, dw2)


def _rk4_step(s, dt):
    def add(a, b, k):
        return tuple(ai + bi * k for ai, bi in zip(a, b))
    k1 = _deriv(s)
    k2 = _deriv(add(s, k1, dt / 2))
    k3 = _deriv(add(s, k2, dt / 2))
    k4 = _deriv(add(s, k3, dt))
    return tuple(
        si + dt * (k1i + 2 * k2i + 2 * k3i + k4i) / 6
        for si, k1i, k2i, k3i, k4i in zip(s, k1, k2, k3, k4)
    )


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


def _plot_aa(f: Frame, fx: float, fy: float, rgb, intensity: float = 1.0) -> None:
    ix = int(math.floor(fx)); iy = int(math.floor(fy))
    dx = fx - ix; dy = fy - iy
    _blend(f, ix, iy, rgb, (1 - dx) * (1 - dy) * intensity)
    _blend(f, ix + 1, iy, rgb, dx * (1 - dy) * intensity)
    _blend(f, ix, iy + 1, rgb, (1 - dx) * dy * intensity)
    _blend(f, ix + 1, iy + 1, rgb, dx * dy * intensity)


def _line_aa(f: Frame, fx0: float, fy0: float, fx1: float, fy1: float, rgb) -> None:
    dx = fx1 - fx0; dy = fy1 - fy0
    length = max(abs(dx), abs(dy))
    steps = int(length * 2) + 2
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


class Pendulum(Program):
    DESCRIPTION = "double pendulum — N copies (default 1) with chaos divergence"

    def setup(self) -> None:
        self.n = max(1, int(self.params.get("n", 1)))
        self._reset()

    def _reset(self) -> None:
        # Shared random seed so every copy starts from the same chaotic initial
        # condition, differentiated only by CHAOS_OFFSET * i on theta1.
        t1 = random.uniform(0.85, 0.99) * math.pi * random.choice((-1, 1))
        t2 = random.uniform(0.85, 0.99) * math.pi * random.choice((-1, 1))
        w1 = random.uniform(-0.3, 0.3)
        w2 = random.uniform(-0.3, 0.3)
        self.sims = [
            (t1 + i * CHAOS_OFFSET, w1, t2, w2) for i in range(self.n)
        ]
        self.trails: list[list[tuple[float, float]]] = [[] for _ in range(self.n)]
        self._accum = 0.0
        self._elapsed = 0.0
        self._peak_all = 0.0
        self._peak_window = 0.0
        self._window_start = 0.0

    def update(self, dt: float, events) -> None:
        scaled = min(dt, 0.5) * TIME_SCALE
        self._accum += scaled
        while self._accum >= SIM_DT:
            self.sims = [_rk4_step(s, SIM_DT) for s in self.sims]
            self._accum -= SIM_DT

        self._elapsed += scaled
        # Use sum of |w| across all copies and joints as the "alive" proxy.
        speed = sum(abs(s[1]) + abs(s[3]) for s in self.sims)
        if speed > self._peak_all:
            self._peak_all = speed
        if speed > self._peak_window:
            self._peak_window = speed

        if self._elapsed - self._window_start >= WINDOW_S:
            if (self._elapsed >= WARMUP_S
                    and self._peak_window < self._peak_all * 0.5):
                self._reset()
                return
            self._window_start = self._elapsed
            self._peak_window = 0.0

        if self._elapsed >= HARD_CAP_S:
            self._reset()

    def _project(self, state):
        px, py = WIDTH / 2.0, HEIGHT / 2.0 - 2.0
        scale = 14.0
        t1, _, t2, _ = state
        x1 = px + scale * math.sin(t1)
        y1 = py + scale * math.cos(t1)
        x2 = x1 + scale * math.sin(t2)
        y2 = y1 + scale * math.cos(t2)
        return (px, py), (x1, y1), (x2, y2)

    def render(self) -> Frame:
        f = Frame.black()
        projs = [self._project(s) for s in self.sims]

        for i, (_, _, a2) in enumerate(projs):
            self.trails[i].append(a2)
            if len(self.trails[i]) > TRAIL_LEN:
                self.trails[i].pop(0)

        # Trails: draw oldest copies first, newest on top so later copies win
        # overlap. Within each trail, fade quadratically.
        for i, trail in enumerate(self.trails):
            base = PALETTE[i % len(PALETTE)][3]
            n = len(trail)
            for j in range(n - 1):
                k = (j + 1) / n
                k2 = k * k
                c = (int(base[0] * k2), int(base[1] * k2), int(base[2] * k2))
                x0, y0 = trail[j]; x1, y1 = trail[j + 1]
                _line_aa(f, x0, y0, x1, y1, c)

        # Rods + bobs. Later copies on top so the "primary" (index 0) sits
        # behind its divergent siblings — i.e. the outliers are emphasized.
        for i, (piv, p1, p2) in enumerate(projs):
            bob_hi, bob_lo, rod, _ = PALETTE[i % len(PALETTE)]
            _line_aa(f, piv[0], piv[1], p1[0], p1[1], rod)
            _line_aa(f, p1[0], p1[1], p2[0], p2[1], rod)
            _blit_disk(f, p1[0], p1[1], bob_lo, 1.2)
            _blit_disk(f, p2[0], p2[1], bob_hi, 1.5)

        # Shared pivot on top.
        piv = projs[0][0]
        _blit_disk(f, piv[0], piv[1], (90, 90, 100), 2.4)
        _blit_disk(f, piv[0], piv[1], (240, 240, 255), 1.5)
        _blit_disk(f, piv[0], piv[1], (255, 230, 180), 0.7)
        return f
