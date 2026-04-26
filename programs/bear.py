"""Bear den — 72-minute year, 24 days, diurnal bear.

Time scales:
  year  = 72 minutes (4 seasons × 3 months × 2 days per month)
  day   = 3 minutes (≈ 138 s of daylight + 42 s of night)

The bear wakes each dawn, wanders the meadow through the day (walks,
dwells, eats at the berry bush, occasionally rears up on hind legs), and
retreats into its cave at dusk to sleep the night. In winter it hibernates
for the whole season. Weather — calm, cloudy, rain, storm (with thunder
flashes), snow, leaves, blossom — rolls through per season. Season
palettes cross-fade smoothly across the last day of each season so
transitions are continuous, with the deepest blend at night.

The moon runs through one lunar cycle per year (8 phases × 3 days each).

Ambient-scene light on CPU: per frame is a few thousand bytearray writes
plus a single C-level bytes.translate for night dim / lightning flash.

Params:
  year=FLOAT   year length in seconds (default 4320 = 72 minutes)
  start=STR    starting season: spring|summer|autumn|winter (default spring)
"""
from __future__ import annotations

import math
import random

from pixoolib.frame import HEIGHT, WIDTH, Frame
from pixoolib.runtime import Program

# ── Layout ────────────────────────────────────────────────────────────────
GROUND_Y = 48
CAVE_X = 14
CAVE_TOP_Y = 30
CAVE_FLOOR_Y = GROUND_Y - 1
CAVE_HALF_W = 6
HILL_X_MAX = 38
HILL_TOP_Y = 10
HILL_PARABOLA_K = 0.11       # flatter = wider cave/hill

TREE_XS = (38, 56)
TREE_TRUNK_W = 3
TREE_TRUNK_H = 11
TREE_FOLIAGE_RX = 7
TREE_FOLIAGE_RY = 6

BERRY_X = 48
BERRY_HALF_W = 4
BERRY_HALF_H = 2

FLOWER_XS = (34, 42, 50, 54, 60, 62)

BEAR_MIN_X = 11
BEAR_MAX_X = WIDTH - 12
BEAR_BASE_SPEED = 5.5

# ── Time ──────────────────────────────────────────────────────────────────
DAY_LENGTH = 180.0
DAYS_PER_MONTH = 2
MONTHS_PER_YEAR = 12
DAYS_PER_YEAR = DAYS_PER_MONTH * MONTHS_PER_YEAR           # 24
SEASONS_PER_YEAR = 4
DAYS_PER_SEASON = DAYS_PER_YEAR // SEASONS_PER_YEAR        # 6
YEAR_LENGTH = DAY_LENGTH * DAYS_PER_YEAR                   # 4320 s = 72 min
MOON_PHASES = 8
DAYS_PER_MOON_PHASE = DAYS_PER_YEAR // MOON_PHASES         # 3

# Day-phase fractions (of day_frac in [0,1]). Day dominates (~78 %).
# Dawn/dusk are long, deep-painted twilight arcs — sunrise and sunset
# each take a full minute. Breakdown over 180 s:
#   dawn        0.000..0.289  (~52 s sunrise twilight)
#   full day    0.289..0.500  (~38 s high sun)
#   dusk        0.500..0.789  (~52 s sunset twilight)
#   deep night  0.789..0.928  (~25 s stars)
#   pre-dawn    0.928..1.000  (~13 s horizon glow)
DAWN_END = 0.289
SUN_END = 0.500
DUSK_END = 0.789
NIGHT_END = 0.928
SEASON_NAMES = ("spring", "summer", "autumn", "winter")
WEATHER_CHANGE_S = 75.0

# Foliage/particle spawn origin (matches _paint_trees' cy math).
TREE_FOLIAGE_CY = GROUND_Y - TREE_TRUNK_H - TREE_FOLIAGE_RY + 2

# ── Sky (day per season, one shared night) ────────────────────────────────
SKY_DAY = (
    ((160, 200, 240), (255, 228, 210)),
    ((90,  170, 240), (220, 240, 255)),
    ((220, 140, 90),  (255, 210, 140)),
    ((150, 160, 180), (210, 218, 235)),
)
SKY_NIGHT = ((5, 8, 30), (22, 18, 48))
SKY_DUSK = ((230, 110, 80), (255, 170, 100))

# ── Ground / rock per season ──────────────────────────────────────────────
GROUND_COLORS = (
    ((110, 190, 110), (60,  140, 70)),
    ((120, 200, 90),  (70,  150, 60)),
    ((200, 150, 70),  (130, 90,  40)),
    ((235, 235, 245), (195, 200, 220)),
)
ROCK_COLORS = (
    ((140, 130, 110), (90,  80,  70)),
    ((130, 120, 100), (80,  70,  60)),
    ((150, 110, 80),  (100, 80,  60)),
    ((210, 215, 230), (130, 140, 160)),
)

TRUNK_COLOR = (80, 55, 35)
TRUNK_COLOR_WINTER = (95, 80, 65)
FOLIAGE = (
    ((100, 170, 80),  (150, 210, 120), (240, 180, 220)),
    ((60,  140, 60),  (100, 180, 90),  None),
    ((195, 85,  30),  (235, 140, 50),  (255, 200, 80)),
    (None, None, None),
)

SUN_COLOR = (255, 235, 140)
SUN_RIM = (255, 180, 80)
MOON_COLOR = (245, 248, 255)
MOON_RIM = (205, 210, 230)
MOON_SHADOW = (75, 80, 110)
STAR_COLORS = ((255, 255, 255), (220, 220, 255), (255, 240, 180))

# 8 discrete lunar phases across an 8-day year (one per day).
# Each tuple covers a 5-wide core mask for the moon disc: columns
# dx=-2,-1,0,1,2. True means lit, False means shadow side.
# new → waxing crescent → first quarter → waxing gibbous → full →
# waning gibbous → last quarter → waning crescent → back to new.
MOON_PHASE_MASKS = (
    (False, False, False, False, False),  # new
    (False, False, False, False, True),   # waxing crescent
    (False, False, False, True,  True),   # first quarter
    (False, False, True,  True,  True),   # waxing gibbous
    (True,  True,  True,  True,  True),   # full
    (True,  True,  True,  False, False),  # waning gibbous
    (True,  True,  False, False, False),  # last quarter
    (True,  False, False, False, False),  # waning crescent
)

BEAR_FUR = (120, 75, 40)
BEAR_FUR_DARK = (80, 50, 25)
BEAR_FUR_LIGHT = (150, 100, 60)
BEAR_SNOUT = (180, 140, 100)
BEAR_EYE = (15, 15, 15)

# Papa bear — darker, slightly redder fur. Distinguishable silhouette.
PAPA_FUR = (90, 55, 30)
PAPA_FUR_DARK = (55, 30, 15)
PAPA_FUR_LIGHT = (125, 80, 50)
PAPA_SNOUT = (165, 125, 90)

MOMMA_PALETTE = (BEAR_FUR, BEAR_FUR_DARK, BEAR_FUR_LIGHT, BEAR_SNOUT, BEAR_EYE)
PAPA_PALETTE = (PAPA_FUR, PAPA_FUR_DARK, PAPA_FUR_LIGHT, PAPA_SNOUT, BEAR_EYE)

HEART_CORE = (255, 80, 120)
HEART_EDGE = (255, 160, 190)

RABBIT_FUR = (180, 170, 155)
RABBIT_FUR_DARK = (140, 130, 120)
BIRD_COLOR = (40, 35, 35)
BIRD_PERCH = (60, 50, 45)

CLOUD_DAY = (245, 248, 255)
CLOUD_DUSK = (255, 210, 200)
CLOUD_NIGHT = (70, 75, 110)
CLOUD_SHADE = (205, 210, 230)
CLOUD_RAIN = (120, 125, 150)
CLOUD_STORM = (70, 70, 95)

LIGHTNING_CORE = (255, 255, 240)
LIGHTNING_EDGE = (200, 210, 255)

ZZZ_COLOR = (235, 235, 250)

WEATHER_TABLE = (
    (("calm", 0.40), ("cloudy", 0.70), ("rain", 0.85), ("storm", 0.92), ("blossom", 1.0)),
    (("calm", 0.70), ("cloudy", 0.90), ("rain", 0.97), ("storm", 1.0)),
    (("calm", 0.32), ("leaves", 0.62), ("cloudy", 0.82), ("rain", 0.92), ("storm", 1.0)),
    (("snow", 0.55), ("calm", 0.80), ("cloudy", 1.0)),
)
PARTICLE_COUNT = {"calm": 0, "cloudy": 0, "rain": 26, "storm": 36,
                  "snow": 24, "leaves": 14, "blossom": 10}
