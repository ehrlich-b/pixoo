"""Single-step Langton's ant behaviour, pinned to programs/langton.py.

Rule under test (programs/langton.py lines 43-56): if the ant's current cell
is ON (cells[i] == 1), turn LEFT (adir = (adir - 1) % 4) and flip the cell
OFF; if it is OFF, turn RIGHT (adir = (adir + 1) % 4) and flip the cell ON.
The turn always happens BEFORE the move. Edges wrap with plain `%`: an ant
stepping off any edge reappears on the opposite side.
"""
import unittest

from programs.langton import DX, DY, HEIGHT, WIDTH, Langton

# Direction indices (line 18): 0=up 1=right 2=down 3=left.
# Move vectors (lines 19-20):        up        right       down        left
#   DX = (0, 1, 0, -1); DY = (-1, 0, 1, 0)


class TestLangton(unittest.TestCase):
    def test_fresh_grid_single_step_turns_right_flips_on(self):
        l = Langton()
        l.setup()
        l._advance(1)
        # Off cell -> turn right 0->1, flip ON, step DX[1], DY[1] = +1, 0.
        self.assertEqual((l.ax, l.ay, l.adir), (33, 32, 1))
        self.assertEqual(l.cells[32 * 64 + 32], 1, "start cell flipped on")
        self.assertEqual(l.steps, 1)

    def test_on_cell_turns_left_flips_off(self):
        l = Langton()
        l.setup()
        l.cells[l.ay * 64 + l.ax] = 1
        l._advance(1)
        # On cell -> turn left 0->3, flip OFF, step DX[3], DY[3] = -1, 0.
        self.assertEqual((l.ax, l.ay, l.adir), (31, 32, 3))
        self.assertEqual(l.cells[32 * 64 + 32], 0, "start cell flipped back off")
        self.assertEqual(l.steps, 1)

    def test_left_edge_wraps(self):
        # Left-edge wrap: start (ax=0, ay=5, adir=2) on a fresh (all-off) grid.
        # Off-cell turn right (2+1)%4=3, move DX[3],DY[3] = -1,0:
        #   (0-1) % 64 == 63. Result: (ax, ay, adir) == (63, 5, 3).
        l = Langton()
        l.setup()
        l.ax, l.ay, l.adir = 0, 5, 2
        l._advance(1)
        self.assertEqual((l.ax, l.ay, l.adir), (63, 5, 3))

    def test_right_edge_wraps(self):
        # Right-edge wrap: start (ax=63, ay=5, adir=0) on a fresh grid.
        # Off-cell turn right (0+1)%4=1, move DX[1],DY[1] = 1,0:
        #   (63+1) % 64 == 0. Result: (ax, ay, adir) == (0, 5, 1).
        l = Langton()
        l.setup()
        l.ax, l.ay, l.adir = 63, 5, 0
        l._advance(1)
        self.assertEqual((l.ax, l.ay, l.adir), (0, 5, 1))

    def test_top_edge_wraps(self):
        # Top-edge wrap: start (ax=5, ay=0, adir=3) on a fresh grid.
        # Off-cell turn right (3+1)%4=0, move DX[0],DY[0] = 0,-1:
        #   (0-1) % 64 == 63. Result: (ax, ay, adir) == (5, 63, 0).
        l = Langton()
        l.setup()
        l.ax, l.ay, l.adir = 5, 0, 3
        l._advance(1)
        self.assertEqual((l.ax, l.ay, l.adir), (5, 63, 0))

    def test_bottom_edge_wraps(self):
        # Bottom-edge wrap: start (ax=5, ay=63, adir=1) on a fresh grid.
        # Off-cell turn right (1+1)%4=2 (down), move DX[2],DY[2] = 0,1:
        #   (63+1) % 64 == 0. Result: (ax, ay, adir) == (5, 0, 2).
        l = Langton()
        l.setup()
        l.ax, l.ay, l.adir = 5, 63, 1
        l._advance(1)
        self.assertEqual((l.ax, l.ay, l.adir), (5, 0, 2))

    def test_multi_step_determinism(self):
        a = Langton()
        a.setup()
        b = Langton()
        b.setup()
        a._advance(500)
        b._advance(500)
        self.assertEqual(a.cells, b.cells, "cells identical across two runs")
        self.assertEqual((a.ax, a.ay, a.adir), (b.ax, b.ay, b.adir))

    def test_toggle_count_never_exceeds_steps(self):
        l = Langton()
        l.setup()
        # Each step toggles at most one previously-off cell to on; toggling an
        # on cell to off never increases the count. So on-cells <= steps.
        for _ in range(300):
            l._advance(1)
            self.assertLessEqual(sum(l.cells), l.steps)
        self.assertEqual(l.steps, 300)


if __name__ == "__main__":
    unittest.main()
