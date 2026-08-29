"""Tests for the pure decision core of programs/tetris_ai.py.

`_drop` and `_heuristic` decide every move the AI makes and are pure: no
IO, no random, no clock (`import random` at module scope is only used by
the `TetrisAI` class for bag-shuffling, never inside these two functions).
They were untested at the time of writing; these tests pin the behaviour.
Stdlib unittest only, matching tests/test_protocol.py.
"""
from __future__ import annotations

import copy
import unittest

from programs.tetris_ai import COLS, ROWS, SHAPES, _drop, _heuristic

FLOOR = ROWS - 1  # 19: the bottom row of the ROWS=20 grid


def grid_from(rows: list[str]) -> list[list[str]]:
    """Build a ROWS x COLS grid from one string per row."""
    grid = [list(r) for r in rows]
    assert len(grid) == ROWS, f"expected {ROWS} rows, got {len(grid)}"
    assert all(len(r) == COLS for r in grid), f"every row must be {COLS} wide"
    return grid


def filled_cells(grid: list[list[str]]) -> list[tuple[int, int]]:
    return [(r, c) for r in range(ROWS) for c in range(COLS)
            if grid[r][c] != "."]


def any_full_row(grid: list[list[str]]) -> bool:
    return any(all(cell != "." for cell in row) for row in grid)


class DropEmptyBoardTest(unittest.TestCase):
    def test_single_cell_lands_on_floor(self):
        g = grid_from(["." * COLS] * ROWS)
        res = _drop(g, [(0, 0)], 0, "X")
        self.assertIsNotNone(res)
        new_grid, landing_height, cleared, y_final = res

        # Hand derivation: with a single cell (offset y_ == 0) the piece fits
        # from y_try = 0 up to y_try = ROWS - 1; the shallowest y_try that
        # does NOT fit is ROWS, because cy = y_try + 0 = ROWS >= ROWS trips the
        # "cy >= ROWS" guard. y_final = y_try - 1 = ROWS - 1 = 19 (the floor).
        self.assertEqual(y_final, FLOOR)
        self.assertEqual(cleared, 0)
        # bottom_y = y_final + max(y_) = 19, so landing_height = ROWS - 19 - 1.
        self.assertEqual(landing_height, 0)
        self.assertEqual(filled_cells(new_grid), [(FLOOR, 0)])
        self.assertEqual(new_grid[FLOOR][0], "X")


class DropStackTest(unittest.TestCase):
    def test_stacks_exactly_one_row_higher(self):
        # One cell already sitting on the floor in column 0.
        g = grid_from(["." * COLS] * (ROWS - 1)
                      + ["X" + "." * (COLS - 1)])
        res = _drop(g, [(0, 0)], 0, "X")
        self.assertIsNotNone(res)
        new_grid, landing_height, cleared, y_final = res

        # The piece can reach y_try = 18 (cell at cy = 18 is empty) but at
        # y_try = 19 it would hit grid[19][0] == "X", so y_final = 18.
        # Hand-derived: exactly one row above the old cell.
        self.assertEqual(y_final, FLOOR - 1)
        self.assertEqual(cleared, 0)
        self.assertEqual(new_grid[FLOOR - 1][0], "X")
        self.assertEqual(new_grid[FLOOR][0], "X")
        self.assertEqual(len(filled_cells(new_grid)), 2)


class DropOutOfBoundsTest(unittest.TestCase):
    def setUp(self):
        self.g = grid_from(["." * COLS] * ROWS)

    def test_left_edge_rejected_without_raising(self):
        # Guard at the top of _drop: col + x_ = -1 + 0 = -1 < 0 -> None.
        self.assertIsNone(_drop(self.g, [(0, 0)], -1, "X"))
        self.assertTrue(True, "must return None, not raise")

    def test_right_edge_rejected_without_raising(self):
        # Guard: col + x_ = COLS + 0 = 10 >= COLS -> None.
        self.assertIsNone(_drop(self.g, [(0, 0)], COLS, "X"))

    def test_partial_overhang_rejected(self):
        # Two-cell shape whose first cell fits at column COLS - 1 but whose
        # second cell would sit at cx = COLS -> still None.
        self.assertIsNone(_drop(self.g, [(0, 0), (1, 0)], COLS - 1, "X"))

    def test_all_guarded_columns_never_raise(self):
        for col in (-3, -2, -1, COLS, COLS + 1, COLS + 2):
            _drop(self.g, [(0, 0)], col, "X")  # must not raise


