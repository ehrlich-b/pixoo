"""Snowflake symmetry, pinned stdlib unittest only.

Every behaviour under test lives in _set_sym/_build_sym/_reset — none touch
random, so no .update() is ever called here.

- _set_sym(0,0) is the degenerate zero-vector case: all 12 rotations of the
  origin collapse onto the single center pixel.
- _set_sym(5,2) is the full 12-fold orbit (hard-coded exact set).
- _set_sym(3,0) is the on-axis 6-fold collapse (hard-coded exact set).
- A third offset is checked against an independent reimplementation of the
  rotation formula (differential, not hard-coded).
- A large offset exercises edge clipping (radius beyond the 0..63 bounds).
"""
from __future__ import annotations

import math
import unittest

from programs.snowflake import Snowflake

WIDTH = 64
HEIGHT = 64
CX = WIDTH // 2
CY = HEIGHT // 2


def _lit_pixels(snow: Snowflake) -> set[tuple[int, int]]:
    """All lit (x, y) cells in the snowflake's grid, as a set."""
    return {(x, y)
            for y in range(HEIGHT)
            for x in range(WIDTH)
            if snow._grid[y * WIDTH + x]}


def _predict_orbit(dx: int, dy: int) -> set[tuple[int, int]]:
    """Independent reimplementation of the 6-fold x mirror rotation.

    Deliberately NOT imported from snowflake.py — an independent differential
    check of the same cos/sin geometry derived from the documented behaviour.
    Returns only the in-bounds points, mirroring _set_sym's clipping rule.
    """
    pts = set()
    for k in range(6):
        ang = k * math.pi / 3
        cs = math.cos(ang)
        sn = math.sin(ang)
        for mirror in (1, -1):
            rx = dx * cs - (dy * mirror) * sn
            ry = dx * sn + (dy * mirror) * cs
            xi = CX + int(round(rx))
            yi = CY + int(round(ry))
            if 0 <= xi < WIDTH and 0 <= yi < HEIGHT:
                pts.add((xi, yi))
    return pts


class SnowflakeSymmetryTest(unittest.TestCase):
    def test_setup_leaves_exactly_one_lit_pixel_at_center(self):
        snow = Snowflake()
        snow.setup()
        lit = _lit_pixels(snow)
        self.assertEqual(lit, {(CX, CY)},
                         "zero-vector orbit must collapse to the single center pixel")

    def test_set_sym_5_2_full_twelve_fold_orbit_exact_set(self):
        snow = Snowflake()
        snow.setup()
        before = _lit_pixels(snow)
        snow._set_sym(5, 2)
        new = _lit_pixels(snow) - before
        self.assertEqual(new, {
            (27, 30), (27, 34), (28, 29), (28, 35),
            (31, 27), (31, 37), (33, 27), (33, 37),
            (36, 29), (36, 35), (37, 30), (37, 34),
        }, "low-symmetry offset must paint the full 12-fold orbit")

    def test_set_sym_3_0_on_axis_collapses_to_six_exact_set(self):
        snow = Snowflake()
        snow.setup()
        before = _lit_pixels(snow)
        snow._set_sym(3, 0)
        new = _lit_pixels(snow) - before
        self.assertEqual(new, {
            (29, 32), (30, 29), (31, 35),
            (34, 29), (34, 35), (35, 32),
        }, "dy=0 makes mirror a no-op, so each rotation paints one pixel, not two")

    def test_set_sym_third_offset_matches_independent_prediction(self):
        dx, dy = 2, 7  # non-axis, non-degenerate: must be a full 12-fold orbit
        snow = Snowflake()
        snow.setup()
        before = _lit_pixels(snow)
        snow._set_sym(dx, dy)
        new = _lit_pixels(snow) - before
        expect = _predict_orbit(dx, dy)
        self.assertEqual(new, expect,
                         "code output must match the independent rotation helper")
        self.assertEqual(len(new), 12, "low-symmetry third offset must not collapse")

    def test_set_sym_large_offset_clips_without_raising(self):
        dx, dy = 24, 24  # radius ~33.9 > 32 half-extent, so some points must clip
        self.assertGreater(len(_predict_orbit(dx, dy)), 0,
                           "at least one rotated point must stay in bounds")
        self.assertLess(len(_predict_orbit(dx, dy)), 12,
                        "precondition: this offset genuinely loses points")
        snow = Snowflake()
        snow.setup()
        before = _lit_pixels(snow)
        snow._set_sym(dx, dy)  # must not raise
        new = _lit_pixels(snow) - before
        self.assertEqual(new, _predict_orbit(dx, dy),
                         "every in-bounds predicted point must be lit")
        self.assertLess(len(new), 12,
                        "offsets beyond radius ~32 must be clipped by the device bounds")


class SnowflakeBuildSymTest(unittest.TestCase):
    def test_build_sym_returns_twelve_rotations_x_mirrors(self):
        sym = Snowflake._build_sym()  # staticmethod, called without an instance
        self.assertEqual(len(sym), 12, "6 rotations x 2 mirrors")
        expect = []
        for k in range(6):
            ang = k * math.pi / 3
            cs = math.cos(ang)
            sn = math.sin(ang)
            expect.append((cs, sn, 1.0, 0.0))   # rotation only
            expect.append((cs, sn, -1.0, 0.0))  # flipped mirror
        self.assertEqual(len(expect), len(sym))
        for got, want in zip(sym, expect):
            self.assertEqual(len(got), 4, "each entry is (cos, sin, mirror, 0.0)")
            self.assertEqual(got[2], want[2], "mirror flag order: 1.0 then -1.0")
            self.assertEqual(got[3], 0.0, "4th component is always 0.0")
            self.assertAlmostEqual(got[0], want[0], places=12, msg="cos term")
            self.assertAlmostEqual(got[1], want[1], places=12, msg="sin term")


if __name__ == "__main__":
    unittest.main()
