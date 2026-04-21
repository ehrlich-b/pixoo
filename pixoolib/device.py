"""PixooDriver — rate-limited HTTP frame pusher."""
from __future__ import annotations

import base64
import time

from .client import PixooClient
from .frame import Frame
from .runtime import Event


class PixooDriver:
    def __init__(self, client: PixooClient, fps: float = 12.0):
        self.client = client
        self.min_dt = 1.0 / fps
        self._last_push = 0.0
        self._pic_id = 1

    def start(self) -> None:
        self.client.set_channel(3)
        self.client.reset_gif_id()
        self._pic_id = 1

    def stop(self) -> None:
        pass

    def render(self, frame: Frame) -> None:
        now = time.monotonic()
        if now - self._last_push < self.min_dt:
            return
        self._last_push = now
        data = base64.b64encode(bytes(frame.pixels)).decode()
        try:
            self.client.post({
                "Command": "Draw/SendHttpGif",
                "PicNum": 1, "PicWidth": 64, "PicOffset": 0,
                "PicID": self._pic_id, "PicSpeed": 100, "PicData": data,
            })
        except Exception:
            pass  # drop frame on transient network hiccup
        self._pic_id += 1

    def events(self) -> list[Event]:
        return []