class DropNoMutationTest(unittest.TestCase):
    def test_input_grid_is_not_mutated(self):
        g = grid_from(["." * COLS] * (ROWS - 2)
                      + ["XX" + "." * (COLS - 2), "XXXXXXXXXX"])
        before = copy.deepcopy(g)
        res = _drop(g, [(0, 0)], 0, "X")
        self.assertIsNotNone(res)
        # A search that mutated the board it evaluates would corrupt every
        # later candidate in _plan(). This confirms _drop is side-effect free.
        self.assertEqual(g, before)
        self.assertTrue(all(g[r][c] == before[r][c]
                            for r in range(ROWS) for c in range(COLS)))


class LineClearTest(unittest.TestCase):
    def test_single_line_clear_shifts_rows_down(self):
        # Row 17 holds a marker ("XX") we can track through the shift.
        # Row 19 is full except for column 5.
        g = grid_from(
            ["." * COLS] * 17
            + ["XX" + "." * (COLS - 2)]
            + ["." * COLS]
            + ["X" * 5 + "." + "X" * (COLS - 6)],
        )
        # "X"*5 + "." + "X"*4 == "XXXXX.XXXX": col 5 is the gap.
        res = _drop(g, [(0, 0)], 5, "X")
        self.assertIsNotNone(res)
        new_grid, _lh, cleared, y_final = res

        # The single cell falls freely down column 5 to y_try = 19 (the gap),
        # filling the last hole in the row below.
        self.assertEqual(y_final, FLOOR)
        self.assertEqual(cleared, 1)

        # The full row is removed; the marker that was on row 17 is now on
        # row 18 (shifted down by one), and a blank row is inserted on top.
        self.assertFalse(any_full_row(new_grid), "cleared row must be gone")
        self.assertEqual("".join(new_grid[18]), "XX" + "." * (COLS - 2))
        self.assertEqual("".join(new_grid[19]), "." * COLS)


class MultiLineClearTest(unittest.TestCase):
    def test_vertical_i_clears_two_lines(self):
        # Rows 18 and 19 are each full except column 5. Among the shapes in
        # this file only the vertical I fills four cells in one column, so it
        # is the only piece that can complete both rows in a single drop.
        g = grid_from(
            ["." * COLS] * 18
            + ["X" * 5 + "." + "X" * (COLS - 6)] * 2,
        )
        vertical_i = SHAPES["I"][1]  # [(2,0),(2,1),(2,2),(2,3)]
        res = _drop(g, vertical_i, 3, "I")
        self.assertIsNotNone(res)
        new_grid, _lh, cleared, y_final = res

        # Dropped at col 3, cells sit at cx = 5. The deepest fit is y_try = 16
        # (y_try = 17 would push cy = 20 >= ROWS). Rows 18 and 19 keep their
        # col-5 gaps until the piece fills them, so both become full.
        self.assertEqual(y_final, 16)
        self.assertEqual(cleared, 2)

        # Two lines are removed and two blanks are inserted at the top, so the
        # surviving piece cells (new_grid rows 16/17, col 5) shift DOWN two
        # rows and land on result rows 18 and 19.
        self.assertFalse(any_full_row(new_grid))
        self.assertEqual("".join(new_grid[16]), "." * COLS)
        self.assertEqual("".join(new_grid[17]), "." * COLS)
        self.assertEqual("".join(new_grid[18]), "....." + "I" + "....")
        self.assertEqual("".join(new_grid[19]), "....." + "I" + "....")


class HeuristicDeterminismTest(unittest.TestCase):
    def test_same_input_same_float_grid_untouched(self):
        g = grid_from(["." * COLS] * 18 + ["XXXXX.XXXX", "X" * COLS])
        before = copy.deepcopy(g)
        a = _heuristic(g, landing_height=3, cleared=1)
        b = _heuristic(g, landing_height=3, cleared=1)
        self.assertIsInstance(a, float)
        self.assertEqual(a, b, "deterministic: same args -> same float")
        self.assertEqual(g, before, "pure: no mutation of the evaluated board")


