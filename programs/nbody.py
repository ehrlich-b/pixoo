"""Three-body figure-8 choreography (Chenciner & Montgomery, 2000).

Three equal masses chasing each other around a single figure-8 orbit under
pure Newtonian gravity with G = m = 1. Integrated with velocity Verlet at
fixed 2kHz so the orbit stays stable indefinitely.

Params:
  scale=FLOAT   world→pixel multiplier (default 20). Path spans roughly
                x=±1.3, y=±0.4 in world units.
  chaos=FLOAT   initial velocity perturbation on body 0 (default 0). Try
                0.002 to watch the figure-8 slowly unravel into chaos.
"""
from __future__ import annotations

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

# Chenciner-Montgomery initial conditions, G = m_i = 1.
INIT_POS = [
    (-0.97000436,  0.24308753),
    ( 0.97000436, -0.24308753),
    ( 0.0,         0.0),
]
_V3 = (-0.93240737, -0.86473146)
INIT_VEL = [
    (-_V3[0] / 2, -_V3[1] / 2),
    (-_V3[0] / 2, -_V3[1] / 2),
    _V3,
]
PERIOD = 6.3259  # sim-seconds per orbit

SIM_HZ = 2000.0
SIM_DT = 1.0 / SIM_HZ
TIME_SCALE = 0.55  # slow down so motion reads clearly at the device's ~5fps

# Fixed trail sample cadence (sim-seconds) → trail length always covers the
# same chunk of orbit regardless of framerate. PERIOD / 60 ≈ 0.105s/sample.
TRAIL_SAMPLES = 60
TRAIL_SIM_DT = PERIOD / TRAIL_SAMPLES

SOFTENING2 = 1e-3  # tiny softening to avoid singular force at crossover

# Per-body (bright, dim) — trail fades from dim at the tail to bright at the head.
COLORS = [
    ((255, 130, 70),  (50, 18, 8)),    # orange
    ((90, 200, 255),  (10, 32, 55)),   # cyan
    ((200, 255, 130), (30, 55, 20)),   # lime
]


def _accel(pos):
    ax = [0.0, 0.0, 0.0]
    ay = [0.0, 0.0, 0.0]
    for i in range(3):
        xi, yi = pos[i]
        for j in range(i + 1, 3):
            xj, yj = pos[j]
            dx = xj - xi
            dy = yj - yi
            r2 = dx * dx + dy * dy + SOFTENING2
            inv_r3 = r2 ** -1.5
            fx = dx * inv_r3
            fy = dy * inv_r3
            ax[i] += fx
            ay[i] += fy
            ax[j] -= fx
            ay[j] -= fy
    return ax, ay


class NBody(Program):
    DESCRIPTION = "3-body figure-8 choreography with fading trails"

    def setup(self) -> None:
        self.scale = float(self.params.get("scale", 20))
        chaos = float(self.params.get("chaos", 0))
        self.pos = [list(p) for p in INIT_POS]
        self.vel = [list(v) for v in INIT_VEL]
        if chaos:
            self.vel[0][0] += chaos
        self._acc = _accel(self.pos)
        self._sim_accum = 0.0
        self._trail_accum = 0.0
        self.trails: list[list[tuple[float, float]]] = [[], [], []]

    def _step(self, dt: float) -> None:
        pos, vel = self.pos, self.vel
        ax, ay = self._acc
        for i in range(3):
            pos[i][0] += vel[i][0] * dt + 0.5 * ax[i] * dt * dt
            pos[i][1] += vel[i][1] * dt + 0.5 * ay[i] * dt * dt
        ax_new, ay_new = _accel(pos)
        for i in range(3):
            vel[i][0] += 0.5 * (ax[i] + ax_new[i]) * dt
            vel[i][1] += 0.5 * (ay[i] + ay_new[i]) * dt
        self._acc = (ax_new, ay_new)

    def update(self, dt: float, events) -> None:
        self._sim_accum += dt * TIME_SCALE
        # Cap backlog so a stalled device doesn't trigger a simulation storm.
        if self._sim_accum > 0.25:
            self._sim_accum = 0.25
        while self._sim_accum >= SIM_DT:
            self._sim_accum -= SIM_DT
            self._step(SIM_DT)
            self._trail_accum += SIM_DT
            if self._trail_accum >= TRAIL_SIM_DT:
                self._trail_accum -= TRAIL_SIM_DT
                for i in range(3):
                    t = self.trails[i]
                    t.append((self.pos[i][0], self.pos[i][1]))
                    if len(t) > TRAIL_SAMPLES:
                        del t[:len(t) - TRAIL_SAMPLES]

    def _to_px(self, wx: float, wy: float) -> tuple[int, int]:
        return (
            int(round(WIDTH / 2 + wx * self.scale)),
            int(round(HEIGHT / 2 + wy * self.scale)),
        )

    def render(self) -> Frame:
        f = Frame.black()
        # Trails: oldest → newest so the newest (brightest) overwrites crossings.
        for i, trail in enumerate(self.trails):
            bright, dim = COLORS[i]
            n = len(trail)
            if n < 2:
                continue
            denom = n - 1
            for k, (wx, wy) in enumerate(trail):
                t = k / denom
                r = int(dim[0] + (bright[0] - dim[0]) * t)
                g = int(dim[1] + (bright[1] - dim[1]) * t)
                b = int(dim[2] + (bright[2] - dim[2]) * t)
                f.set(*self._to_px(wx, wy), (r, g, b))
        # Bodies: bright core + dimmed plus-halo so they stand out from the trail.
        for i, (wx, wy) in enumerate(self.pos):
            bright = COLORS[i][0]
            cx, cy = self._to_px(wx, wy)
            halo = (bright[0] // 2, bright[1] // 2, bright[2] // 2)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                f.set(cx + dx, cy + dy, halo)
            f.set(cx, cy, bright)
        return f
