"""Dot — arrow-key smoke test; one bright pixel you can drive around."""
from __future__ import annotations

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


COLORS = [
    (255, 240, 120),
    (120, 230, 255),
    (255, 130, 200),
    (140, 255, 160),
    (255, 200, 110),
]


class Dot(Program):
    DESCRIPTION = "Smoke test — arrow-key-driven pixel"

    def setup(self) -> None:
        self._x = WIDTH // 2
        self._y = HEIGHT // 2
        self._color = 0
        self._trail: list[tuple[int, int, int]] = []  # (x, y, age_frames)

    def update(self, dt: float, events) -> None:
        moved = False
        for ev in events:
            if ev.kind != "key":
                continue
            if ev.key == "up":
                self._y = max(0, self._y - 1); moved = True
            elif ev.key == "down":
                self._y = min(HEIGHT - 1, self._y + 1); moved = True
            elif ev.key == "left":
                self._x = max(0, self._x - 1); moved = True
            elif ev.key == "right":
                self._x = min(WIDTH - 1, self._x + 1); moved = True
            elif ev.key == "space":
                self._color = (self._color + 1) % len(COLORS)
        if moved:
            self._trail.append((self._x, self._y, 0))
            if len(self._trail) > 32:
                self._trail.pop(0)
        self._trail = [(x, y, age + 1) for x, y, age in self._trail]

    def render(self) -> Frame:
        f = Frame.black()
        col = COLORS[self._color]
        for x, y, age in self._trail:
            t = max(0, 32 - age) / 32.0
            f.set(x, y, (int(col[0] * t * 0.45),
                        int(col[1] * t * 0.45),
                        int(col[2] * t * 0.45)))
        f.set(self._x, self._y, col)
        return f
