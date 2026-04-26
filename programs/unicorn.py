"""Pixel-art sky + rainbow + unicorn scene — procedural, walks across screen."""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

GROUND_Y = 54
UNICORN_SPEED = 6.0      # px/s
HORN_Y_OFFSET = -10      # relative to body top


# Sky gradient: dusk-lavender top → peach/pink horizon. Evaluated per row.
def _sky_color(y: int) -> tuple[int, int, int]:
    t = y / max(1, GROUND_Y - 1)
    # top (t=0): soft lavender; horizon (t=1): peach
    r = int(140 + (255 - 140) * t)
    g = int(170 + (200 - 170) * t)
    b = int(230 + (180 - 230) * t)
    return (r, g, b)


# ROYGBIV — classic 7-band. Innermost = violet, outermost = red.
RAINBOW = [
    (255, 70, 70),    # red
    (255, 150, 60),   # orange
    (255, 230, 80),   # yellow
    (120, 220, 100),  # green
    (80, 160, 240),   # blue
    (110, 80, 220),   # indigo
    (190, 100, 230),  # violet
]

# Cloud blobs: (cx, cy, rx, ry). Drawn as soft white ellipses.
CLOUDS = [
    (12, 10, 7, 3),
    (46, 6, 9, 3),
    (32, 16, 5, 2),
]


def _blend(f: Frame, x: int, y: int, rgb, w: float = 1.0) -> None:
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        return
    if w <= 0:
        return
    if w > 1.0:
        w = 1.0
    i = (y * WIDTH + x) * 3
    px = f.pixels
    r = int(rgb[0] * w); g = int(rgb[1] * w); b = int(rgb[2] * w)
    # Sky uses straight write, sprite uses over-write. For simplicity, overwrite.
    px[i] = r; px[i + 1] = g; px[i + 2] = b


def _set(f: Frame, x: int, y: int, rgb) -> None:
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        i = (y * WIDTH + x) * 3
        f.pixels[i] = rgb[0]; f.pixels[i + 1] = rgb[1]; f.pixels[i + 2] = rgb[2]


def _paint_sky(f: Frame) -> None:
    for y in range(GROUND_Y):
        rgb = _sky_color(y)
        for x in range(WIDTH):
            _set(f, x, y, rgb)


def _paint_rainbow(f: Frame) -> None:
    # Arc centered at (WIDTH/2, GROUND_Y + 15) with radii from 34 inward.
    cx = WIDTH / 2.0
    cy = GROUND_Y + 14.0
    outer_r = 36
    for band_idx, rgb in enumerate(RAINBOW):
        r0 = outer_r - band_idx * 2
        r1 = r0 - 2
        # Walk around the arc; only draw the upper half (y <= cy - 2).
        for theta_deg in range(180, 360 + 1):  # 180..360 covers upper half
            theta = math.radians(theta_deg)
            for rr in (r0, r0 - 1):
                px = int(round(cx + rr * math.cos(theta)))
                py = int(round(cy + rr * math.sin(theta)))
                if py >= GROUND_Y - 1:
                    continue
                _set(f, px, py, rgb)


def _paint_clouds(f: Frame) -> None:
    for cx, cy, rx, ry in CLOUDS:
        for dy in range(-ry - 1, ry + 2):
            for dx in range(-rx - 1, rx + 2):
                # Superelliptic blob (squared distance weighted).
                norm = (dx / rx) ** 2 + (dy / ry) ** 2
                if norm < 1.0:
                    _set(f, cx + dx, cy + dy, (250, 250, 255))
                elif norm < 1.35:
                    # soft edge
                    _set(f, cx + dx, cy + dy, (210, 215, 235))


def _paint_ground(f: Frame) -> None:
    for y in range(GROUND_Y, HEIGHT):
        t = (y - GROUND_Y) / max(1, HEIGHT - GROUND_Y)
        r = int(120 + (80 - 120) * t)
        g = int(200 + (130 - 200) * t)
        b = int(120 + (80 - 120) * t)
        for x in range(WIDTH):
            # Tiny grass-blade flicker
            if y == GROUND_Y and (x * 7 + 3) % 5 == 0:
                _set(f, x, y, (90, 170, 90))
            else:
                _set(f, x, y, (r, g, b))


