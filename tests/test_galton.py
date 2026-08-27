"""Galton-board peg geometry and bin-index math, stdlib unittest only.

Scoped to the pure, RNG-free parts of programs/galton.py: the triangular
peg grid built at import time and the x->bin mapping. Nothing random, no
.setup()/.update()/.render(), no device.
"""
from __future__ import annotations

import unittest

from pixoolib.frame import WIDTH

from programs.galton import (
    NUM_BINS,
    PEGS,
    PEG_DX,
    PEG_DY,
    PEG_ROWS,
    PEG_START_Y,
    Galton,
)

CX = (WIDTH - 1) / 2  # 31.5, the x-center of the board


def _row_pegs(y: float) -> list[float]:
    """x-values of every peg whose y is within float tolerance of y."""
    return sorted(x for x, yy in PEGS if abs(yy - y) < 1e-9)


class PegLayoutTest(unittest.TestCase):
    def test_peg_count_is_triangular_number(self):
        # Rows 0..9 hold 1,2,...,10 pegs; 1+2+...+10 = 55.
        self.assertEqual(len(PEGS), 55)

    def test_row_structure_row_i_has_i_plus_1_pegs(self):
        for i in range(PEG_ROWS):
            y = PEG_START_Y + i * PEG_DY
            self.assertEqual(len(_row_pegs(y)), i + 1)

    def test_row_0_exact_position(self):
        self.assertEqual(_row_pegs(PEG_START_Y), [31.5])

    def test_last_row_exact_positions(self):
        y = PEG_START_Y + (PEG_ROWS - 1) * PEG_DY
        self.assertEqual(
            _row_pegs(y),
            [13.5, 17.5, 21.5, 25.5, 29.5, 33.5, 37.5, 41.5, 45.5, 49.5],
        )

    def test_every_row_symmetric_around_center(self):
        # The grid is centered on cx: each peg at x must have a mirror peg
        # at 2*cx - x in the same row.
        for i in range(PEG_ROWS):
            y = PEG_START_Y + i * PEG_DY
            xs = set(_row_pegs(y))
            for x in xs:
                self.assertIn(2 * CX - x, xs)


class BinIndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.g = Galton()

    def test_concrete_mappings(self):
        # Hard-coded from the layout: leftmost_x = 11.5, bins are 4px wide.
        self.assertEqual(self.g._bin_index(11.5), 0)   # leftmost peg column
        self.assertEqual(self.g._bin_index(15.5), 1)
        self.assertEqual(self.g._bin_index(31.5), 5)   # dead center
        self.assertEqual(self.g._bin_index(51.5), 10)  # past right edge, clamped

    def test_monotonic_across_wide_range(self):
        # 12 samples crossing both negative and >WIDTH territory exercises
        # both clamps; x1 < x2 must imply idx(x1) <= idx(x2).
        xs = [-1000.0, -5.0, 0.0, 10.0, 11.5, 15.5, 31.5, 40.0, 51.5, 64.0, 100.0, 1000.0]
        self.assertGreaterEqual(len(xs), 10)
        prev = self.g._bin_index(xs[0])
        for x in xs[1:]:
            cur = self.g._bin_index(x)
            self.assertLessEqual(prev, cur)
            prev = cur

    def test_monotonic_on_evenly_spaced_samples(self):
        samples = [-800.0 + i * 80.0 for i in range(10)]
        prev = self.g._bin_index(samples[0])
        for x in samples[1:]:
            cur = self.g._bin_index(x)
            self.assertLessEqual(prev, cur)
            prev = cur

    def test_clamped_at_both_extremes(self):
        self.assertEqual(self.g._bin_index(-1000.0), 0)
        self.assertEqual(self.g._bin_index(1000.0), NUM_BINS - 1)


if __name__ == "__main__":
    unittest.main()
