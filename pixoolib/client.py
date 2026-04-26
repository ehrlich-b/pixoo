"""HTTP client for the Pixoo-64 /post endpoint."""
from __future__ import annotations

import base64
import json
import urllib.request

PROBE_TIMEOUT = 0.6
CMD_TIMEOUT = 3.0


class PixooClient:
    def __init__(self, ip: str):
        self.ip = ip

    def post(self, payload: dict, timeout: float = CMD_TIMEOUT) -> dict:
        req = urllib.request.Request(
            f"http://{self.ip}/post",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

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
