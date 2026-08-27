"""Newton's cradle physics invariants — stdlib unittest only.

Exercises the Verlet + position-based constraint core (`_step`) directly,
bypassing `setup()` (which picks a random kicker via unseeded `random`):
state is injected by hand so the suite is fully deterministic. No hardware,
no network, no timing assertions.
"""
from __future__ import annotations

import math
import unittest

from programs.cradle import (
    BOB_RADIUS,
    CONSTRAINT_ITERS,
    SIM_DT,
    Cradle,
    ROD_LEN,
)

PIVOT_Y = 5.0


def _make_cradle(pivots, pos, prev) -> Cradle:
    """Build a Cradle with explicit physics state, bypassing setup()."""
    c = Cradle()
    c.n = len(pivots)
    c.pivots = pivots
    c.pos = [list(p) for p in pos]
    c.prev = [list(p) for p in prev]
    c._accum = 0.0
    c._elapsed = 0.0
    c._peak_speed = 0.0
    c._flash_time = -1.0
    c._flash_pos = None
    return c


def _rod_errors(c: Cradle) -> list[float]:
    """Absolute deviation of each ball's pivot distance from ROD_LEN."""
    errs = []
    for i in range(c.n):
        pvx, pvy = c.pivots[i]
        dx = c.pos[i][0] - pvx
        dy = c.pos[i][1] - pvy
        errs.append(abs(math.hypot(dx, dy) - ROD_LEN))
    return errs


class RodConstraintTest(unittest.TestCase):
    def test_rod_length_invariant_no_collision(self):
        pivots = [(10.0, PIVOT_Y), (20.0, PIVOT_Y), (30.0, PIVOT_Y)]
        kick = 1.1
        pos = [
            [10.0 + ROD_LEN * math.sin(kick), PIVOT_Y + ROD_LEN * math.cos(kick)],
            [20.0, PIVOT_Y + ROD_LEN],
            [30.0, PIVOT_Y + ROD_LEN],
        ]
        c = _make_cradle(pivots, pos, pos)
        for _ in range(20):
            c._step(SIM_DT)
            for err in _rod_errors(c):
                self.assertLess(err, 1e-6)

    def test_rod_length_invariant_during_collision(self):
        pivots = [(10.0, PIVOT_Y), (10.0 + 2 * BOB_RADIUS, PIVOT_Y)]
        pos = [
            [10.0, PIVOT_Y + ROD_LEN],
            [10.0 + 2 * BOB_RADIUS, PIVOT_Y + ROD_LEN],
        ]
        prev = [[pos[0][0] - 0.05, pos[0][1]], list(pos[1])]
        c = _make_cradle(pivots, pos, prev)
        for _ in range(50):
            c._step(SIM_DT)
            for err in _rod_errors(c):
                self.assertLess(err, 1e-3)

    def test_no_interpenetration_during_collision(self):
        pivots = [(10.0, PIVOT_Y), (10.0 + 2 * BOB_RADIUS, PIVOT_Y)]
        pos = [
            [10.0, PIVOT_Y + ROD_LEN],
            [10.0 + 2 * BOB_RADIUS, PIVOT_Y + ROD_LEN],
        ]
        prev = [[pos[0][0] - 0.05, pos[0][1]], list(pos[1])]
        c = _make_cradle(pivots, pos, prev)
        for _ in range(50):
            c._step(SIM_DT)
            d = math.hypot(c.pos[1][0] - c.pos[0][0], c.pos[1][1] - c.pos[0][1])
            self.assertGreaterEqual(d, 2 * BOB_RADIUS - 1e-6)

    def test_x_momentum_approximately_conserved_through_collision(self):
        pivots = [(10.0, PIVOT_Y), (10.0 + 2 * BOB_RADIUS, PIVOT_Y)]
        pos = [
            [10.0, PIVOT_Y + ROD_LEN],
            [10.0 + 2 * BOB_RADIUS, PIVOT_Y + ROD_LEN],
        ]
        prev = [[pos[0][0] - 0.05, pos[0][1]], list(pos[1])]
        c = _make_cradle(pivots, pos, prev)
        before = sum(c.pos[i][0] - c.prev[i][0] for i in range(c.n))
        c._step(SIM_DT)
        after = sum(c.pos[i][0] - c.prev[i][0] for i in range(c.n))
        self.assertLess(abs(before - after), 1e-2)

    def test_hanging_ball_at_rest_is_exactly_unmoved(self):
        pivot = (10.0, PIVOT_Y)
        rest = [10.0, PIVOT_Y + ROD_LEN]
        c = _make_cradle([pivot], [rest], [rest])
        for _ in range(20):
            c._step(SIM_DT)
        self.assertEqual(c.pos[0], [10.0, PIVOT_Y + ROD_LEN])
        self.assertEqual(c.prev[0], [10.0, PIVOT_Y + ROD_LEN])


if __name__ == "__main__":
    unittest.main()
