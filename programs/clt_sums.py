"""CLT — sums of N uniform variables converging to a Gaussian as N grows."""
from __future__ import annotations

import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program


N_VALUES = [1, 2, 3, 4, 6, 10, 16]
PHASE_SECONDS = 5.0
SAMPLES_PER_FRAME = 240
HIST_BINS = WIDTH
PEG_TOP = 2
PEG_HEIGHT = 5
HIST_TOP = PEG_TOP + PEG_HEIGHT + 2
HIST_BOTTOM = HEIGHT - 1
HIST_HEIGHT = HIST_BOTTOM - HIST_TOP


class CLT(Program):
    DESCRIPTION = "Central limit theorem — N uniforms summed approach a Gaussian"

    def setup(self) -> None:
        self._n_idx = 0
        self._phase_t = 0.0
        self._reset_hist()

    def _reset_hist(self) -> None:
        self._hist = [0] * HIST_BINS

    def update(self, dt: float, events) -> None:
        self._phase_t += dt
        if self._phase_t > PHASE_SECONDS:
            self._phase_t = 0
            self._n_idx = (self._n_idx + 1) % len(N_VALUES)
            self._reset_hist()
        n = N_VALUES[self._n_idx]
        for _ in range(SAMPLES_PER_FRAME):
            s = sum(random.random() for _ in range(n))
            bin_ = int(s / n * HIST_BINS)
            if bin_ >= HIST_BINS:
                bin_ = HIST_BINS - 1
            self._hist[bin_] += 1

    def render(self) -> Frame:
        f = Frame.black()
        # Top row: N glowing dots indicating how many uniforms are being summed.
        n = N_VALUES[self._n_idx]
        if n <= 16:
            spacing = WIDTH // (n + 1)
            for i in range(n):
                cx = spacing * (i + 1)
                cy = PEG_TOP + 2
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dx * dx + dy * dy <= 2:
                            f.set(cx + dx, cy + dy, (255, 220, 110))
        # Histogram body.
        peak = max(self._hist) if self._hist else 1
        if peak == 0:
            peak = 1
        for x in range(WIDTH):
            h = int(self._hist[x] / peak * HIST_HEIGHT)
            for y in range(HIST_BOTTOM - h, HIST_BOTTOM + 1):
                t = (y - (HIST_BOTTOM - h)) / max(1, h)
                r = int(60 + 180 * t)
                g = int(220 - 60 * t)
                b = int(255 - 90 * (1 - t))
                f.set(x, y, (r, g, b))
        # Phase progress strip at the very top.
        prog = int(self._phase_t / PHASE_SECONDS * WIDTH)
        for x in range(prog):
            f.set(x, 0, (90, 200, 110))
        return f
