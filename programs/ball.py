"""Bouncing ball — 45 degree velocity, reflects off all 4 edges."""
from __future__ import annotations

from pixoolib.frame import Frame, HEIGHT, WIDTH
from pixoolib.runtime import Program


class Ball(Program):
    speed = 20.0  # px/sec on each axis → 45 degrees

    def setup(self) -> None:
        # middle of the left edge, heading down-right → traces a diamond
        # that kisses the middle of each edge in turn.
        self.x, self.y = 0.0, 32.0
        self.vx, self.vy = self.speed, self.speed

    def update(self, dt: float, events) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.x <= 0:
            self.x = 0
            self.vx = abs(self.vx)
        elif self.x >= WIDTH - 1:
            self.x = WIDTH - 1
            self.vx = -abs(self.vx)
        if self.y <= 0:
            self.y = 0
            self.vy = abs(self.vy)
        elif self.y >= HEIGHT - 1:
            self.y = HEIGHT - 1
            self.vy = -abs(self.vy)

    def render(self) -> Frame:
        f = Frame.black()
        cx, cy = self.x, self.y
        r2 = 2.5 * 2.5
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                px, py = int(cx) + dx, int(cy) + dy
                d2 = (px - cx) ** 2 + (py - cy) ** 2
                if d2 <= r2:
                    f.set(px, py, (255, 255, 255))
                elif d2 <= r2 + 2.5:
                    f.set(px, py, (90, 90, 90))
        return f
