"""TerminalDriver.render() — pure buffer-to-ANSI encoder, stdlib unittest.

render() never touches a real TTY; only start()/stop() do (termios/isatty),
and this task never calls those. Sedentary behavior pinned here:

- 64x64 source pixels map to 32 terminal rows x 64 columns. Each cell is a
  U+2580 half-block where the FOREGROUND color is the TOP source pixel
  (source y = row*2) and the BACKGROUND color is the BOTTOM source pixel
  (source y = row*2 + 1).
- Output always starts with CURSOR_HOME.
- Run-length optimization: an ANSI truecolor escape is emitted only when the
  (top, bottom) color pair differs from the PREVIOUS cell in the same row.
- No cross-row memory: the pair is reset to None at the start of every row,
  so the FIRST cell of every row always gets a fresh escape.
- Each row ends with RESET + "\n".
"""
from __future__ import annotations

import contextlib
import io
import re
import unittest

from pixoolib.frame import Frame
from pixoolib.term import CURSOR_HOME, RESET, TerminalDriver

RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 128, 0)

TRUE_COLOR_ESCAPE = r"\x1b\[38;2;"


def render_terminal(frame: Frame) -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        TerminalDriver().render(frame)
    return out.getvalue()


def escape_count(output: str) -> int:
    return len(re.findall(TRUE_COLOR_ESCAPE, output))


class RenderPrefixTest(unittest.TestCase):
    def test_output_starts_with_cursor_home(self):
        out = render_terminal(Frame.black())
        self.assertTrue(out.startswith(CURSOR_HOME))

    def test_all_black_frame_emits_exactly_one_escape_per_row(self):
        out = render_terminal(Frame.black())
        # All 64 source pixels are black, so every cell's (top, bottom) pair
        # is (black, black). Within a row that pair never changes, so a row
        # emits exactly ONE escape: the mandatory fresh one for its first
        # cell. There is no cross-row memory (last pair resets to None at the
        # start of each row), so the first cell of every row re-emits even
        # though it matches the last cell of the previous row. 32 rows -> 32
        # escapes total. If rows had cross-row memory, row 1..31 would each
        # skip their first escape and the count would be 1 (for row 0).
        self.assertEqual(escape_count(out), 32)

    def test_known_trace_exact_prefix(self):
        # Verified concrete trace: set top-left to red, top-right-of-it to
        # red, and the pixel directly below the top-left to green.
        f = Frame.black()
        f.set(0, 0, RED)      # top pixel of cell (row 0, col 0)
        f.set(1, 0, RED)      # top pixel of cell (row 0, col 1)
        f.set(0, 1, GREEN)    # bottom pixel of cell (row 0, col 0)
        out = render_terminal(f)
        # cell 0 (top red, bottom green) -> own escape + glyph
        # cell 1 (top red, bottom black, differs from cell 0) -> new escape
        # cell 2 on (top black, bottom black) -> one more escape, then plain
        # glyphs with no further escapes for the rest of row 0.
        prefix = (
            CURSOR_HOME
            + "\x1b[38;2;255;0;0;48;2;0;255;0m\u2580"
            + "\x1b[38;2;255;0;0;48;2;0;0;0m\u2580"
            + "\x1b[38;2;0;0;0;48;2;0;0;0m\u2580"
            + "\u2580\u2580\u2580"
        )
        self.assertTrue(out.startswith(prefix))

    def test_escape_count_matches_hand_model(self):
        # Hand-designed pattern covering all 32 rows uniformly. Fill 3 column
        # blocks across the full 64-pixel height:
        #   cols   0-15 -> top & bottom RED    (pair RR)
        #   cols  16-31 -> top & bottom GREEN  (pair GG)
        #   cols  32-63 -> top & bottom RED    (pair RR)
        # Per row the pair sequence is RR x16, GG x16, RR x32. Escape count
        # per row = 1 (mandatory fresh escape for cell 0, since the reset
        # gives it no memory of the previous row) + 1 (pair changes RR->GG at
        # col 16) + 1 (pair changes GG->RR at col 32) = 3. The 32 identical
        # cells within each block coalesce into that single transition escape.
        # 32 rows -> 32 * 3 = 96 escapes total.
        f = Frame.black()
        f.fill_rect(0, 0, 16, 64, RED)
        f.fill_rect(16, 0, 16, 64, GREEN)
        f.fill_rect(32, 0, 32, 64, RED)
        out = render_terminal(f)
        self.assertEqual(escape_count(out), 96)
        # sanity: the repeat-heavy blocks also exercise run-length coalescing
        # (16 identical cells share one escape, proven by the count above).


class RenderStructureTest(unittest.TestCase):
    def test_row_and_glyph_counts(self):
        f = Frame.black()
        f.fill_rect(5, 5, 10, 10, ORANGE)
        f.fill_rect(40, 40, 20, 20, BLUE)
        out = render_terminal(f)
        self.assertEqual(out.count(RESET + "\n"), 32)
        self.assertEqual(out.count("\u2580"), 32 * 64)

    def test_first_cell_of_every_row_gets_fresh_escape(self):
        # Cross-row independence, deliberately. The LAST cell of row 0 is
        # source pixels (col 63, y 0) / (col 63, y 1); the FIRST cell of row
        # 1 is source pixels (col 0, y 2) / (col 0, y 3). A solid frame makes
        # both cells the SAME (top, bottom) pair. Even so, because the render
        # loop resets last_t/last_b to None at the start of each row, row 1's
        # first cell must emit a fresh escape rather than coalesce with the
        # end of row 0. That is invisible in the visual output (same colors),
        # so assert the byte stream directly: the run of row 1 starts with a
        # new escape sequence right after row 0's RESET+"\n". With cross-row
        # memory this would start with a bare half-block and the assertion
        # fails.
        f = Frame.black()
        f.clear(ORANGE)
        out = render_terminal(f)
        row0_end = RESET + "\n"
        idx = out.index(row0_end)  # end of row 0 (and of every row)
        row1 = out[idx + len(row0_end):]
        self.assertTrue(row1.startswith("\x1b[38;2;255;128;0;48;2;255;128;0m"))


if __name__ == "__main__":
    unittest.main()