class HeuristicOrderingTest(unittest.TestCase):
    def test_covered_hole_scores_worse_than_same_board_without_it(self):
        # Both boards have a flat floor (row 19 full). The "holey" board adds a
        # floating full row at row 9, which covers rows 10..18 in every one of
        # the 10 columns: 10 * 9 = 90 empty cells hidden beneath a filled row.
        # Each such cell is one `hole` (empty below a filled cell in its
        # column). W_HOLES = -7.899 penalises holes, and this 90-hole term
        # dwarfs the accompanying +20 ctrans / -2 rtrans deltas, so the covered
        # board must score strictly worse. (Landing height / cleared are passed
        # equal so they cancel.)
        clean = grid_from(["." * COLS] * 19 + ["X" * COLS])
        holey = grid_from(["." * COLS] * 9
                          + ["X" * COLS]
                          + ["." * COLS] * 9
                          + ["X" * COLS])
        s_clean = _heuristic(clean, 0, 0)
        s_holey = _heuristic(holey, 0, 0)
        self.assertLess(s_holey, s_clean,
                        "90 covered holes must outrank a clean flat floor")

    def test_flat_surface_scores_better_than_jagged_same_cell_count(self):
        # Both boards hold exactly 10 filled cells, monotone (no holes, no
        # wells). FLAT stacks them as one full bottom row; JAGGED spreads them
        # as a 4/3/2/1 staircase. The only differing feature is rtrans:
        # a full row has 0 row transitions while each staircase row has 2
        # (X-run -> empty and empty -> right-wall), so JAGGED carries 2 extra
        # row transitions and W_RTRANS = -3.218 pushes it below FLAT.
        flat = grid_from(["." * COLS] * 19 + ["X" * COLS])
        jagged = grid_from(["." * COLS] * 16
                           + ["X" + "." * (COLS - 1)]
                           + ["XX" + "." * (COLS - 2)]
                           + ["XXX" + "." * (COLS - 3)]
                           + ["XXXX" + "." * (COLS - 4)])
        self.assertEqual(len(filled_cells(flat)), 10)
        self.assertEqual(len(filled_cells(jagged)), 10)
        self.assertGreater(_heuristic(flat, 0, 0),
                           _heuristic(jagged, 0, 0),
                           "flatter surface must beat a jagged skyline")

    def test_clearing_more_lines_scores_better(self):
        # _heuristic is linear in `cleared` with W_CLEAR = +3.418 > 0, so with
        # the identical board and landing height, more cleared lines must score
        # strictly higher -- the clear term is the only thing that changes.
        g = grid_from(["." * COLS] * 19 + ["X" * COLS])
        self.assertGreater(_heuristic(g, landing_height=0, cleared=2),
                           _heuristic(g, landing_height=0, cleared=1))


class RowTransitionIsolationTest(unittest.TestCase):
    def test_full_floor_beats_empty_board_via_row_transitions_only(self):
        # _heuristic does not expose its component counts, so isolate the
        # rtrans term with a differential pair whose OTHER features are equal:
        #
        #   EMPTY  all 20 rows blank.
        #   BOTTOM row 19 fully filled, rows 0..18 blank.
        #
        # Hand count, row transitions (walls count as filled):
        #   EMPTY  row [..........]:  left-wall->empty (1) at col 0, then the
        #          run stays empty, and empty->right-wall (1) at the end => 2
        #          per row * 20 rows = 40.
        #   BOTTOM rows 0..18 are blank => 2 each = 38; row 19 [XXXXXXXXXX]
        #          is one filled run from the left wall to the right wall, no
        #          transition at all => 38 total.
        #
        # Everything else is provably identical:
        #   ctrans: every column is "blank then maybe one filled cell at the
        #          bottom", i.e. exactly 2 transitions top-wall->blank and
        #          blank->filled/blank->bottom-wall => 20 in both.
        #   holes: 0 in both (monotone, nothing hangs above a gap).
        #   wells: heights are all-equal (0 vs 1) so no column is strictly
        #          lower than both neighbours (edges compare against ROWS,
        #          which is never < the neighbour) => 0 in both.
        #
        # So score(BOTTOM) - score(EMPTY) = W_RTRANS * (38 - 40) = +6.436.
        empty = grid_from(["." * COLS] * ROWS)
        bottom = grid_from(["." * COLS] * (ROWS - 1) + ["X" * COLS])
        s_empty = _heuristic(empty, 0, 0)
        s_bottom = _heuristic(bottom, 0, 0)
        self.assertEqual(round(s_bottom - s_empty, 3), 6.436,
                         "only the two saved row transitions differ")
        self.assertGreater(s_bottom, s_empty)


if __name__ == "__main__":
    unittest.main()
