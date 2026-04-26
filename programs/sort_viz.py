"""Sort viz — bubble / insertion / selection / shell, cycled."""
from __future__ import annotations

import random
from typing import Callable, Generator

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N = WIDTH        # 64 bars
SCAN_COL = (140, 200, 255)
ACTIVE_COL = (255, 230, 110)
DONE_COL = (110, 220, 130)
BAR_COL = (110, 130, 180)


def _bubble(arr: list[int]) -> Generator[tuple[int, int], None, None]:
    n = len(arr)
    for i in range(n):
        for j in range(n - 1 - i):
            yield j, j + 1
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]


def _insertion(arr: list[int]) -> Generator[tuple[int, int], None, None]:
    for i in range(1, len(arr)):
        j = i
        while j > 0:
            yield j - 1, j
            if arr[j - 1] > arr[j]:
                arr[j - 1], arr[j] = arr[j], arr[j - 1]
                j -= 1
            else:
                break


def _selection(arr: list[int]) -> Generator[tuple[int, int], None, None]:
    n = len(arr)
    for i in range(n):
        m = i
        for j in range(i + 1, n):
            yield m, j
            if arr[j] < arr[m]:
                m = j
        if m != i:
            arr[i], arr[m] = arr[m], arr[i]
            yield i, m


def _shell(arr: list[int]) -> Generator[tuple[int, int], None, None]:
    n = len(arr)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            j = i
            while j >= gap:
                yield j - gap, j
                if arr[j - gap] > arr[j]:
                    arr[j - gap], arr[j] = arr[j], arr[j - gap]
                    j -= gap
                else:
                    break
        gap //= 2


ALGORITHMS: tuple[tuple[str, Callable, int], ...] = (
    ("bubble", _bubble, 32),
    ("insertion", _insertion, 14),
    ("selection", _selection, 18),
    ("shell", _shell, 8),
)


class SortViz(Program):
    DESCRIPTION = "Sort viz — bubble / insertion / selection / shell"

    def setup(self) -> None:
        self._idx = 0
        self._begin()

    def _begin(self) -> None:
        self._arr = list(range(N))
        random.shuffle(self._arr)
        name, factory, steps_per_frame = ALGORITHMS[self._idx]
        self._gen = factory(self._arr)
        self._steps = steps_per_frame
        self._cur: tuple[int, int] | None = None
        self._done_hold = 0

    def update(self, dt: float, events) -> None:
        if self._cur is None and self._done_hold > 0:
            self._done_hold -= 1
            if self._done_hold <= 0:
                self._idx = (self._idx + 1) % len(ALGORITHMS)
                self._begin()
            return
        for _ in range(self._steps):
            try:
                self._cur = next(self._gen)
            except StopIteration:
                self._cur = None
                self._done_hold = 60
                return

    def render(self) -> Frame:
        f = Frame.black()
        cur = self._cur
        for x in range(N):
            v = self._arr[x]
            top = HEIGHT - 1 - v
            color = ACTIVE_COL if (cur is not None and x in cur) else BAR_COL
            if cur is None and self._done_hold > 0:
                color = DONE_COL
            for y in range(top, HEIGHT):
                f.set(x, y, color)
        return f