CLOUD_COUNT = {"calm": 2, "cloudy": 5, "rain": 6, "storm": 10,
               "snow": 4, "leaves": 3, "blossom": 3}

# Deterministic stars (fixed positions, random per-star phases)
_SRAND = random.Random(0xBEA4)
STARS = tuple(
    (_SRAND.randint(0, WIDTH - 1), _SRAND.randint(0, 34),
     _SRAND.random() * math.tau, STAR_COLORS[_SRAND.randrange(3)])
    for _ in range(42)
)

CLOUD_SHAPES = (
    ((-3, 0), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
     (-2, -1), (-1, -1), (0, -1), (1, -1)),
    ((-4, 0), (-3, 0), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (3, 0),
     (-3, -1), (-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1),
     (-1, -2), (0, -2)),
    ((-2, 0), (-1, 0), (0, 0), (1, 0),
     (-1, -1), (0, -1)),
)


# ── Utilities ─────────────────────────────────────────────────────────────
def _lerp_rgb(a, b, t):
    return (int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t))


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _clamp255(x):
    return 0 if x < 0 else 255 if x > 255 else int(x)


def _setp(px, x, y, rgb):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        i = (y * WIDTH + x) * 3
        px[i] = rgb[0]; px[i + 1] = rgb[1]; px[i + 2] = rgb[2]


def _fill_row(px, y, rgb):
    start = y * WIDTH * 3
    px[start:start + WIDTH * 3] = bytes(rgb) * WIDTH


def _smoothstep(t):
    if t <= 0: return 0.0
    if t >= 1: return 1.0
    return t * t * (3 - 2 * t)


# ── Time / season state ───────────────────────────────────────────────────
def _year_state(year_frac):
    """Cross-fade palettes smoothly over the second day of each season so
    transitions are continuous with the deepest blend at night.

    Returns (cur_season, next_season, blend_0_to_1)."""
    sf = year_frac * 4.0
    cur = int(sf) % 4
    frac = sf - int(sf)
    if frac < 0.5:
        blend = 0.0
    else:
        # Second half (last day): 0→1 via smoothstep.
        blend = _smoothstep((frac - 0.5) / 0.5)
    return cur, (cur + 1) % 4, blend


def _day_phases(day_frac):
    """Return (night_level, is_day, sun_or_moon_phase).

    The sun arcs continuously from horizon (phase=0) at dawn-start to
    horizon (phase=1) at dusk-end, so it's visibly rising or setting
    throughout twilight. The moon uses a separate arc across the night.
    Dawn and pre-dawn are one continuous NIGHT_END→1.0→DAWN_END ramp so
    the sky doesn't jump dark at midnight. Ramps use cos smoothstep."""
    # Pre-dawn (NIGHT_END..1.0) flows into dawn (0..DAWN_END) as a single
    # smooth 1→0 transition; dusk (SUN_END..DUSK_END) is its 0→1 mirror.
    dawn_span = (1.0 - NIGHT_END) + DAWN_END
    if day_frac < DAWN_END:
        t = ((1.0 - NIGHT_END) + day_frac) / dawn_span
        night_level = 0.5 * (1 + math.cos(t * math.pi))
        return night_level, True, day_frac / DUSK_END
    if day_frac < SUN_END:
        return 0.0, True, day_frac / DUSK_END
    if day_frac < DUSK_END:
        t = (day_frac - SUN_END) / (DUSK_END - SUN_END)
        night_level = 0.5 * (1 - math.cos(t * math.pi))
        return night_level, True, day_frac / DUSK_END
    night_span = 1.0 - DUSK_END
    moon_phase = (day_frac - DUSK_END) / night_span
    if day_frac < NIGHT_END:
        night_level = 1.0
    else:
        t = (day_frac - NIGHT_END) / dawn_span
        night_level = 0.5 * (1 + math.cos(t * math.pi))
    return night_level, False, moon_phase


# ── Palette blending across the season cross-fade ─────────────────────────
def _blend_sky(cur, nxt, blend):
    return (_lerp_rgb(SKY_DAY[cur][0], SKY_DAY[nxt][0], blend),
            _lerp_rgb(SKY_DAY[cur][1], SKY_DAY[nxt][1], blend))


def _blend_ground(cur, nxt, blend):
    return (_lerp_rgb(GROUND_COLORS[cur][0], GROUND_COLORS[nxt][0], blend),
            _lerp_rgb(GROUND_COLORS[cur][1], GROUND_COLORS[nxt][1], blend))


def _blend_rock(cur, nxt, blend):
    return (_lerp_rgb(ROCK_COLORS[cur][0], ROCK_COLORS[nxt][0], blend),
            _lerp_rgb(ROCK_COLORS[cur][1], ROCK_COLORS[nxt][1], blend))


def _blend_foliage(cur, nxt, blend):
    cf = FOLIAGE[cur]
    nf = FOLIAGE[nxt]
    if cf[0] is None and nf[0] is None:
        return None, None, None
    if cf[0] is None:
        # Current is winter: only show next's colors once the cross-fade starts.
        if blend <= 0.01:
            return None, None, None
        return nf[0], nf[1], nf[2]
    if nf[0] is None:
        # Next is winter — keep current season's colors; density fades instead.
        return cf[0], cf[1], cf[2]
    return (_lerp_rgb(cf[0], nf[0], blend),
            _lerp_rgb(cf[1], nf[1], blend),
            nf[2] if blend > 0.5 else cf[2])


def _tree_leaf_density(year_frac):
    """0..1 density; bare in winter, ramps in spring, full in summer,
    thins mid-autumn, fully bare by end of autumn."""
    yf = year_frac
    if yf < 0.25:
        return yf / 0.25
    if yf < 0.5:
        return 1.0
    if yf < 0.75:
        return 1.0 - (yf - 0.5) / 0.25 * 0.7
    return max(0.0, 0.3 - (yf - 0.75) / 0.25 * 0.3)


def _grass_density(year_frac):
    if year_frac < 0.1:
        return year_frac / 0.1 * 0.6
    if year_frac < 0.5:
        return 0.6 + (year_frac - 0.1) / 0.4 * 0.4
    if year_frac < 0.75:
        return 1.0 - (year_frac - 0.5) / 0.25 * 0.7
    return 0.0


# ── Sky / stars / celestial ───────────────────────────────────────────────
SKY_STORM = ((85, 90, 110), (140, 145, 165))
SKY_RAIN = ((125, 130, 150), (165, 170, 190))


def _paint_sky(px, sky_top, sky_hor, night_level, day_frac, weather):
    night_top, night_hor = SKY_NIGHT
    # Heavy overcast: storm fully covers the sky in slate; rain partially.
    overcast = 0.0
    if weather == "storm":
        sky_top = _lerp_rgb(sky_top, SKY_STORM[0], 1.0)
        sky_hor = _lerp_rgb(sky_hor, SKY_STORM[1], 1.0)
        overcast = 1.0
    elif weather == "rain":
        sky_top = _lerp_rgb(sky_top, SKY_RAIN[0], 0.55)
        sky_hor = _lerp_rgb(sky_hor, SKY_RAIN[1], 0.55)
        overcast = 0.55
    # Dusk-tint ramp: peaks where the sun is just above horizon. Ramps up
    # during dawn (0..DAWN_END), stays 0 mid-day, ramps back up during
    # dusk (SUN_END..DUSK_END), fades through deep night, peaks again at
    # pre-dawn glow. Using sin(·*π) makes the peak bell-shaped.
    dusk_amount = 0.0
    if day_frac < DAWN_END:
        dusk_amount = math.sin((1 - day_frac / DAWN_END) * math.pi * 0.5)
    elif SUN_END <= day_frac < DUSK_END:
        dusk_amount = math.sin(
            (day_frac - SUN_END) / (DUSK_END - SUN_END) * math.pi * 0.5)
    elif NIGHT_END <= day_frac <= 1.0:
        dusk_amount = math.sin(
            (1 - (day_frac - NIGHT_END) / (1.0 - NIGHT_END)) * math.pi * 0.5)
    dusk_amount = min(1.0, dusk_amount) * (1 - overcast * 0.8)
    for y in range(GROUND_Y):
        t = y / (GROUND_Y - 1)
        day_rgb = _lerp_rgb(sky_top, sky_hor, t)
        night_rgb = _lerp_rgb(night_top, night_hor, t)
        base = _lerp_rgb(day_rgb, night_rgb, night_level)
        if dusk_amount > 0:
            dusk_rgb = _lerp_rgb(SKY_DUSK[0], SKY_DUSK[1], t)
            # Strong near horizon, softer up top but still present.
            weight = dusk_amount * (0.35 + 0.65 * t) * (1 - night_level * 0.4)
            base = _lerp_rgb(base, dusk_rgb, weight)
        _fill_row(px, y, base)


