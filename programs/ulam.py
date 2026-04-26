"""Ulam spiral — walk integers outward on a square spiral; primes light up."""
from __future__ import annotations

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N = WIDTH * HEIGHT  # 4096 integers covers the whole panel
STEPS_PER_FRAME = 80
RESET_FRAMES = 120


def _sieve(limit: int) -> list[bool]:
    p = [True] * (limit + 1)
    p[0] = p[1] = False
    for i in range(2, int(limit ** 0.5) + 1):
        if p[i]:
            for j in range(i * i, limit + 1, i):
                p[j] = False
    return p


_PRIMES = _sieve(N + 4)


def _spiral_coords(limit: int) -> list[tuple[int, int]]:
    """Square-spiral lattice points (cx,cy)-centred; yields limit points."""
    cx, cy = WIDTH // 2 - 1, HEIGHT // 2 - 1
    x = y = 0
    dx, dy = 1, 0
    leg_len = 1
    step_in_leg = 0
    legs_at_len = 0
    out: list[tuple[int, int]] = []
    for _ in range(limit):
        out.append((cx + x, cy + y))
        x += dx; y += dy
        step_in_leg += 1
        if step_in_leg == leg_len:
            step_in_leg = 0
            dx, dy = -dy, dx
            legs_at_len += 1
            if legs_at_len == 2:
                legs_at_len = 0
                leg_len += 1
    return out


_COORDS = _spiral_coords(N)


class Ulam(Program):
    DESCRIPTION = "Ulam prime spiral — primes glow on a square integer spiral"

    def setup(self) -> None:
        self._cur = 1
        self._hold = 0

    def update(self, dt: float, events) -> None:
        if self._cur < N:
            self._cur = min(N, self._cur + STEPS_PER_FRAME)
        else:
            self._hold += 1
            if self._hold >= RESET_FRAMES:
                self._cur = 1
                self._hold = 0

    def render(self) -> Frame:
        f = Frame.black()
        for n in range(1, self._cur + 1):
            x, y = _COORDS[n - 1]
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                if _PRIMES[n]:
                    f.set(x, y, (255, 220, 120))
                else:
                    f.set(x, y, (28, 30, 50))
        # Highlight the leading edge so progress is visible while filling.
        if self._cur < N:
            x, y = _COORDS[self._cur - 1]
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                f.set(x, y, (255, 255, 255))
        return f
