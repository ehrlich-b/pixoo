"""Snake AI — BFS planner; replans every move toward the food."""
from __future__ import annotations

import random
from collections import deque

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


MOVE_HZ = 35.0


class SnakeAI(Program):
    DESCRIPTION = "Snake AI — BFS planner plays itself forever"

    def setup(self) -> None:
        self._reset()
        self._tick_acc = 0.0

    def _reset(self) -> None:
        self._snake: deque[tuple[int, int]] = deque([(WIDTH // 2, HEIGHT // 2)])
        self._spawn_food()

    def _spawn_food(self) -> None:
        body = set(self._snake)
        # Random open cell — biased away from being adjacent to head so the
        # snake gets a meaningful path.
        for _ in range(64):
            x = random.randrange(WIDTH)
            y = random.randrange(HEIGHT)
            if (x, y) not in body:
                self._food = (x, y)
                return
        # Fallback: scan.
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if (x, y) not in body:
                    self._food = (x, y)
                    return
        self._reset()

    def _bfs(self, start: tuple[int, int], goal: tuple[int, int],
             blocked: set[tuple[int, int]]) -> list[tuple[int, int]] | None:
        prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        q: deque[tuple[int, int]] = deque([start])
        while q:
            cx, cy = q.popleft()
            if (cx, cy) == goal:
                path: list[tuple[int, int]] = []
                cur: tuple[int, int] | None = goal
                while prev[cur] is not None:
                    path.append(cur)
                    cur = prev[cur]
                path.reverse()
                return path
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < WIDTH and 0 <= ny < HEIGHT
                        and (nx, ny) not in blocked
                        and (nx, ny) not in prev):
                    prev[(nx, ny)] = (cx, cy)
                    q.append((nx, ny))
        return None

    def _step_once(self) -> None:
        head = self._snake[0]
        # Tail is about to move, so its cell is reachable on the next move.
        body = set(self._snake) - {self._snake[-1]}
        path = self._bfs(head, self._food, body)
        if path:
            nx, ny = path[0]
        else:
            # No path — wander into any safe cell, else die.
            full = set(self._snake)
            options: list[tuple[int, int]] = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                cx, cy = head[0] + dx, head[1] + dy
                if (0 <= cx < WIDTH and 0 <= cy < HEIGHT
                        and (cx, cy) not in full):
                    options.append((cx, cy))
            if not options:
                self._reset()
                return
            nx, ny = random.choice(options)
        if (nx, ny) == self._food:
            self._snake.appendleft((nx, ny))
            self._spawn_food()
        else:
            self._snake.appendleft((nx, ny))
            self._snake.pop()

    def update(self, dt: float, events) -> None:
        self._tick_acc += dt * MOVE_HZ
        while self._tick_acc >= 1.0:
            self._tick_acc -= 1.0
            self._step_once()

    def render(self) -> Frame:
        f = Frame.black()
        fx, fy = self._food
        f.set(fx, fy, (255, 80, 80))
        body = list(self._snake)
        n = len(body)
        for i, (x, y) in enumerate(body):
            if i == 0:
                f.set(x, y, (240, 250, 220))
            else:
                t = i / max(1, n - 1)
                r = int(60 + 30 * t)
                g = int(220 - 60 * t)
                b = int(110 + 90 * t)
                f.set(x, y, (r, g, b))
        return f
