"""Protocol behavior pinned to PROTOCOL.md, stdlib unittest only.

No hardware, no network: every PixooClient gets a FakeDevice poster.
"""
from __future__ import annotations

import base64
import unittest

from pixoolib.anim import upload_animation
from pixoolib.client import MAX_POST_BYTES, PixooClient, PixooProtocolError
from pixoolib.frame import Frame

from tests.fake_device import FakeDevice

IP = "192.0.2.9"
URL = f"http://{IP}/post"
FRAME_B64 = 64 * 64 * 3 // 3 * 4  # 16384 base64 chars per 64x64 RGB frame


def _frame_payload(**overrides) -> dict:
    payload = {
        "Command": "Draw/SendHttpGif",
        "PicNum": 1,
        "PicWidth": 64,
        "PicOffset": 0,
        "PicID": 1,
        "PicSpeed": 100,
        "PicData": base64.b64encode(bytes(64 * 64 * 3)).decode(),
    }
    payload.update(overrides)
    return payload


class UploadAnimationTest(unittest.TestCase):
    def test_n_frames_n_posts_shared_picid_ordered_offsets_picnum_n(self):
        dev = FakeDevice()
        c = PixooClient(IP, poster=dev)
        n = 4
        frames = [Frame.black() for _ in range(n)]
        upload_animation(c, frames, speed_ms=100, pic_id=100)

        self.assertEqual(dev.post_count, n)
        for i in range(n):
            req = dev.requests[i]
            self.assertEqual(req["url"], URL)
            self.assertEqual(req["order"], i)  # sent in upload order
            p = req["payload"]
            self.assertEqual(p["Command"], "Draw/SendHttpGif")
            self.assertEqual(p["PicID"], 100, "same PicID on every POST")
            self.assertEqual(p["PicNum"], n, "PicNum is the total frame count")
            self.assertEqual(p["PicOffset"], i, "offsets run 0..N-1 in order")
            self.assertEqual(len(p["PicData"]), FRAME_B64,
                             "one 64x64 RGB frame of base64 per POST")
            self.assertEqual(len(base64.b64decode(p["PicData"])), 64 * 64 * 3)


class PrimeTest(unittest.TestCase):
    def test_prime_setindex_then_reset_then_black_frame(self):
        dev = FakeDevice()
        c = PixooClient(IP, poster=dev)
        c.prime()

        self.assertEqual(dev.commands, [
            "Channel/SetIndex",
            "Draw/ResetHttpGifId",
            "Draw/SendHttpGif",
        ])
        self.assertEqual(dev.payload_at(0)["SelectIndex"], 3,
                         "prime switches to channel 3 (custom/HTTP)")
        self.assertEqual(dev.payload_at(2)["PicData"],
                         base64.b64encode(bytes(64 * 64 * 3)).decode(),
                         "prime ends with a black frame")
        self.assertEqual(len(dev.payload_at(2)["PicData"]), FRAME_B64)


class SizeGuardTest(unittest.TestCase):
    def test_single_frame_body_is_sent(self):
        dev = FakeDevice()
        c = PixooClient(IP, poster=dev)
        c.post(_frame_payload())
        self.assertEqual(dev.post_count, 1)

    def test_oversize_body_raises_clear_error_and_is_not_sent(self):
        dev = FakeDevice()
        c = PixooClient(IP, poster=dev)
        packed = _frame_payload(
            PicNum=2,
            PicData="A" * (MAX_POST_BYTES + 1),  # two frames rammed into one body
        )
        with self.assertRaises(PixooProtocolError) as ctx:
            c.post(packed)
        msg = str(ctx.exception)
        self.assertIn("PROTOCOL.md", msg, "error cites the spec's size ceiling")
        self.assertIn("16KB", msg, "error names the ~16KB ceiling")
        self.assertEqual(dev.post_count, 0, "oversize request must never be sent")

    def test_oversize_body_raises_for_non_animation_commands_too(self):
        dev = FakeDevice()
        c = PixooClient(IP, poster=dev)
        with self.assertRaises(PixooProtocolError):
            c.post({"Command": "Draw/SendHttpText", "TextString": "x" * (MAX_POST_BYTES + 1)})
        self.assertEqual(dev.post_count, 0)


if __name__ == "__main__":
    unittest.main()