def _paint_stars(px, night_level, t):
    # Deep-night only — below 0.7 the sky is still bright enough that star
    # dots read as dirty pixels rather than stars.
    if night_level < 0.7:
        return
    strength = min(1.0, (night_level - 0.7) / 0.25)
    for sx, sy, phase, color in STARS:
        tw = 0.55 + 0.45 * math.sin(t * 2.4 + phase)
        b = max(0.0, tw) * strength
        if b < 0.15:
            continue
        _setp(px, sx, sy,
              (int(color[0] * b), int(color[1] * b), int(color[2] * b)))


def _paint_sun_or_moon(px, is_day, phase, moon_phase_idx=0):
    cx = int(5 + phase * (WIDTH - 11))
    peak_y = 6
    horizon_y = GROUND_Y - 5
    cy = int(horizon_y - math.sin(phase * math.pi) * (horizon_y - peak_y))
    if is_day:
        # 3x3 core + 4-point rim + corner rim for a bigger sun disc.
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                _setp(px, cx + dx, cy + dy, SUN_COLOR)
        for (dx, dy) in ((-2, 0), (2, 0), (0, -2), (0, 2),
                         (-2, -1), (2, -1), (-2, 1), (2, 1),
                         (-1, -2), (1, -2), (-1, 2), (1, 2)):
            _setp(px, cx + dx, cy + dy, SUN_RIM)
        return
    # Moon with discrete phases. A 5-wide by 3-tall disc is rendered,
    # with the appropriate phase mask dimming the shadow side.
    mask = MOON_PHASE_MASKS[moon_phase_idx % 8]
    for dy in (-1, 0, 1):
        for idx, lit in enumerate(mask):
            dx = idx - 2
            # Disc shape: skip outer corners so the moon looks round.
            if abs(dx) == 2 and dy != 0:
                continue
            if lit:
                col = MOON_COLOR if abs(dx) <= 1 and dy == 0 else MOON_RIM
                _setp(px, cx + dx, cy + dy, col)
            else:
                # Only draw shadow for waxing/waning (non-new) phases — the
                # shadow edge makes the crescent/gibbous silhouette readable.
                if moon_phase_idx != 0:
                    _setp(px, cx + dx, cy + dy, MOON_SHADOW)


# ── Clouds / weather atmospherics ─────────────────────────────────────────
def _cloud_base(weather):
    if weather == "storm":
        return CLOUD_STORM
    if weather == "rain":
        return CLOUD_RAIN
    return CLOUD_DAY


def _cloud_color(night_level, day_frac, weather):
    base = _cloud_base(weather)
    base = _lerp_rgb(base, CLOUD_NIGHT, night_level)
    dusk = 0.0
    if day_frac < DAWN_END or (SUN_END <= day_frac < DUSK_END):
        dusk = 0.7 * (1 - night_level)
    if dusk > 0:
        base = _lerp_rgb(base, CLOUD_DUSK, dusk)
    return base


def _paint_clouds(px, clouds, color, shade_color):
    for (cx, cy, shape_idx) in clouds:
        for (dx, dy) in CLOUD_SHAPES[shape_idx]:
            c = shade_color if dy == 0 else color
            _setp(px, int(cx) + dx, int(cy) + dy, c)


def _paint_lightning_bolt(px, seed):
    r = random.Random(seed)
    # Start near a random cloud x at top, jitter downward to the ground.
    x = r.randint(12, WIDTH - 12)
    y = 4
    while y < GROUND_Y - 2:
        _setp(px, x, y, LIGHTNING_CORE)
        _setp(px, x + 1, y, LIGHTNING_EDGE)
        _setp(px, x - 1, y, LIGHTNING_EDGE)
        y += 1
        x += r.choice((-1, 0, 0, 1))
        x = _clamp(x, 4, WIDTH - 5)


# ── Ground / hill / cave ──────────────────────────────────────────────────
def _paint_ground(px, ground_top, ground_bot):
    h = HEIGHT - GROUND_Y
    r0, g0, b0 = ground_top
    r1, g1, b1 = ground_bot
    for y in range(GROUND_Y, HEIGHT):
        t = (y - GROUND_Y) / max(1, h - 1)
        r = int(r0 + (r1 - r0) * t)
        g = int(g0 + (g1 - g0) * t)
        b = int(b0 + (b1 - b0) * t)
        for x in range(WIDTH):
            j = ((x * 73 + y * 151) & 7) - 4
            i = (y * WIDTH + x) * 3
            px[i]     = _clamp255(r + j)
            px[i + 1] = _clamp255(g + j)
            px[i + 2] = _clamp255(b + j)


def _paint_hill_cave(px, rock_top, rock_bot):
    # Hill: parabolic rise centered at x=CAVE_X, spanning HILL_X_MAX.
    for x in range(HILL_X_MAX):
        dx = x - CAVE_X
        top_y = int(HILL_TOP_Y + (dx * dx) * HILL_PARABOLA_K)
        if top_y >= GROUND_Y:
            continue
        for y in range(top_y, GROUND_Y):
            t = (y - top_y) / max(1, GROUND_Y - top_y - 1)
            _setp(px, x, y, _lerp_rgb(rock_top, rock_bot, t))
    # Cave mouth
    for y in range(CAVE_TOP_Y, CAVE_FLOOR_Y + 1):
        dy = y - CAVE_TOP_Y
        half = CAVE_HALF_W - max(0, 2 - dy)  # 3, 4, 5, 5, ...
        for dx in range(-half, half + 1):
            _setp(px, CAVE_X + dx, y, (10, 6, 16))


# ── Trees, berry bush, flowers, grass ─────────────────────────────────────
BRANCHES = ((0, -2), (-1, -3), (1, -3), (-2, -4), (2, -4),
            (-1, -5), (1, -5), (0, -6), (-3, -3), (3, -3))