# Unicorn sprite. Drawn at (x, y) where y is the ground line. All pixels
# painted via _set so sprite overwrites sky/rainbow/grass. Leg positions
# depend on walk phase (0..3 cycle).
def _paint_unicorn(f: Frame, x_center: float, phase: int) -> None:
    x = int(round(x_center))
    gy = GROUND_Y - 1  # hoof row

    body = (255, 248, 252)      # pearl white
    body_shade = (210, 200, 220)
    mane = (255, 130, 200)      # pink
    mane_light = (255, 180, 220)
    horn = (255, 220, 120)
    horn_hi = (255, 240, 180)
    eye = (60, 40, 80)
    hoof = (220, 170, 230)

    # Body (oval-ish, 10 wide, 4 tall) at y = gy-4 .. gy-1.
    for by in range(4):
        y = gy - 4 + by
        # Body width tapers at top/bottom row.
        if by == 0 or by == 3:
            span = 7
            offset = -3
        else:
            span = 9
            offset = -4
        for bx in range(span):
            px = x + offset + bx
            col = body_shade if by == 3 or (by == 0 and bx % 2 == 0) else body
            _set(f, px, y, col)

    # Head + neck (right side of body, pixel art horse silhouette).
    head_x = x + 5
    head_y = gy - 6
    # Neck diagonal 2 pixels
    _set(f, x + 4, gy - 5, body)
    _set(f, x + 5, gy - 5, body)
    _set(f, x + 5, gy - 6, body)
    # Head block 3x2
    for hy in range(2):
        for hx in range(3):
            _set(f, head_x + hx, head_y - hy, body)
    # Snout nub
    _set(f, head_x + 3, head_y, body_shade)
    # Eye
    _set(f, head_x + 1, head_y, eye)
    # Ear
    _set(f, head_x, head_y - 2, body)

    # Horn (diagonal 3 pixels, yellow).
    _set(f, head_x + 1, head_y - 2, horn)
    _set(f, head_x + 1, head_y - 3, horn_hi)
    _set(f, head_x + 2, head_y - 4, horn)

    # Mane — pink streaks trailing from the neck and top of head.
    _set(f, x + 3, gy - 5, mane)
    _set(f, x + 4, gy - 6, mane_light)
    _set(f, x + 3, gy - 6, mane)
    _set(f, x + 2, gy - 5, mane_light)
    _set(f, head_x, head_y - 1, mane)

    # Tail — pink curve trailing from the body's back (left side).
    tail_tip_dx = -1 if (phase % 2 == 0) else 0  # slight wave
    _set(f, x - 4, gy - 3, mane)
    _set(f, x - 5, gy - 3 + tail_tip_dx, mane_light)
    _set(f, x - 4, gy - 2, mane_light)
    _set(f, x - 5, gy - 2, mane)

    # Legs — 4 legs at relative xs (-3, -1, +2, +4). Walk cycle: diagonal
    # pairs lift alternately. Phase 0/2 legs A up, phase 1/3 legs B up.
    leg_xs = [-3, -1, 2, 4]
    for idx, lx in enumerate(leg_xs):
        up = (idx in (0, 3)) if (phase % 2 == 0) else (idx in (1, 2))
        leg_top = gy - 2
        leg_bot = gy if not up else gy - 1
        for ly in range(leg_top, leg_bot + 1):
            _set(f, x + lx, ly, body_shade if ly == leg_top else body)
        _set(f, x + lx, leg_bot, hoof)


class Unicorn(Program):
    DESCRIPTION = "sky + rainbow + clouds, a unicorn walks along the meadow"

    def setup(self) -> None:
        self.x = -6.0             # start off-screen left
        self._phase_accum = 0.0
        self.phase = 0
        self._sparkles: list[tuple[float, float, float]] = []

    def update(self, dt: float, events) -> None:
        self.x += UNICORN_SPEED * dt
        if self.x > WIDTH + 6:
            self.x = -6.0
        # Leg cycle at 4 steps/sec.
        self._phase_accum += dt * 4.0
        while self._phase_accum >= 1.0:
            self._phase_accum -= 1.0
            self.phase = (self.phase + 1) % 4
            # Spawn a rainbow-colored sparkle behind the unicorn each step.
            if 0 < self.x < WIDTH:
                self._sparkles.append((self.x - 5, GROUND_Y - 2, 0.0))
        # Age sparkles.
        self._sparkles = [(sx, sy, age + dt)
                          for (sx, sy, age) in self._sparkles if age + dt < 1.2]

    def render(self) -> Frame:
        f = Frame.black()
        _paint_sky(f)
        _paint_rainbow(f)
        _paint_clouds(f)
        _paint_ground(f)

        # Sparkles (rainbow colors cycling by age).
        for (sx, sy, age) in self._sparkles:
            life = 1.0 - age / 1.2
            hue_idx = int((age * 6) % len(RAINBOW))
            rgb = RAINBOW[hue_idx]
            r = int(rgb[0] * life); g = int(rgb[1] * life); b = int(rgb[2] * life)
            _set(f, int(sx), int(sy), (r, g, b))
            # Gentle upward drift
            off = int(age * 4)
            _set(f, int(sx), int(sy) - off, (r, g, b))

        _paint_unicorn(f, self.x, self.phase)
        return f
