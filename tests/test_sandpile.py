"""Abelian sandpile invariants — stdlib unittest only.

Tests the toppling rule itself via _drop_one/_drop_n on the deterministic
center-drop path: exact grain conservation inside the domain, bounded-loss
at the boundary, perpetual stabilization (no cell ever rests >= 4), and
purity of the no-seed path. No seed params, no update()/render(), no Frame.
"""
from __future__ import annotations

import unittest

from programs.sandpile import CX, CY, Sandpile


def _total(s: Sandpile) -> int:
    return sum(sum(row) for row in s._grid)


class GrainConservationTest(unittest.TestCase):
    def test_exact_conservation_inside_domain_at_1000(self) -> None:
        s = Sandpile()
        s.setup()
        s._drop_n(1000)
        self.assertEqual(_total(s), s._dropped)
        self.assertEqual(s._dropped, 1000)

    def test_boundary_loss_is_strict_and_never_creates(self) -> None:
        s = Sandpile()
        s.setup()
        s._drop_n(20000)
        self.assertGreater(s._dropped, _total(s), "grains WERE lost off the edge")
        self.assertGreaterEqual(_total(s), 0, "total must never go negative")
        self.assertLessEqual(_total(s), s._dropped, "toppling never creates grains")


class StabilizationTest(unittest.TestCase):
    def test_no_cell_unstable_after_domain_drop(self) -> None:
        s = Sandpile()
        s.setup()
        s._drop_n(1000)
        self.assertLessEqual(max(max(row) for row in s._grid), 3)

    def test_no_cell_unstable_after_boundary_drop(self) -> None:
        s = Sandpile()
        s.setup()
        s._drop_n(20000)
        self.assertLessEqual(max(max(row) for row in s._grid), 3)

    def test_stabilized_after_every_single_drop(self) -> None:
        s = Sandpile()
        s.setup()
        for _ in range(400):
            s._drop_one()
            self.assertLessEqual(
                max(max(row) for row in s._grid), 3,
                "grid must be stable after every toppling, not just at the end",
            )


class PurityTest(unittest.TestCase):
    def test_unseeded_center_drop_is_deterministic(self) -> None:
        a, b = Sandpile(), Sandpile()
        a.setup()
        b.setup()
        a._drop_n(500)
        b._drop_n(500)
        self.assertEqual(a._grid, b._grid)


class ToppleRedistributionTest(unittest.TestCase):
    def test_single_topple_redistributes_to_four_neighbours(self) -> None:
        s = Sandpile()
        s.setup()
        s._grid[CY][CX] = 3
        s._drop_one()
        self.assertEqual(s._grid[CY][CX], 0, "center topples to 0")
        for nx, ny in ((CX - 1, CY), (CX + 1, CY), (CX, CY - 1), (CX, CY + 1)):
            self.assertEqual(s._grid[ny][nx], 1, f"neighbour ({nx},{ny}) gains exactly 1")
        self.assertEqual(_total(s), 4, "3 pre-seeded + 1 dropped, all conserved")


if __name__ == "__main__":
    unittest.main()