def _paint_trees(px, year_frac, foliage, perches, is_winter_like):
    dark, light, accent = foliage
    density = _tree_leaf_density(year_frac)
    trunk = TRUNK_COLOR_WINTER if is_winter_like else TRUNK_COLOR
    rx = TREE_FOLIAGE_RX
    ry = TREE_FOLIAGE_RY
    for tx in TREE_XS:
        # Trunk
        for y in range(GROUND_Y - TREE_TRUNK_H, GROUND_Y):
            for dx in range(TREE_TRUNK_W):
                _setp(px, tx + dx, y, trunk)
        cx = tx + 1
        cy = GROUND_Y - TREE_TRUNK_H - TREE_FOLIAGE_RY + 2
        # Stem bridges the trunk top up into the foliage center so leaves
        # never look detached, even at very low density.
        for y in range(cy, GROUND_Y - TREE_TRUNK_H):
            _setp(px, cx, y, trunk)
        # Branches radiate from the center; drawn before foliage so sparse
        # leaves read as a skeleton with buds.
        for (bx, by) in BRANCHES:
            _setp(px, cx + bx, cy + by, trunk)
        # Snow on branches in deep winter
        if density <= 0 and year_frac >= 0.8:
            for (bx, by) in ((-1, -4), (1, -5), (0, -6), (-2, -3)):
                _setp(px, cx + bx, cy + by, (230, 235, 245))
        if dark is None or density <= 0:
            continue
        # Density gates the ellipse radius, not per-pixel probability — low
        # density = compact tuft of leaves at the crown; full density = the
        # whole foliage ellipse. Cleaner silhouette at every size.
        rng = random.Random(tx * 31 + (int(year_frac * 4) & 3))
        for dy in range(-ry - 1, ry + 1):
            for dx in range(-rx - 1, rx + 2):
                n = (dx / (rx + 0.2)) ** 2 + (dy / (ry + 0.2)) ** 2
                if n >= density:
                    continue
                col = dark if n < density * 0.55 else light
                _setp(px, cx + dx, cy + dy, col)
        if accent and density > 0.4:
            for _ in range(4):
                _setp(px, cx + rng.randint(-rx + 1, rx - 1),
                      cy + rng.randint(-ry + 1, ry // 2), accent)
        for (ptx, px_x, py_y) in perches:
            if ptx == tx:
                _setp(px, px_x, py_y, BIRD_PERCH)


def _paint_berry_bush(px, is_berry_season, is_storm_dim):
    if not is_berry_season:
        return
    cx, cy = BERRY_X, GROUND_Y - BERRY_HALF_H - 1
    hw = BERRY_HALF_W
    hh = BERRY_HALF_H
    leaf = (40, 100, 40) if not is_storm_dim else (30, 70, 35)
    leaf_hi = (70, 140, 70) if not is_storm_dim else (55, 100, 55)
    berry = (200, 40, 50)
    for dy in range(-hh, hh):
        for dx in range(-hw, hw + 1):
            n = (dx / (hw + 0.2)) ** 2 + (dy / (hh + 0.5)) ** 2
            if n < 1.0:
                _setp(px, cx + dx, cy + dy, leaf if n > 0.35 else leaf_hi)
    # Berries dotted around the bush
    for (dx, dy) in ((-2, -1), (1, -1), (3, 0), (-3, 0), (0, -2), (2, 1)):
        _setp(px, cx + dx, cy + dy, berry)


def _paint_flowers_and_grass(px, year_frac):
    # Grass blades
    n_grass = int(_grass_density(year_frac) * len(FLOWER_XS) * 3 + 4)
    for i in range(n_grass):
        gx = (i * 37 + 5) % WIDTH
        col = (90, 170, 90) if (i & 1) else (120, 200, 110)
        _setp(px, gx, GROUND_Y, col)

    # Flowers with piecewise bloom
    yf = year_frac
    if yf < 0.15:
        bloom = yf / 0.15
    elif yf < 0.45:
        bloom = 1.0
    elif yf < 0.55:
        bloom = 1.0 - (yf - 0.45) / 0.1
    else:
        bloom = 0.0
    if bloom > 0:
        n = max(1, int(bloom * len(FLOWER_XS)))
        pink = (255, 200, 230)
        yellow = (250, 230, 120)
        leaf = (170, 210, 110)
        for i, fx in enumerate(FLOWER_XS[:n]):
            col = pink if i & 1 else yellow
            _setp(px, fx, GROUND_Y, col)
            _setp(px, fx, GROUND_Y - 1, leaf)
    elif 0.55 <= yf < 0.75:
        for fx in FLOWER_XS:
            _setp(px, fx, GROUND_Y, (200, 160, 80))


# ── Bear ──────────────────────────────────────────────────────────────────
# Bear sprite bitmap — 13 cols × 10 rows, right-facing.
# Origin (0,0) is the bear's anchor at ground level: col = dx - (-5), row = dy - (-9).
# So col 0 corresponds to dx=-5 (rump tip) and col 12 to dx=+7 (snout tip);
# row 0 is dy=-9 (top of ears) and row 9 is dy=0 (feet on ground).
#
# Silhouette goals:
#   • Shoulder hump rises at cols 3-5 (above fore legs).
#   • Neck dip at col 6 — key silhouette cue that reads as "bear".
#   • Head at cols 7-10 lower than the hump; ears bump up at cols 7,9.
#   • Snout extends 2 cols past the head at cols 11-12.
#   • Fore legs directly under the hump (cols 5-6); hind legs at cols 1-2.
#
# Char codes:
#   f fur     d fur_dark (belly)   l fur_light (highlight)
#   E ear (fur_dark)               e eye       s snout        n nose
#   L leg (fur_dark)               . empty
# Bear sprite — 10 wide × 9 tall. Compact silhouette with a clearly
# separate head sitting on top-right of the body.
#
# Col 0 = dx=-4 (rump), col 9 = dx=+5 (snout tip). Row 0 = dy=-8 (ear
# tip), row 8 = dy=0 (ground).
# Bear sprite — 10 wide × 9 tall with a clear blocky head rising from a
# compact rounded body. Ears bump up in pairs; snout is 1 pixel forward
# tipped with a dark nose dot. Eye sits on the back of the muzzle.
# Bear sprite — 10 wide × 9 tall. Body with a visible shoulder hump
# (cols 3-4 rise above the rump), small blocky head forward of the neck
# dip, rounded 2-wide ear bumps on top. Single-pixel dark nose tip.
# Bear sprite v2 — 21 wide × 14 tall. Auto-outlined silhouette with
# distinct head + shoulder hump (3 bumps along top: 2 ears + hump).
# Light back highlight (l) on shoulder/upper body, regular fur (f) below.
# 4 legs visible with 3-row tall stance for chunky proportions.
# Col 0 = dx=-10 (rump), col 20 = dx=+10 (head/nose). Head is on RIGHT
# in source so default dir_right=True renders head-forward.
# Row 0 = dy=-13 (ear tip), row 13 = dy=0 (feet on ground line).
_BEAR_WALK_A = (
    "..............dd..dd.",  # -13  two ears only (no third hump bump)
    "..............dfEdfEd",  # -12  ear bases
    ".......ddfffffffffffd",  # -11  head top + shoulder hump (in back silhouette)
    ".....ddllllllllffffed",  # -10  eye + light hump highlight
    "...ddlllllllllllffffd",  # -9
    ".ddllllllllllllfffffn",  # -8   nose on right
    "dfllllllllllllffffffn",  # -7
    ".dffffffffffffffffffs",  # -6   muzzle bottom
    ".ddffffffffffffffffs.",  # -5   chin
    "..fffffffffffffffff..",  # -4   body bottom
    ".LLL.LLL....LLL.LLL..",  # -3   4 legs
    ".LLL.LLL....LLL.LLL..",  # -2
    ".LLL.LLL....LLL.LLL..",  # -1
    ".LLL.LLL....LLL.LLL..",  # 0    feet on ground line
)
_BEAR_WALK_B = (
    "..............dd..dd.",
    "..............dfEdfEd",
    ".......ddfffffffffffd",
    ".....ddllllllllffffed",
    "...ddlllllllllllffffd",
    ".ddllllllllllllfffffn",
    "dfllllllllllllffffffn",
    ".dffffffffffffffffffs",
    ".ddffffffffffffffffs.",
    "..fffffffffffffffff..",
    "LLL.LLL....LLL.LLL...",  # legs shifted 1 col
    "LLL.LLL....LLL.LLL...",
    "LLL.LLL....LLL.LLL...",
    "LLL.LLL....LLL.LLL...",
)
_BEAR_DWELL = _BEAR_WALK_A
# Eat pose — head ducked (ears tucked, eye/nose unchanged). The cycle alternates
# this with _BEAR_DWELL so the bear visibly bobs while munching.
_BEAR_EAT_DUCK = (
    ".....................",   # -13  ears tucked
    ".....................",   # -12
    ".......ddfffffffffffd",   # -11
    ".....ddllllllllffffed",   # -10
    "...ddlllllllllllffffd",   # -9
    ".ddllllllllllllfffffn",   # -8
    "dfllllllllllllffffffn",   # -7
    ".dffffffffffffffffffs",   # -6
    ".ddffffffffffffffffs.",   # -5
    "..fffffffffffffffff..",   # -4
    ".LLL.LLL....LLL.LLL..",   # -3
    ".LLL.LLL....LLL.LLL..",   # -2
    ".LLL.LLL....LLL.LLL..",   # -1
    ".LLL.LLL....LLL.LLL..",   # 0
)


def _bear_palette_map(palette):
    fur, fur_dark, fur_light, snout, eye = palette
    return {
        'f': fur, 'd': fur_dark, 'l': fur_light,
        'E': fur_dark, 'e': eye, 's': snout, 'n': eye, 'L': fur_dark,
    }


def _paint_bitmap(px, x, gy, rows, row0_dy, col0_dx, dir_right, cmap):
    """Paint a bitmap anchored at (x, gy). col0_dx is the dx for column 0;
    row0_dy is the dy for row 0. Flips horizontally when not dir_right."""
    d = 1 if dir_right else -1
    for r, rowstr in enumerate(rows):
        py = gy + row0_dy + r
        for c, ch in enumerate(rowstr):
            if ch == '.':
                continue
            dx = col0_dx + c
            _setp(px, x + d * dx, py, cmap[ch])


def _paint_bear(px, x_center, phase, fatness, dir_right, activity,
                palette=MOMMA_PALETTE, rx_bonus=0):
    x = int(round(x_center))
    gy = GROUND_Y - 1
    d = 1 if dir_right else -1

    if activity == "stand":
        _paint_bear_standing(px, x, fatness, d, palette)
        return

    cmap = _bear_palette_map(palette)

    if activity == "eat":
        rows = _BEAR_EAT_DUCK if (phase & 1) else _BEAR_DWELL
    elif activity == "walk":
        rows = _BEAR_WALK_B if (phase & 1) else _BEAR_WALK_A
    else:
        rows = _BEAR_DWELL

    _paint_bitmap(px, x, gy, rows, row0_dy=-13, col0_dx=-10,
                  dir_right=dir_right, cmap=cmap)

    # Fatness — sagging belly fills the inter-leg gap pre-hibernation.
    if fatness > 0.25:
        fur_col = palette[0]
        for c in (8, 9, 10):
            dx = -10 + c
            _setp(px, x + d * dx, gy - 3, fur_col)
        if fatness > 0.65:
            for c in (8, 9, 10):
                dx = -10 + c
                _setp(px, x + d * dx, gy - 2, fur_col)


def _paint_bear_settling(px, x_center, fatness, dir_right, settle_frac):
    """Bear settles at the cave mouth before hibernation/sleep — uses the
    regular dwell sprite; the eye closes progressively. settle_frac ∈ [0,1]."""
    x = int(round(x_center))
    gy = GROUND_Y - 1
    d = 1 if dir_right else -1
    cmap = _bear_palette_map(MOMMA_PALETTE)
    fur, fur_dark, _, _, eye_col = MOMMA_PALETTE
    _paint_bitmap(px, x, gy, _BEAR_DWELL, row0_dy=-13, col0_dx=-10,
                  dir_right=dir_right, cmap=cmap)
    # Eye: wide open → half-lidded (dark) → closed (blends into fur).
    if settle_frac < 0.4:
        eye_overlay = eye_col
    elif settle_frac < 0.8:
        eye_overlay = fur_dark
    else:
        eye_overlay = fur
    _setp(px, x + d * 9, gy - 10, eye_overlay)


def _paint_bear_standing(px, x, fatness, d, palette=MOMMA_PALETTE):
    fur, fur_dark, fur_light, snout, eye = palette
    gy = GROUND_Y - 1
    fat = int(round(fatness * 1))
    body_w = 3 + fat
    # Belly (6 rows)
    for dy in range(-5, 1):
        for dx in range(-body_w, body_w + 1):
            if dy == -5 and abs(dx) == body_w:
                continue
            if dy == 0 and dx == 0:
                continue
            col = fur if dy > -5 else fur_dark
            _setp(px, x + dx, gy + dy, col)
    _setp(px, x - 1, gy, fur_dark)
    _setp(px, x + 1, gy, fur_dark)
    for dy in range(-8, -5):
        for dx in range(-2, 3):
            if dy == -8 and abs(dx) == 2:
                continue
            _setp(px, x + dx, gy + dy, fur)
    _setp(px, x - 2, gy - 9, fur_dark)
    _setp(px, x + 2, gy - 9, fur_dark)
    _setp(px, x + d, gy - 7, eye)
    _setp(px, x + 2 * d, gy - 6, snout)


# Cub sprite — half-scale momma silhouette. 12 wide × 9 tall.
# col 0 → dx=-6 (rump), col 11 → dx=+5 (nose). Head on RIGHT (matches momma).
# row 0 → dy=-8 (ear tip), row 8 → dy=0 (feet on ground line).
_CUB_WALK_A = (
    "....dd..dd..",   # -8  ears
    "...dfEdfEdd.",   # -7  ear bases
    "..ddffffffed",   # -6  head top + eye
    ".ddllllllffn",   # -5  light back + nose
    "dfllllllllff",   # -4  body w/ light back fading
    ".dfffffffffs",   # -3  body + snout cream
    ".dffffffffs.",   # -2  body bottom
    "..LL.LL.LL..",   # -1  legs row 1
    "..LL.LL.LL..",   # 0   feet
)
_CUB_WALK_B = (
    "....dd..dd..",
    "...dfEdfEdd.",
    "..ddffffffed",
    ".ddllllllffn",
    "dfllllllllff",
    ".dfffffffffs",
    ".dffffffffs.",
    ".LL.LL.LL...",   # legs shifted forward
    ".LL.LL.LL...",
)
_CUB_DWELL = _CUB_WALK_A


def _paint_cub(px, x_center, phase, dir_right, activity):
    """Cub — half-scale of momma. Same head-on-right convention; the 'e' and
    'n' chars in the bitmap put eye/nose where the cmap will paint them."""
    x = int(round(x_center))
    gy = GROUND_Y - 1
    cmap = _bear_palette_map(MOMMA_PALETTE)
    rows = _CUB_WALK_B if (activity == "walk" and (phase & 1)) else _CUB_DWELL
    _paint_bitmap(px, x, gy, rows, row0_dy=-8, col0_dx=-6,
                  dir_right=dir_right, cmap=cmap)


def _paint_heart(px, x, y):
    """Tiny 3-wide heart; core on petals + valley, edge on shoulders."""
    _setp(px, x - 1, y, HEART_CORE)
    _setp(px, x + 1, y, HEART_CORE)
    _setp(px, x, y, HEART_EDGE)
    _setp(px, x - 1, y + 1, HEART_CORE)
    _setp(px, x, y + 1, HEART_CORE)
    _setp(px, x + 1, y + 1, HEART_CORE)
    _setp(px, x, y + 2, HEART_CORE)


def _paint_sleeping_face(px, t):
    """Bear face peeking out of the cave, eyes closed, gently breathing."""
    cx = CAVE_X
    # Breathing: head bobs up/down by 1 px over ~1.5 s.
    breath = 1 if math.sin(t * 0.8) > 0 else 0
    top_y = CAVE_FLOOR_Y - 6 + breath
    # Head silhouette rows (relative to top_y)
    rows = (
        ((-2, -1, 0, 1, 2),),                    # row 0 — head cap
        ((-3, -2, -1, 0, 1, 2, 3),),             # row 1
        ((-4, -3, -2, -1, 0, 1, 2, 3, 4),),      # row 2 — widest
        ((-4, -3, -2, -1, 0, 1, 2, 3, 4),),      # row 3 — eyes row
        ((-4, -3, -2, -1, 0, 1, 2, 3, 4),),      # row 4 — snout row
        ((-3, -2, -1, 0, 1, 2, 3),),             # row 5 — chin
    )
    for dy, (xs,) in enumerate(rows):
        y = top_y + dy
        for dx in xs:
            _setp(px, cx + dx, y, BEAR_FUR)
    # Ears
    _setp(px, cx - 3, top_y - 1, BEAR_FUR_DARK)
    _setp(px, cx - 4, top_y, BEAR_FUR_DARK)
    _setp(px, cx + 3, top_y - 1, BEAR_FUR_DARK)
    _setp(px, cx + 4, top_y, BEAR_FUR_DARK)
    # Closed eyes — two tilde-like marks
    for (dx, dy) in ((-3, 3), (-2, 3), (-3, 2)):
        _setp(px, cx + dx, top_y + dy, BEAR_FUR_DARK)
    for (dx, dy) in ((2, 3), (3, 3), (3, 2)):
        _setp(px, cx + dx, top_y + dy, BEAR_FUR_DARK)
    # Snout
    for (dx, dy) in ((-1, 4), (0, 4), (1, 4)):
        _setp(px, cx + dx, top_y + dy, BEAR_SNOUT)
    _setp(px, cx, top_y + 4, BEAR_EYE)  # nose


def _paint_zzz(px, t):
    # Three drifting Zs at staggered phases, each a small stylized 'z'.
    x0 = CAVE_X + 5
    for i in range(3):
        phase = ((t * 0.35) + i * 0.33) % 1.0
        y = int(CAVE_TOP_Y - 3 - phase * 18)
        if y < 0 or y > CAVE_TOP_Y - 2:
            continue
        x = x0 + int(math.sin(phase * 6) * 2)
        # Fade as it rises
        fade = 1.0 - phase * 0.6
        col = (int(ZZZ_COLOR[0] * fade),
               int(ZZZ_COLOR[1] * fade),
               int(ZZZ_COLOR[2] * fade))
        for (dx, dy) in ((0, 0), (1, 0), (2, 0),
                         (1, 1),
                         (0, 2), (1, 2), (2, 2)):
            _setp(px, x + dx, y + dy, col)


# ── Wildlife ──────────────────────────────────────────────────────────────
RABBIT_TAIL = (240, 240, 245)


def _paint_rabbit(px, rabbit):
    x, y_bot, hop_phase, dir_ = rabbit
    up = 1 if 0.25 < hop_phase < 0.6 else 0
    x = int(x); y = int(y_bot) - up  # y is ground row
    # Body: 4 wide × 2 tall at rows y-1 (top, light) and y (bottom, dark).
    for dx in range(4):
        _setp(px, x + dx, y, RABBIT_FUR_DARK)
        _setp(px, x + dx, y - 1, RABBIT_FUR)
    # Head: 2 px wide, 1 tall, on the front-top. Eye on the front pixel.
    if dir_ > 0:
        head_front = x + 4
        head_back = x + 3
        tail_x = x - 1
        ear_front = head_front
        ear_back = head_back
    else:
        head_front = x - 1
        head_back = x
        tail_x = x + 4
        ear_front = head_front
        ear_back = head_back
    _setp(px, head_back, y - 2, RABBIT_FUR)
    _setp(px, head_front, y - 2, RABBIT_FUR)
    _setp(px, head_front, y - 2, (30, 25, 20))  # eye
    # Ears: 2 px tall, one straight up on the back-ear, one slightly
    # forward-leaning on the front-ear — classic alert-bunny silhouette.
    _setp(px, ear_back, y - 3, RABBIT_FUR_DARK)
    _setp(px, ear_back, y - 4, RABBIT_FUR_DARK)
    _setp(px, ear_front, y - 3, RABBIT_FUR_DARK)
    # Cotton tail on the back.
    _setp(px, tail_x, y - 1, RABBIT_TAIL)


def _paint_bird_flying(px, bird):
    x, y = int(bird[0]), int(bird[1])
    wing_phase = bird[4]
    if wing_phase < 0.5:
        _setp(px, x - 1, y - 1, BIRD_COLOR)
        _setp(px, x, y, BIRD_COLOR)
        _setp(px, x + 1, y - 1, BIRD_COLOR)
    else:
        _setp(px, x - 1, y + 1, BIRD_COLOR)
        _setp(px, x, y, BIRD_COLOR)
        _setp(px, x + 1, y + 1, BIRD_COLOR)


# ── Weather particles ─────────────────────────────────────────────────────
def _spawn_particle(weather):
    if weather == "rain":
        return [random.uniform(-4, WIDTH), random.uniform(-HEIGHT, -1),
                -4.0, 55.0, 0]
    if weather == "storm":
        return [random.uniform(-4, WIDTH), random.uniform(-HEIGHT, -1),
                -10.0, 80.0, 0]
    if weather == "snow":
        return [random.uniform(-4, WIDTH), random.uniform(-HEIGHT, -1),
                random.uniform(-3, 3), 8.0 + random.random() * 4, 1]
    if weather == "leaves":
        # Spawn from tree foliage, not the whole sky.
        tx = random.choice(TREE_XS) + 1  # +1 matches tree cx in _paint_trees
        x = tx + random.uniform(-TREE_FOLIAGE_RX, TREE_FOLIAGE_RX)
        y = TREE_FOLIAGE_CY + random.uniform(-TREE_FOLIAGE_RY, TREE_FOLIAGE_RY)
        return [x, y, random.uniform(-10, 2), 10.0 + random.random() * 6, 2]
    if weather == "blossom":
        tx = random.choice(TREE_XS) + 1
        x = tx + random.uniform(-TREE_FOLIAGE_RX, TREE_FOLIAGE_RX)
        y = TREE_FOLIAGE_CY + random.uniform(-TREE_FOLIAGE_RY, TREE_FOLIAGE_RY)
        return [x, y, random.uniform(-2, 2), 4.0 + random.random() * 3, 3]
    return None


def _update_particles(particles, weather, dt):
    alive = []
    for p in particles:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        if p[4] in (1, 2):
            p[2] += (random.random() - 0.5) * 6.0 * dt
            if p[2] > 10: p[2] = 10
            if p[2] < -10: p[2] = -10
        if p[1] >= GROUND_Y or p[0] < -6 or p[0] > WIDTH + 6:
            continue
        alive.append(p)
    target = PARTICLE_COUNT.get(weather, 0)
    while len(alive) < target:
        np = _spawn_particle(weather)
        if np is None:
            break
        alive.append(np)
    particles[:] = alive


LEAF_COLORS = ((220, 120, 40), (200, 90, 30), (255, 170, 60))
BLOSSOM_COLORS = ((255, 200, 220), (255, 170, 200))


def _paint_particles(px, particles):
    for p in particles:
        x, y, k = int(p[0]), int(p[1]), p[4]
        if k == 0:
            _setp(px, x, y, (100, 160, 220))
            _setp(px, x, y - 1, (70, 120, 180))
        elif k == 1:
            _setp(px, x, y, (240, 245, 255))
        elif k == 2:
            _setp(px, x, y, LEAF_COLORS[(x + y) % 3])
        elif k == 3:
            _setp(px, x, y, BLOSSOM_COLORS[(x + y) & 1])


# ── Program ───────────────────────────────────────────────────────────────
class BearDen(Program):
    DESCRIPTION = "12-min year, 8 days, diurnal bear with weather & seasons"

    def setup(self) -> None:
        self.year = float(self.params.get("year", YEAR_LENGTH))
        start = self.params.get("start", "spring").lower()
        try:
            start_season = SEASON_NAMES.index(start)
        except ValueError:
            start_season = 0
        self._t = start_season * self.year / 4 + 1.0

        self.bear_x = float(CAVE_X + 8)
        self.bear_dir = 1
        self.bear_target = 32.0
        self.bear_state = "walk"   # walk|dwell|eat|stand|pre_sleep|night_sleep|hibernate
        self.dwell_left = 0.0
        self._sleep_target = "night_sleep"
        self._phase_acc = 0.0
        self.phase = 0

        self._weather = "calm"
        self._weather_t = 0.0
        self._settle_total = 2.6
        self._particles: list[list[float]] = []

        self._clouds: list[list[float]] = []
        self._rabbits: list[list[float]] = []
        self._rabbit_spawn_t = 3.0
        self._birds: list[list[float]] = []
        self._bird_spawn_t = 4.0
        self._perches: list[tuple[int, int, int]] = []
        self._perch_t = 0.0

        # Lightning state
        self._lightning_timer = float('inf')
        self._strike_t = 10.0
        self._bolt_seed = 0

        # Family arc: papa bear visits mid-summer; cub emerges from
        # cave on a night in early autumn and follows momma until winter.
        self._year_count = 0
        self._papa_state = "away"      # away|arriving|courting|leaving
        self._papa_x = float(WIDTH + 6)
        self._papa_dir = -1
        self._papa_phase = 0
        self._papa_phase_acc = 0.0
        self._papa_court_t = 0.0
        self._papa_visited = False
        self._cub_state = "absent"     # absent|emerging|active|departing
        self._cub_x = float(CAVE_X)
        self._cub_dir = 1
        self._cub_phase = 0
        self._cub_phase_acc = 0.0
        self._cub_emerge_t = 0.0
        self._cub_emerged = False
        self._hearts: list[list[float]] = []

    # Derived state ────────────────────────────────────────────────────────
    @property
    def year_frac(self) -> float:
        return (self._t % self.year) / self.year

    @property
    def day_frac(self) -> float:
        return (self._t % DAY_LENGTH) / DAY_LENGTH

    @property
    def season(self) -> int:
        return min(3, int(self.year_frac * 4))

    @property
    def fatness(self) -> float:
        yf = self.year_frac
        if yf < 0.25:
            return yf * 0.4
        if yf < 0.5:
            return 0.1 + (yf - 0.25) * 1.8
        if yf < 0.75:
            return 0.55 + (yf - 0.5) * 1.8
        return 1.0

    def _is_night(self) -> bool:
        return self.day_frac >= SUN_END

    def _choose_weather(self) -> str:
        table = WEATHER_TABLE[self.season]
        r = random.random()
        for name, cum in table:
            if r < cum:
                return name
        return table[-1][0]

    def _pick_target(self) -> float:
        s = self.season
        if s == 3:
            return float(CAVE_X)
        pool = [22.0, 30.0, 36.0, 44.0, 48.0, 52.0]
        if s == 1:
            pool.extend([float(BERRY_X)] * 2)
        if s == 2:
            pool.extend([float(BERRY_X)] * 2)
            pool.extend(float(tx) for tx in TREE_XS)
        return _clamp(random.choice(pool), BEAR_MIN_X, BEAR_MAX_X)

    def _food_near(self, x: float) -> bool:
        if self.season in (1, 2) and abs(x - BERRY_X) < 4:
            return True
        if self.season == 2 and any(abs(x - tx) < 3 for tx in TREE_XS):
            return True
        return False

    # Bear brain ───────────────────────────────────────────────────────────
    def _step_bear(self, dt: float) -> None:
        # Winter: hibernate full season.
        if self.season == 3:
            if self.bear_state in ("hibernate", "pre_sleep"):
                pass
            elif abs(self.bear_x - CAVE_X) < 1:
                self.bear_state = "pre_sleep"
                self.dwell_left = 2.6
                self._settle_total = 2.6
                self._sleep_target = "hibernate"
            else:
                self.bear_target = float(CAVE_X)
                self.bear_state = "walk"
        else:
            # Wake from prior hibernation or night sleep.
            if self.bear_state in ("hibernate", "night_sleep") and not self._is_night():
                self.bear_state = "walk"
                self.bear_x = float(CAVE_X + 6)
                self.bear_target = self._pick_target()
            elif self._is_night() and self.bear_state not in ("night_sleep", "pre_sleep"):
                if abs(self.bear_x - CAVE_X) < 1:
                    self.bear_state = "pre_sleep"
                    self.dwell_left = 1.4
                    self._sleep_target = "night_sleep"
                else:
                    self.bear_target = float(CAVE_X)
                    self.bear_state = "walk"

        # Pre-sleep: bear sits at cave mouth briefly before the face swaps in.
        if self.bear_state == "pre_sleep":
            self.dwell_left -= dt
            if self.dwell_left <= 0:
                self.bear_state = self._sleep_target
            return
        if self.bear_state == "hibernate":
            return

        # Process active states (walk / dwell / eat / stand / sleep).
        if self.bear_state == "walk":
            dx = self.bear_target - self.bear_x
            if abs(dx) < 0.5:
                # Arrived
                if self._is_night() and abs(self.bear_x - CAVE_X) < 2:
                    self.bear_state = "night_sleep"
                    return
                if self._food_near(self.bear_x) and not self._is_night():
                    self.bear_state = "eat"
                    self.dwell_left = random.uniform(2.5, 5.5)
                elif random.random() < 0.06 and not self._is_night():
                    self.bear_state = "stand"
                    self.dwell_left = random.uniform(1.5, 3.0)
                else:
                    self.bear_state = "dwell"
                    self.dwell_left = random.uniform(1.2, 3.5)
                return
            self.bear_dir = 1 if dx > 0 else -1
            speed = BEAR_BASE_SPEED * (1.0 - 0.35 * self.fatness)
            self.bear_x += self.bear_dir * speed * dt
            self.bear_x = _clamp(self.bear_x, BEAR_MIN_X, BEAR_MAX_X)
            self._phase_acc += dt * 4.0
            while self._phase_acc >= 1.0:
                self._phase_acc -= 1.0
                self.phase = (self.phase + 1) & 3
        elif self.bear_state in ("dwell", "stand"):
            self.dwell_left -= dt
            if self.dwell_left <= 0:
                self.bear_target = float(CAVE_X) if self._is_night() else self._pick_target()
                self.bear_state = "walk"
        elif self.bear_state == "eat":
            self.dwell_left -= dt
            self._phase_acc += dt * 3.0
            while self._phase_acc >= 1.0:
                self._phase_acc -= 1.0
                self.phase = (self.phase + 1) & 3
            if self.dwell_left <= 0:
                self.bear_target = float(CAVE_X) if self._is_night() else self._pick_target()
                self.bear_state = "walk"

    # Clouds / rabbits / birds / lightning ─────────────────────────────────
    def _update_clouds(self, dt: float) -> None:
        target = CLOUD_COUNT.get(self._weather, 2)
        self._clouds = [c for c in self._clouds if c[0] > -8]
        for c in self._clouds:
            c[0] += c[3] * dt
        while len(self._clouds) < target:
            if self._weather == "storm":
                shape_idx = 1 if random.random() < 0.7 else 0  # mostly big
            elif self._weather == "rain":
                shape_idx = random.choice((0, 1, 1))
            else:
                shape_idx = random.randrange(len(CLOUD_SHAPES))
            self._clouds.append([
                float(WIDTH + random.randint(0, 20)),
                float(random.randint(3, 18)),
                shape_idx,
                -random.uniform(1.2, 3.0),
            ])

    def _update_rabbits(self, dt: float) -> None:
        new = []
        for r in self._rabbits:
            r[0] += r[3] * 11.0 * dt
            r[2] = (r[2] + dt * 2.2) % 1.0
            if -4 < r[0] < WIDTH + 4:
                new.append(r)
        self._rabbits = new
        self._rabbit_spawn_t -= dt
        if self._rabbit_spawn_t <= 0:
            # No rabbits in winter or at night. Rarer than before —
            # 2-3 visible per day feels like "oh look, a bunny" rather
            # than a parade.
            if (self.season != 3 and not self._is_night()
                    and len(self._rabbits) < 2 and random.random() < 0.5):
                direction = random.choice((-1, 1))
                x = -3 if direction > 0 else WIDTH + 3
                self._rabbits.append([float(x), float(GROUND_Y - 1),
                                      random.random(), float(direction)])
            self._rabbit_spawn_t = random.uniform(12.0, 28.0)

    def _update_birds(self, dt: float) -> None:
        new = []
        for b in self._birds:
            b[0] += b[2] * dt
            b[1] += math.sin(self._t * 4 + b[5]) * 0.3 * dt + b[3] * dt
            b[4] = (b[4] + dt * 5.0) % 1.0
            if -4 < b[0] < WIDTH + 4 and b[1] < GROUND_Y - 2:
                new.append(b)
        self._birds = new
        self._bird_spawn_t -= dt
        if self._bird_spawn_t <= 0:
            if self.season != 3 and not self._is_night() and random.random() < 0.5:
                direction = random.choice((-1, 1))
                x = -3 if direction > 0 else WIDTH + 3
                y = random.randint(5, 22)
                vx = direction * random.uniform(6, 12)
                self._birds.append([float(x), float(y), float(vx), 0.0,
                                    random.random(), random.random() * 6.28])
            self._bird_spawn_t = random.uniform(5.0, 12.0)

        # Perched birds — regenerate periodically
        self._perch_t -= dt
        if self._perch_t <= 0:
            self._perches = []
            if self.season != 3 and not self._is_night() and random.random() < 0.7:
                for tx in TREE_XS:
                    if random.random() < 0.4:
                        self._perches.append(
                            (tx, tx + random.randint(-3, 3),
                             GROUND_Y - TREE_TRUNK_H - 2 + random.randint(-3, 1))
                        )
            self._perch_t = random.uniform(4.0, 10.0)

    def _update_lightning(self, dt: float) -> None:
        self._strike_t += dt
        if self._weather == "storm":
            if self._lightning_timer == float('inf'):
                self._lightning_timer = random.uniform(2.5, 6.0)
            self._lightning_timer -= dt
            if self._lightning_timer <= 0:
                self._lightning_timer = random.uniform(4.0, 12.0)
                self._strike_t = 0.0
                self._bolt_seed = random.randint(1, 1_000_000)
        else:
            self._lightning_timer = float('inf')

    def _flash_amount(self) -> float:
        # Double-peaked flash for the "strobe" look of a lightning strike.
        t = self._strike_t
        if t > 0.45:
            return 0.0
        # Initial burst 0→0.08s, dip 0.08→0.14, second flash 0.14→0.25, decay to 0.45
        if t < 0.08:
            return t / 0.08
        if t < 0.14:
            return 1.0 - (t - 0.08) / 0.06 * 0.6
        if t < 0.25:
            return 0.4 + (t - 0.14) / 0.11 * 0.6
        return max(0.0, 1.0 - (t - 0.25) / 0.20)

    def _bolt_visible(self) -> bool:
        return self._weather == "storm" and self._strike_t < 0.12

    # Papa bear / cub / hearts ─────────────────────────────────────────────
    def _step_papa(self, dt: float) -> None:
        yf = self.year_frac
        ps = self._papa_state
        if ps == "away":
            # Arrive once per year in late summer, daytime, when momma is
            # visibly chunkier than in spring.
            if (0.42 < yf < 0.45 and not self._papa_visited
                    and not self._is_night()
                    and self.bear_state in ("walk", "dwell", "eat", "stand")):
                self._papa_state = "arriving"
                self._papa_x = float(WIDTH + 6)
                self._papa_dir = -1
                self._papa_visited = True
            return
        if ps == "arriving":
            speed = BEAR_BASE_SPEED * 0.95
            self._papa_x += self._papa_dir * speed * dt
            self._papa_phase_acc += dt * 4.0
            while self._papa_phase_acc >= 1.0:
                self._papa_phase_acc -= 1.0
                self._papa_phase = (self._papa_phase + 1) & 3
            if self._papa_x <= self.bear_x + 9:
                self._papa_state = "courting"
                self._papa_court_t = 18.0
            return
        if ps == "courting":
            self._papa_court_t -= dt
            # Spawn hearts between momma and papa — about 5 per second.
            if random.random() < 5.0 * dt:
                cx = (self.bear_x + self._papa_x) / 2 + random.uniform(-3, 3)
                cy = float(GROUND_Y - 6 + random.randint(-3, 0))
                # kind=4 heart; vy negative = rising; vx = small sway.
                self._hearts.append([cx, cy, random.uniform(-2, 2), -10.0,
                                     1.5, 4])
            if self._papa_court_t <= 0 or self._is_night():
                self._papa_state = "leaving"
            return
        if ps == "leaving":
            speed = BEAR_BASE_SPEED * 1.05
            self._papa_x += self._papa_dir * speed * dt
            self._papa_phase_acc += dt * 4.0
            while self._papa_phase_acc >= 1.0:
                self._papa_phase_acc -= 1.0
                self._papa_phase = (self._papa_phase + 1) & 3
            if self._papa_x < -8 or self._papa_x > WIDTH + 8:
                self._papa_state = "away"

    def _step_cub(self, dt: float) -> None:
        yf = self.year_frac
        cs = self._cub_state
        if cs == "absent":
            # Cub emerges from the cave on a night in early autumn, only
            # after papa has visited so the story order is papa → cub.
            if (0.55 < yf < 0.58 and self._is_night() and not self._cub_emerged
                    and self._papa_visited):
                self._cub_state = "emerging"
                self._cub_x = float(CAVE_X)
                self._cub_dir = 1
                self._cub_emerge_t = 2.5
                self._cub_emerged = True
            return
        if cs == "emerging":
            # Cub peeks out of cave then totters forward toward momma.
            self._cub_emerge_t -= dt
            if self._cub_emerge_t <= 1.5:
                # Start slowly walking out of cave.
                self._cub_x += 1.8 * dt
                self._cub_phase_acc += dt * 3.0
                while self._cub_phase_acc >= 1.0:
                    self._cub_phase_acc -= 1.0
                    self._cub_phase = (self._cub_phase + 1) & 3
            if self._cub_emerge_t <= 0:
                self._cub_state = "active"
            return
        if cs == "active":
            # Follow momma: target = 4 px behind her based on her facing.
            target_x = self.bear_x - self.bear_dir * 5
            target_x = _clamp(target_x, BEAR_MIN_X, BEAR_MAX_X)
            dx = target_x - self._cub_x
            if abs(dx) > 1.0:
                self._cub_dir = 1 if dx > 0 else -1
                speed = BEAR_BASE_SPEED * 0.85
                self._cub_x += self._cub_dir * speed * dt
                self._cub_phase_acc += dt * 4.5
                while self._cub_phase_acc >= 1.0:
                    self._cub_phase_acc -= 1.0
                    self._cub_phase = (self._cub_phase + 1) & 3
            # Grown up + wanders off-screen near end of autumn.
            if yf > 0.72:
                self._cub_state = "departing"
                self._cub_dir = 1 if self._cub_x < WIDTH / 2 else -1
            return
        if cs == "departing":
            self._cub_x += self._cub_dir * BEAR_BASE_SPEED * 0.9 * dt
            self._cub_phase_acc += dt * 4.5
            while self._cub_phase_acc >= 1.0:
                self._cub_phase_acc -= 1.0
                self._cub_phase = (self._cub_phase + 1) & 3
            if self._cub_x < -6 or self._cub_x > WIDTH + 6:
                self._cub_state = "absent"

    def _update_hearts(self, dt: float) -> None:
        alive = []
        for h in self._hearts:
            h[0] += h[2] * dt
            h[1] += h[3] * dt
            h[4] -= dt
            # Gentle sideways wobble while rising.
            h[2] += math.sin((h[1] + h[0]) * 0.3) * 4.0 * dt
            if h[4] > 0 and h[1] > -4:
                alive.append(h)
        self._hearts = alive

    def _tick_year(self) -> None:
        cur_year = int(self._t // self.year)
        if cur_year != self._year_count:
            self._year_count = cur_year
            self._papa_visited = False
            self._cub_emerged = False

    # Main loop ────────────────────────────────────────────────────────────
    def update(self, dt: float, events) -> None:
        self._t += dt

        self._weather_t -= dt
        if self._weather_t <= 0:
            self._weather = self._choose_weather()
            self._weather_t = WEATHER_CHANGE_S + random.uniform(-10, 10)

        self._tick_year()
        self._step_bear(dt)
        self._step_papa(dt)
        self._step_cub(dt)
        self._update_hearts(dt)
        _update_particles(self._particles, self._weather, dt)
        self._update_clouds(dt)
        self._update_rabbits(dt)
        self._update_birds(dt)
        self._update_lightning(dt)

    def render(self) -> Frame:
        f = Frame.black()
        px = f.pixels

        # Palette (season cross-fade)
        year_frac = self.year_frac
        cur, nxt, blend = _year_state(year_frac)
        sky_top, sky_hor = _blend_sky(cur, nxt, blend)
        gnd_top, gnd_bot = _blend_ground(cur, nxt, blend)
        rock_top, rock_bot = _blend_rock(cur, nxt, blend)
        foliage = _blend_foliage(cur, nxt, blend)

        # Time / day cycle
        day_frac = self.day_frac
        night_level, is_day, phase = _day_phases(day_frac)

        # Paint layers
        _paint_sky(px, sky_top, sky_hor, night_level, day_frac, self._weather)
        _paint_stars(px, night_level, self._t)
        # Clouds split by altitude so lightning can render between them:
        # high clouds (back, low cy) paint first, then bolt, then low clouds.
        cloud_color = _cloud_color(night_level, day_frac, self._weather)
        cloud_shade = _lerp_rgb(cloud_color, CLOUD_NIGHT, 0.3)
        back_clouds = [(c[0], c[1], int(c[2])) for c in self._clouds if c[1] < 11]
        front_clouds = [(c[0], c[1], int(c[2])) for c in self._clouds if c[1] >= 11]
        _paint_clouds(px, back_clouds, cloud_color, cloud_shade)
        # One full lunar cycle per year = 8 phases × DAYS_PER_MOON_PHASE days.
        moon_phase_idx = (int(self._t / DAY_LENGTH)
                          // DAYS_PER_MOON_PHASE) % MOON_PHASES
        # Hide the sun behind a heavy storm — too much cloud cover.
        if not (is_day and self._weather == "storm"):
            _paint_sun_or_moon(px, is_day, phase, moon_phase_idx)
        if self._bolt_visible():
            _paint_lightning_bolt(px, self._bolt_seed)
        _paint_clouds(px, front_clouds, cloud_color, cloud_shade)

        _paint_ground(px, gnd_top, gnd_bot)
        _paint_hill_cave(px, rock_top, rock_bot)
        _paint_flowers_and_grass(px, year_frac)
        # Berry season: summer (cur=1) or autumn (cur=2), with fade through blend
        is_berry = (cur in (1, 2)) or (nxt in (1, 2) and blend > 0.3)
        _paint_berry_bush(px, is_berry, self._weather == "storm")
        _paint_trees(px, year_frac, foliage, self._perches,
                     is_winter_like=(cur == 3 and blend < 0.5) or (cur == 2 and blend > 0.5))

        for r in self._rabbits:
            _paint_rabbit(px, r)

        if self.bear_state in ("hibernate", "night_sleep"):
            _paint_sleeping_face(px, self._t)
            _paint_zzz(px, self._t)
        elif self.bear_state == "pre_sleep":
            settle_frac = 1.0 - _clamp(self.dwell_left / self._settle_total, 0.0, 1.0)
            _paint_bear_settling(px, self.bear_x, self.fatness,
                                 self.bear_dir > 0, settle_frac)
        else:
            _paint_bear(px, self.bear_x, self.phase, self.fatness,
                        self.bear_dir > 0, self.bear_state)

        # Papa bear: courting pose faces momma; otherwise faces travel dir.
        if self._papa_state != "away":
            if self._papa_state == "courting":
                papa_faces_right = self.bear_x > self._papa_x
            else:
                papa_faces_right = self._papa_dir > 0
            papa_activity = "walk" if self._papa_state in ("arriving", "leaving") else "dwell"
            _paint_bear(px, self._papa_x, self._papa_phase, 0.8,
                        papa_faces_right, papa_activity,
                        palette=PAPA_PALETTE, rx_bonus=1)

        # Cub: emerging cub is drawn as a small silhouette peeking out; active
        # cub trots in the scene.
        if self._cub_state == "emerging":
            # Cub peeks from cave — same position as cave mouth, small body
            # that grows with emerge progress.
            progress = 1.0 - _clamp(self._cub_emerge_t / 2.5, 0.0, 1.0)
            if progress > 0.15:
                _paint_cub(px, self._cub_x, self._cub_phase,
                           self._cub_dir > 0, "dwell")
        elif self._cub_state in ("active", "departing"):
            _paint_cub(px, self._cub_x, self._cub_phase,
                       self._cub_dir > 0, "walk")

        # Hearts float above the courting pair.
        for h in self._hearts:
            _paint_heart(px, int(h[0]), int(h[1]))

        for b in self._birds:
            _paint_bird_flying(px, b)

        _paint_particles(px, self._particles)

        # Post: night dim (everything) + lightning flash (additive) via a
        # single byte-translation table — very fast.
        dim = 1.0 - 0.55 * night_level
        flash = self._flash_amount()
        if dim < 1.0 or flash > 0:
            flash_add = int(flash * 110)
            table = bytes(
                _clamp255(int(i * dim) + flash_add) for i in range(256)
            )
            f.pixels[:] = f.pixels.translate(table)

        return f
