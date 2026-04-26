"""Elementary cellular automaton — cycles iconic rules, scrolls bottom-up."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

ROWS_PER_SEC = 30.0
SECONDS_PER_RULE = 8.0
SEED_DENSITY = 0.35  # random-soup starting row; single seed looks uniform on a 64-wide torus

# Rules chosen for visual variety:
#   30  — chaotic (used as a PRNG by Mathematica)
#   90  — Sierpinski triangle from a single seed
#   110 — Turing complete, gliders in chaos
#   54  — class-4 edge of chaos
#   73  — striped + chaos
#   150 — XOR rule, self-similar
RULES = [30, 90, 110, 54, 73, 150]


def _step(row: list[int], rule: int) -> list[int]:
    """One generation of rule `rule`, wrapped at edges."""
    n = len(row)
    out = [0] * n
    for i in range(n):
        l = row[(i - 1) % n]
        c = row[i]
        r = row[(i + 1) % n]
        idx = (l << 2) | (c << 1) | r
        out[i] = (rule >> idx) & 1
    return out


class ECA(Program):
    DESCRIPTION = "Elementary cellular automaton — cycles rules 30/90/110/54/73/150"

    def setup(self) -> None:
        self._rule_idx = 0
        self._row_accum = 0.0
        self._rule_timer = 0.0
        self.rows: list[list[int]] = []  # oldest first; length ≤ HEIGHT
        self._start_rule()

    def _start_rule(self) -> None:
        self.rule = RULES[self._rule_idx % len(RULES)]
        self.rows = []
        seed = [1 if random.random() < SEED_DENSITY else 0 for _ in range(WIDTH)]
        self.rows.append(seed)
        self._rule_timer = 0.0

    def update(self, dt: float, events) -> None:
        self._rule_timer += dt
        if self._rule_timer >= SECONDS_PER_RULE:
            self._rule_idx += 1
            self._start_rule()
            return
        self._row_accum += dt * ROWS_PER_SEC
        while self._row_accum >= 1.0:
            self._row_accum -= 1.0
            self.rows.append(_step(self.rows[-1], self.rule))
            if len(self.rows) > HEIGHT:
                self.rows.pop(0)

    def render(self) -> Frame:
        f = Frame.black()
        # newest row at the bottom; oldest at the top.
        top_y = HEIGHT - len(self.rows)
        for ry, row in enumerate(self.rows):
            y = top_y + ry
            if y < 0:
                continue
            for x in range(WIDTH):
                if row[x]:
                    f.set(x, y, (220, 220, 220))
        return f
