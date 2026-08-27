"""PixooDriver throttling, PicID cycling, and exception swallowing.

Stdlib unittest only, matching tests/test_protocol.py. No hardware, no
network, no wall clock: every timestamp comes from a mocked
``time.monotonic`` and every push goes to a recording FakeClient.
"""
from __future__ import annotations

import base64
import unittest
from unittest.mock import patch

from pixoolib.device import PixooDriver
from pixoolib.frame import Frame


class FakeClient:
    """Records calls; optionally raises from post, mimicking a network hiccup."""

    def __init__(self, raise_on_post: bool = False):
        self.calls: list[tuple] = []
        self.raise_on_post = raise_on_post

    def set_channel(self, n: int) -> None:
        self.calls.append(("set_channel", n))

    def reset_gif_id(self) -> None:
        self.calls.append(("reset_gif_id",))

    def post(self, payload: dict) -> None:
        self.calls.append(("post", payload))
        if self.raise_on_post:
            raise RuntimeError("network hiccup")


def _post_payloads(client: FakeClient) -> list[dict]:
    return [rec[1] for rec in client.calls if rec[0] == "post"]


class PixooDriverStartTest(unittest.TestCase):
    def test_start_primes_channel_and_resets_pic_id(self):
        fc = FakeClient()
        d = PixooDriver(fc)
        d.start()
        self.assertEqual(fc.calls, [("set_channel", 3), ("reset_gif_id",)])
        self.assertEqual(d._pic_id, 1)


class PixooDriverThrottleTest(unittest.TestCase):
    def test_throttle_trace_matches_context(self):
        fc = FakeClient()
        d = PixooDriver(fc, fps=10.0)  # min_dt = 0.1
        frame = Frame.black()
        # 0.0 no-op, 0.05 no-op, 0.2 push, 0.25 no-op (verified trace)
        timestamps = [0.0, 0.05, 0.2, 0.25]
        expected = [
            (0, 1),  # render 1: 0.0 - 0.0 = 0.0 < 0.1 -> no-op
            (0, 1),  # render 2: 0.05 - 0.0 = 0.05 < 0.1 -> no-op
            (1, 2),  # render 3: 0.2 - 0.0 = 0.2 >= 0.1 -> push PicID 1
            (1, 2),  # render 4: 0.25 - 0.2 = 0.05 < 0.1 -> no-op
        ]
        with patch("pixoolib.device.time.monotonic", side_effect=timestamps):
            for i, (n_posts, pic_id) in enumerate(expected):
                d.render(frame)
                self.assertEqual(len(_post_payloads(fc)), n_posts,
                                 f"post count after render {i + 1}")
                self.assertEqual(d._pic_id, pic_id,
                                 f"_pic_id after render {i + 1}")
        self.assertEqual(len(_post_payloads(fc)), 1,
                         "only the throttle-passing render pushes")

    def test_picid_increments_per_push_not_per_call(self):
        fc = FakeClient()
        d = PixooDriver(fc, fps=10.0)  # min_dt = 0.1
        frame = Frame.black()
        # 0.0 no-op; 0.5 push (PicID 1); 0.55 no-op; 1.0 push (PicID 2);
        # 1.5 push (PicID 3) — three pushes, five renders, throttled in between
        # (deltas of 0.5 are safely above min_dt to dodge float roundoff)
        timestamps = [0.0, 0.5, 0.55, 1.0, 1.5]
        with patch("pixoolib.device.time.monotonic", side_effect=timestamps):
            for _ in timestamps:
                d.render(frame)
        payloads = _post_payloads(fc)
        self.assertEqual([p["PicID"] for p in payloads], [1, 2, 3],
                         "PicID advances by exactly 1 per push, no skips")
        self.assertEqual(d._pic_id, 4, "next push would use PicID 4")

    def test_boundary_equality_is_inclusive_push(self):
        fc = FakeClient()
        d = PixooDriver(fc, fps=10.0)  # min_dt = 0.1
        frame = Frame.black()
        # now - last_push == 0.1 exactly; skip condition is a strict `<`
        # (device.py:31 `if now - self._last_push < self.min_dt:`), so
        # equality does NOT skip -> this renders pushes.
        with patch("pixoolib.device.time.monotonic", side_effect=[0.1]):
            d.render(frame)
        payloads = _post_payloads(fc)
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["PicID"], 1)

    def test_exception_swallow_still_consumes_a_picid(self):
        fc = FakeClient(raise_on_post=True)
        d = PixooDriver(fc, fps=10.0)  # min_dt = 0.1
        frame = Frame.black()
        # 0.0 no-op; 1.0 push (raises, _pic_id -> 2); 1.0 no-op (still
        # throttled to last_push=1.0); 2.0 push (raises, _pic_id -> 3)
        timestamps = [0.0, 1.0, 1.0, 2.0]
        with patch("pixoolib.device.time.monotonic", side_effect=timestamps):
            for _ in timestamps:
                d.render(frame)  # must never raise to the caller
        self.assertEqual(d._pic_id, 3)
        self.assertEqual(len(_post_payloads(fc)), 2,
                         "both throttle-passing frames reached client.post")

    def test_payload_shape_matches_frame_pixels(self):
        fc = FakeClient()
        d = PixooDriver(fc, fps=10.0)
        frame = Frame.black()
        frame.set(10, 10, (1, 2, 3))
        frame.set(63, 63, (255, 255, 255))
        with patch("pixoolib.device.time.monotonic", side_effect=[0.2]):
            d.render(frame)
        payload = _post_payloads(fc)[0]
        self.assertEqual(base64.b64decode(payload["PicData"]),
                         bytes(frame.pixels),
                         "PicData decodes back to the exact frame bytes")
        self.assertEqual(payload["Command"], "Draw/SendHttpGif")
        self.assertEqual(payload["PicWidth"], 64)
        self.assertEqual(payload["PicID"], 1)


if __name__ == "__main__":
    unittest.main()
