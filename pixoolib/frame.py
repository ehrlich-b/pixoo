"""Frame — 64x64 RGB buffer, stdlib only."""
from __future__ import annotations

import base64

RGB = tuple[int, int, int]
WIDTH = 64
HEIGHT = 64


class Frame:
    __slots__ = ("pixels",)

    def __init__(self) -> None:
        self.pixels = bytearray(WIDTH * HEIGHT * 3)

    def set(self, x: int, y: int, rgb: RGB) -> None:
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            i = (y * WIDTH + x) * 3
            self.pixels[i] = rgb[0]
            self.pixels[i + 1] = rgb[1]
            self.pixels[i + 2] = rgb[2]

    def get(self, x: int, y: int) -> RGB:
        i = (y * WIDTH + x) * 3
        return (self.pixels[i], self.pixels[i + 1], self.pixels[i + 2])

    def clear(self, rgb: RGB = (0, 0, 0)) -> None:
        self.pixels[:] = bytes(rgb) * (WIDTH * HEIGHT)

    def fill_rect(self, x: int, y: int, w: int, h: int, rgb: RGB) -> None:
        for yy in range(max(0, y), min(HEIGHT, y + h)):
            for xx in range(max(0, x), min(WIDTH, x + w)):
                self.set(xx, yy, rgb)

    def to_base64(self) -> str:
        return base64.b64encode(bytes(self.pixels)).decode()

    @classmethod
    def black(cls) -> "Frame":
        return cls()
