"""Unit tests for pixoolib.frame and pixoolib.digits. Stdlib unittest only."""
import base64
import unittest

from pixoolib.frame import Frame
from pixoolib import digits


class TestSetGet(unittest.TestCase):
    def test_round_trip(self):
        cases = [
            ((0, 0), (255, 0, 0)),
            ((63, 0), (0, 255, 0)),
            ((0, 63), (0, 0, 255)),
            ((63, 63), (255, 255, 255)),
            ((32, 32), (7, 130, 200)),
            ((17, 5), (0, 0, 0)),
        ]
        for (x, y), rgb in cases:
            f = Frame()
            f.set(x, y, rgb)
            self.assertEqual(f.get(x, y), rgb)


class TestByteLayout(unittest.TestCase):
    def test_offset_is_row_major_3_bytes_per_pixel(self):
        cases = [
            ((0, 0), (255, 0, 0)),
            ((63, 0), (0, 255, 0)),
            ((0, 63), (0, 0, 255)),
            ((63, 63), (12, 34, 56)),
            ((32, 13), (200, 100, 50)),
        ]
        for (x, y), rgb in cases:
            f = Frame()
            f.set(x, y, rgb)
            # Hand-derived: flat row-major buffer, 64 px per row, 3 bytes per px.
            off = (y * 64 + x) * 3
            self.assertEqual(bytes(f.pixels[off:off + 3]), bytes(rgb))


class TestBase64(unittest.TestCase):
    def test_black_frame_round_trips(self):
        f = Frame.black()
        decoded = base64.b64decode(f.to_base64())
        self.assertEqual(decoded, bytes(f.pixels))
        self.assertEqual(len(decoded), 12288)

    def test_pixels_frame_round_trips(self):
        f = Frame.black()
        for (x, y), rgb in [
            ((0, 0), (255, 0, 0)),
            ((63, 0), (0, 255, 0)),
            ((0, 63), (0, 0, 255)),
            ((63, 63), (255, 255, 255)),
            ((32, 32), (7, 130, 200)),
        ]:
            f.set(x, y, rgb)
        decoded = base64.b64decode(f.to_base64())
        self.assertEqual(decoded, bytes(f.pixels))
        self.assertEqual(len(decoded), 12288)


class TestFillRectDifferential(unittest.TestCase):
    """fill_rect must equal a naive per-pixel set() loop over the same rect."""

    def _assert_matches_set_loop(self, x, y, w, h, rgb):
        a = Frame.black()
        b = Frame.black()
        a.fill_rect(x, y, w, h, rgb)
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                b.set(xx, yy, rgb)
        self.assertEqual(a.pixels, b.pixels)

    def test_fully_inside(self):
        self._assert_matches_set_loop(5, 5, 10, 10, (255, 0, 0))

    def test_hangs_off_right_edge(self):
        self._assert_matches_set_loop(60, 5, 10, 5, (0, 255, 0))

    def test_hangs_off_bottom_edge(self):
        self._assert_matches_set_loop(5, 60, 5, 10, (0, 0, 255))

    def test_negative_origin(self):
        self._assert_matches_set_loop(-5, -5, 10, 10, (255, 255, 0))

    def test_larger_than_whole_frame(self):
        self._assert_matches_set_loop(-10, -10, 100, 100, (1, 2, 3))


class TestClear(unittest.TestCase):
    def test_clear_rgb_fills_every_pixel(self):
        f = Frame()
        f.clear((7, 130, 200))
        self.assertEqual(bytes(f.pixels), bytes((7, 130, 200)) * 4096)

    def test_clear_defaults_to_zero(self):
        f = Frame()
        f.clear()
        self.assertEqual(bytes(f.pixels), b"\x00" * 12288)

    def test_clear_equals_full_frame_rect(self):
        rgb = (9, 87, 210)
        a = Frame()
        b = Frame()
        a.clear(rgb)
        b.fill_rect(0, 0, 64, 64, rgb)
        self.assertEqual(a.pixels, b.pixels)


class TestBlack(unittest.TestCase):
    def test_black_is_all_zeros(self):
        self.assertEqual(bytes(Frame.black().pixels), b"\x00" * 12288)

    def test_black_returns_independent_frames(self):
        a = Frame.black()
        b = Frame.black()
        a.set(0, 0, (255, 255, 255))
        self.assertEqual(a.get(0, 0), (255, 255, 255))
        self.assertEqual(bytes(b.pixels), b"\x00" * 12288)


class TestBoundsAsymmetry(unittest.TestCase):
    """set() bounds-checks and silently drops; get() does not bounds-check."""

    def test_set_out_of_bounds_is_noop_no_raise(self):
        f = Frame()
        f.set(10, 10, (1, 2, 3))
        before = bytes(f.pixels)
        for x, y in [(-1, 0), (64, 0), (0, 64), (-1, -1), (64, 64), (0, -1)]:
            f.set(x, y, (255, 0, 0))
        self.assertEqual(bytes(f.pixels), before)
        self.assertEqual(f.get(10, 10), (1, 2, 3))

    def test_get_negative_coordinate_does_not_raise(self):
        f = Frame.black()
        f.set(63, 62, (3, 4, 5))
        # ASYMMETRY: get() never checks bounds, so a negative coordinate is
        # folded straight into the offset arithmetic and reads real bytes from
        # elsewhere in the buffer. (63*64 - 1)*3 == (62*64 + 63)*3 == 12093,
        # so get(-1, 63) reads the same bytes as the valid pixel (63, 62).
        self.assertEqual(f.get(-1, 63), (3, 4, 5))
        self.assertEqual(f.get(-1, 63), f.get(63, 62))
        # (0, -1) lands on negative Python indexing from the buffer end:
        # (-1*64 + 0)*3 == -192 == (0*64 + 63)*3 - 12288, i.e. pixel (0, 63).
        f.set(0, 63, (6, 7, 8))
        self.assertEqual(f.get(0, -1), (6, 7, 8))
        self.assertEqual(f.get(0, -1), f.get(0, 63))


class TestDigits(unittest.TestCase):
    def test_text_width_empty_is_zero(self):
        self.assertEqual(digits.text_width(""), 0)

    def test_text_width_grows_monotonically(self):
        widths = [digits.text_width(""), digits.text_width("1"),
                  digits.text_width("12"), digits.text_width("123"),
                  digits.text_width("1234")]
        for prev, cur in zip(widths, widths[1:]):
            self.assertGreater(cur, prev)

    def test_draw_text_marks_pixels(self):
        f = Frame.black()
        nx = digits.draw_text(f, "12", 0, 0, (255, 255, 255))
        self.assertEqual(nx, 10)
        lit = sum(1 for i in range(0, len(f.pixels), 3) if f.pixels[i] != 0)
        self.assertGreater(lit, 0)
        self.assertEqual(f.get(1, 1), (255, 255, 255))

    def test_draw_text_empty_is_noop(self):
        f = Frame.black()
        nx = digits.draw_text(f, "", 0, 0, (255, 0, 0))
        self.assertEqual(nx, 0)
        self.assertEqual(bytes(f.pixels), b"\x00" * 12288)

    def test_draw_text_out_of_bounds_does_not_raise(self):
        f = Frame.black()
        digits.draw_text(f, "88", 200, 0, (1, 2, 3))
        digits.draw_text(f, "88", 0, 200, (1, 2, 3))
        digits.draw_text(f, "88", -100, -100, (1, 2, 3))
        self.assertEqual(bytes(f.pixels), b"\x00" * 12288)


if __name__ == "__main__":
    unittest.main()
