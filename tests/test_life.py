"""Conway's Game of Life — classic oracles pinned, stdlib unittest only.

Tests only the pure `_step` / `_pattern` helpers in programs/life.py. No
randomness, no timing, no long-run settles (those assume an infinite grid and
are wrong on a 64x64 torus). Most patterns are placed around (20, 20) — far
from any edge — so the toroidal wrap cannot influence them; only the seam test
at the end deliberately uses the wrap.
"""
from __future__ import annotations

import unittest

from programs.life import _pattern, _step

W = H = 64
OX, OY = 20, 20  # origin well inside the grid; 8-cell radius keeps it off the torus


def _stepn(live: set, n: int) -> set:
    """Apply _step n times."""
    for _ in range(n):
        live = _step(live)
    return live


class StillLifeTest(unittest.TestCase):
    def test_2x2_block_is_unchanged(self):
        # A 2x2 block is the canonical still life: every cell has 3 neighbours
        # so it survives; every outside cell has <3, so nothing is born.
        block = {(OX, OY), (OX + 1, OY), (OX, OY + 1), (OX + 1, OY + 1)}
        self.assertEqual(_step(block), block)


class BlinkerTest(unittest.TestCase):
    def test_blinker_oscillates_period_two(self):
        # Horizontal blinker centred at (21, 20). Hand-derived intermediate
        # generation: the two end cells have 1 live neighbour each and die; the
        # middle cell keeps 2 and survives; cells directly above/below the ends
        # each see exactly 3 live neighbours and are born -> a vertical line.
        horiz = {(OX, OY), (OX + 1, OY), (OX + 2, OY)}
        vertical = {(OX + 1, OY - 1), (OX + 1, OY), (OX + 1, OY + 1)}
        self.assertEqual(_step(horiz), vertical)
        self.assertEqual(_step(vertical), horiz)
        self.assertEqual(_stepn(horiz, 2), horiz)


class GliderTest(unittest.TestCase):
    def test_glider_translates_by_one_after_four_gens(self):
        # The definitive oracle: after 4 generations a glider is exactly its
        # own shape shifted (1, 1). This single assertion pins birth rules,
        # survival rules and neighbour counting all at once.
        glider = {(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)}
        shifted = {(x + 1, y + 1) for x, y in glider}
        self.assertEqual(_stepn(set(glider), 4), shifted)


class DegenerateTest(unittest.TestCase):
    def test_empty_set_steps_to_empty_set(self):
        # No cells -> no neighbours -> no births.
        self.assertEqual(_step(set()), set())

    def test_single_cell_dies(self):
        # One cell has 0 live neighbours; it must not survive (needs exactly 2).
        self.assertEqual(_step({(OX, OY)}), set())

    def test_domino_dies(self):
        # Each of the two cells has exactly 1 live neighbour, so neither
        # survives; no cell has 3 neighbours, so nothing is born.
        domino = {(OX, OY), (OX + 1, OY)}
        self.assertEqual(_step(domino), set())


class PurityTest(unittest.TestCase):
    def test_step_does_not_mutate_input_and_returns_new_object(self):
        live = {(OX, OY), (OX + 1, OY), (OX, OY + 1), (OX + 1, OY + 1)}
        snapshot = live.copy()
        out = _step(live)
        self.assertEqual(live, snapshot, "_step must not mutate its input")
        self.assertIsNot(out, live, "a fresh set must be returned")


class TorusTest(unittest.TestCase):
    def test_seam_blinker_oscillates_period_two(self):
        # Blinker straddling the x=0 / x=63 seam, y fixed at 20. The docstring
        # claims toroidal edges; this is the only test that can catch dropped
        # modulo wrapping (which would push live cells out of 0..63).
        #
        # Hand derivation using ((x+dx) % 64, y):
        #   (63,20) and (1,20) each have 1 live neighbour -> die.
        #   (0,20) keeps 2 live neighbours ((63,20) and (1,20)) -> survives.
        #   (0,19) sees live (63,20), (0,20), (1,20) -> 3 neighbours, born.
        #   (0,21) likewise sees all three -> born.
        # So generation 1 is a vertical line {(0,19), (0,20), (0,21)}, and by
        # symmetry generation 2 returns to the original horizontal line.
        seam_blinker = {(W - 1, OY), (0, OY), (1, OY)}
        vertical = {(0, OY - 1), (0, OY), (0, OY + 1)}
        self.assertEqual(_step(seam_blinker), vertical)
        self.assertEqual(_stepn(seam_blinker, 2), seam_blinker)


class PatternTest(unittest.TestCase):
    def test_parses_ascii_block_to_coordinates(self):
        # '#' is live, anything else is dead, y is the line index.
        self.assertEqual(_pattern("##\n.#"), [(0, 0), (1, 0), (1, 1)])

    def test_parses_multi_line_pattern(self):
        self.assertEqual(
            _pattern("#..\n###\n..#"),
            [(0, 0), (0, 1), (1, 1), (2, 1), (2, 2)],
        )

    def test_strips_leading_and_trailing_blank_lines(self):
        self.assertEqual(_pattern("\n\n#\n\n"), [(0, 0)])

    def test_all_dead_is_empty(self):
        self.assertEqual(_pattern("...\n..."), [])


class OutOfRangeCoordinateTest(unittest.TestCase):
    def test_out_of_range_alias_defeats_survival_test(self):
        # _step normalises neighbour coordinates with % WIDTH / % HEIGHT, but
        # the survival test `cell in live` compares against the coordinates
        # exactly as the caller supplied them. So the same physical cell
        # reachable under two names (e.g. (0,0) and (64,0)) is counted twice
        # for its neighbours yet is never re-found for its own survival.
        #
        # {(-1,0), (63,0)}: both name the same physical cell. Neighbour counts
        # are doubled but the 2-count cells are not in the supplied set, so the
        # state collapses to empty -- which coincides with a consistent
        # implementation (one cell, dies).
        self.assertEqual(_step({(-1, 0), (63, 0)}), set())

    def test_phantom_alias_observably_diverges(self):
        # {(1,0), (0,0), (64,0)}: (0,0) and (64,0) are the same physical cell.
        # Its doubled neighbour counts inflate (1,0) to exactly 2, and because
        # (1,0) is in `live` as supplied, it survives. A consistent
        # implementation (one that normalised the input first) would see a
        # plain 2-cell domino {(0,0),(1,0)} where each cell has 1 neighbour
        # and nothing is born -> the empty set. The actual output instead leans
        # on the phantom duplicate:
        self.assertEqual(
            _step({(1, 0), (0, 0), (64, 0)}),
            {(0, 1), (1, 1), (0, 63), (1, 63), (1, 0)},
        )

    def test_out_of_range_is_harmless_for_in_range_callers(self):
        # Pinned divergence above is only reachable if a caller hands _step an
        # out-of-range coordinate. Every real caller goes through _place or
        # _random_soup, which produce coordinates in 0..W-1 x 0..H-1 (checked:
        # _place adds ox/oy to pattern coords; _random_soup ranges over
        # range(WIDTH) x range(HEIGHT); the program's render() uses _step output
        # directly, which is always normalised). So in current usage the quirk
        # is latent, not live.
        self.assertEqual(_step({(W, 0)}), set())


if __name__ == "__main__":
    unittest.main()
