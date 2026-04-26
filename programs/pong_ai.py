"""Pong AI vs AI — two anticipating paddles play forever."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


PADDLE_H = 12
PADDLE_W = 1
LEFT_X = 2
RIGHT_X = WIDTH - 3
BALL_SPEED = 22.0
PADDLE_SPEED = 26.0
BG_LINE = (40, 50, 70)


def _serve(direction: int) -> tuple[float, float, float, float]:
    """Place ball mid-screen with a small random vertical drift."""
    return (WIDTH / 2, HEIGHT / 2,
            direction * BALL_SPEED * 0.95,
            random.uniform(-BALL_SPEED * 0.4, BALL_SPEED * 0.4))


class PongAI(Program):
    DESCRIPTION = "Pong — two AI paddles rally forever"

    def setup(self) -> None:
        self._left_y = HEIGHT / 2
        self._right_y = HEIGHT / 2
        self._score_l = 0
        self._score_r = 0
        self._t_since_score = 0.0
        self._bx, self._by, self._vx, self._vy = _serve(random.choice((-1, 1)))

    def _predict_y(self, target_x: float) -> float:
        """Trace the ball's straight-line path with reflections to target_x."""
        x, y, vx, vy = self._bx, self._by, self._vx, self._vy
        if (target_x - x) * vx <= 0:
            return HEIGHT / 2
        # Time to reach target_x
        t = (target_x - x) / vx
        y_at = y + vy * t
        # Bounce off top/bottom
        period = 2.0 * (HEIGHT - 1)
        y_at = y_at % period
        if y_at >= HEIGHT - 1:
            y_at = period - y_at
        return y_at

    def update(self, dt: float, events) -> None:
        self._bx += self._vx * dt
        self._by += self._vy * dt
        if self._by < 0:
            self._by = -self._by; self._vy = -self._vy
        elif self._by > HEIGHT - 1:
            self._by = 2 * (HEIGHT - 1) - self._by; self._vy = -self._vy

        # Paddle AI
        target_l = self._predict_y(LEFT_X) if self._vx < 0 else HEIGHT / 2
        target_r = self._predict_y(RIGHT_X) if self._vx > 0 else HEIGHT / 2
        for ly_attr, target in (("_left_y", target_l), ("_right_y", target_r)):
            cur = getattr(self, ly_attr)
            d = target - cur
            if abs(d) > 0.5:
                cur += max(-PADDLE_SPEED * dt, min(PADDLE_SPEED * dt, d))
            cur = max(PADDLE_H / 2, min(HEIGHT - PADDLE_H / 2 - 1, cur))
            setattr(self, ly_attr, cur)

        # Paddle collisions
        if self._bx <= LEFT_X + 1 and self._vx < 0:
            if abs(self._by - self._left_y) < PADDLE_H / 2:
                self._vx = abs(self._vx)
                offset = (self._by - self._left_y) / (PADDLE_H / 2)
                self._vy += offset * 8
        if self._bx >= RIGHT_X - 1 and self._vx > 0:
            if abs(self._by - self._right_y) < PADDLE_H / 2:
                self._vx = -abs(self._vx)
                offset = (self._by - self._right_y) / (PADDLE_H / 2)
                self._vy += offset * 8

        # Score & reset
        if self._bx < -2:
            self._score_r += 1
            self._bx, self._by, self._vx, self._vy = _serve(1)
        elif self._bx > WIDTH + 2:
            self._score_l += 1
            self._bx, self._by, self._vx, self._vy = _serve(-1)
        # Soft cap at 9 each so the score is always one digit.
        if self._score_l >= 9 or self._score_r >= 9:
            self._score_l = self._score_r = 0

    def render(self) -> Frame:
        f = Frame.black()
        # Center net
        for y in range(0, HEIGHT, 4):
            f.set(WIDTH // 2, y, BG_LINE)
            f.set(WIDTH // 2, y + 1, BG_LINE)
        # Paddles
        ly = int(self._left_y); ry = int(self._right_y)
        for i in range(-PADDLE_H // 2, PADDLE_H // 2):
            f.set(LEFT_X, ly + i, (240, 240, 240))
            f.set(RIGHT_X, ry + i, (240, 240, 240))
        # Ball
        bx, by = int(self._bx), int(self._by)
        f.set(bx, by, (255, 230, 130))
        # Score (small dots — left top + right top areas)
        for i in range(self._score_l):
            f.set(2 + i * 2, 1, (180, 220, 255))
        for i in range(self._score_r):
            f.set(WIDTH - 3 - i * 2, 1, (255, 200, 180))
        return f
