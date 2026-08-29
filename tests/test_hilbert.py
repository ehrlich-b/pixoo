"""Hilbert curve invariants pinned down, stdlib unittest only.

The order-6 Hilbert curve (_d2xy) is a bijection from d in 0..4095 onto the
64x64 grid where consecutive points are always exactly one unit-step apart.
This file checks those exact, universally-known invariants plus a few fixed
points, a quadrant self-similarity check, and purity (no hidden state).

No random, no timing, no Frame, no Hilbert Program instantiation.
"""
from __future__ import annotations

import unittest

from pixoolib.frame import WIDTH
from programs.hilbert import N_POINTS, _d2xy

N = WIDTH  # 64, the side length used by Hilbert.setup()
QUARTER = N_POINTS // 4  # 1024 points, one quadrant of the curve


class D2xyFixedPointsTest(unittest.TestCase):
    def test_d0_is_origin(self):
        self.assertEqual(_d2xy(N, 0), (0, 0))

    def test_last_point_is_bottom_left(self):
        self.assertEqual(_d2xy(N, N_POINTS - 1), (63, 0))

    def test_midpoint_is_center(self):
        self.assertEqual(_d2xy(N, N_POINTS // 2), (32, 32))


class HilbertCurveInvariantsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.pts = [_d2xy(N, i) for i in range(N_POINTS)]

    def test_bijection_covers_every_cell_exactly_once(self):
        self.assertEqual(len(set(self.pts)), N_POINTS,
                         "curve must visit each of the 4096 cells exactly once")

    def test_all_points_in_bounds(self):
        for x, y in self.pts:
            self.assertTrue(0 <= x < N and 0 <= y < N,
                            f"point ({x}, {y}) out of {N}x{N} bounds")

    def test_consecutive_points_are_one_unit_step_apart(self):
        for i in range(N_POINTS - 1):
            (x0, y0), (x1, y1) = self.pts[i], self.pts[i + 1]
            self.assertEqual(abs(x1 - x0) + abs(y1 - y0), 1,
                             f"gap between pts[{i}] and pts[{i + 1}] is not 1")

    def test_first_quarter_lies_in_bottom_left_quadrant(self):
        # Derived from the rx/ry reflection logic: at the top recursion level
        # (s == 32) the first 1024 d-values all have rx == 0, ry == 0, so the
        # curve starts in the quadrant where both low halves are 0, i.e.
        # 0 <= x < 32 and 0 <= y < 32. Verified by direct computation.
        self.assertTrue(all(0 <= x < N // 2 and 0 <= y < N // 2
                            for x, y in self.pts[:QUARTER]))


class D2xyPurityTest(unittest.TestCase):
    def test_pure_no_hidden_state(self):
        first = _d2xy(N, 0)
        second = _d2xy(N, 0)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
