"""HTTP client for the Pixoo-64 /post endpoint."""
from __future__ import annotations

import base64
import json
import urllib.request

PROBE_TIMEOUT = 0.6
CMD_TIMEOUT = 3.0

# PROTOCOL.md, "Per-request size limits": "never send more than ~16KB in one
# POST." One 64x64 RGB frame is exactly 16384 base64 chars; the JSON envelope
# brings a single-frame body to ~16.5KB on the wire. This constant is that
# one-frame ceiling with room for the envelope — anything larger is a packed
# multi-frame body (the documented "crashes past ~16KB" case) and is refused
# client-side, before the fetch path.
MAX_POST_BYTES = 16 * 1024 + 512  # ~16.5KB: one frame + JSON envelope


class PixooProtocolError(Exception):
    """Raised when a request violates the Pixoo protocol (see PROTOCOL.md)."""


def _urllib_post(url: str, body: bytes, timeout: float) -> dict:
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


class PixooClient:
    def __init__(self, ip: str, poster=None):
        """Poster is the HTTP transport: `poster(url, body_bytes, timeout) -> dict`.

        Defaults to the urllib path; tests substitute a FakeDevice.
        """
        self.ip = ip
        self._poster = _urllib_post if poster is None else poster

    def post(self, payload: dict, timeout: float = CMD_TIMEOUT) -> dict:
        body = json.dumps(payload).encode()
        if len(body) > MAX_POST_BYTES:
            raise PixooProtocolError(
                f"refusing to send {len(body)}-byte body: PROTOCOL.md caps a "
                f"POST at ~16KB (one 64x64 RGB frame is 16384 base64 chars); "
                f"this request was not sent"
            )
        return self._poster(f"http://{self.ip}/post", body, timeout)

    def channel_index(self) -> dict:
        return self.post({"Command": "Channel/GetIndex"}, timeout=PROBE_TIMEOUT)

    def all_conf(self) -> dict:
        return self.post({"Command": "Channel/GetAllConf"})

    def weather_info(self) -> dict:
        return self.post({"Command": "Device/GetWeatherInfo"})

    def device_time(self) -> dict:
        return self.post({"Command": "Device/GetDeviceTime"})

    def set_channel(self, idx: int) -> dict:
        return self.post({"Command": "Channel/SetIndex", "SelectIndex": idx})

    def set_brightness(self, v: int) -> dict:
        return self.post({"Command": "Channel/SetBrightness", "Brightness": v})

    def text(self, s: str, *, color: str = "#FFFFFF", x: int = 0, y: int = 28,
             speed: int = 10, width: int = 64, direction: int = 0,
             font: int = 4, align: int = 1, text_id: int = 4) -> dict:
        return self.post({
            "Command": "Draw/SendHttpText",
            "TextId": text_id,
            "x": x, "y": y,
            "dir": direction,
            "font": font,
            "TextWidth": width,
            "speed": speed,
            "TextString": s,
            "color": color,
            "align": align,
        })

    def clear_text(self) -> dict:
        return self.post({"Command": "Draw/ClearHttpText"})

    def reset_gif_id(self) -> dict:
        return self.post({"Command": "Draw/ResetHttpGifId"})

    def prime(self) -> dict:
        """Channel 3 + reset + black frame so overlays will render."""
        self.set_channel(3)
        self.reset_gif_id()
        black = base64.b64encode(bytes(64 * 64 * 3)).decode()
        return self.post({
            "Command": "Draw/SendHttpGif",
            "PicNum": 1, "PicWidth": 64, "PicOffset": 0,
            "PicID": 1, "PicSpeed": 100, "PicData": black,
        })
