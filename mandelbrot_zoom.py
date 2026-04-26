"""Algorithmic Mandelbrot zoom tour on the Pixoo-64.

First run: scans ~2000 points in the complex plane, scores each by local
detail at deep zoom, dedupes, caches top 50 to /tmp/mandelbrot_targets.json.
Subsequent runs load from cache.

Each run picks N targets from the cache and zooms into each for 30s at 4fps,
rotating through 5 muted palettes.
"""
from __future__ import annotations

import base64
import json
import os
import random
import sys
import threading
import time
import urllib.request
from typing import Tuple

import numpy as np

IP = "192.168.4.111"
W = H = 64
TARGET_FPS = 4.0
SECONDS_PER_TARGET = 30.0
FRAMES_PER_TARGET = int(TARGET_FPS * SECONDS_PER_TARGET)
START_HALF_WIDTH = 1.8
END_HALF_WIDTH = 1e-5
NUM_IN_TOUR = 10

# Bursty renderer: hold up to 40 min of frames, refill when down to 10 min.
# Each refill adds ~30 min of content in ~1 min of hot CPU; then the renderer
# sleeps ~29 min. Trades ~150MB RAM for a near-idle laptop most of the time.
MAX_BUFFER_MINUTES = 40.0
REFILL_THRESHOLD_MINUTES = 10.0
MAX_BUFFER_FRAMES = int(MAX_BUFFER_MINUTES * 60 * TARGET_FPS)
REFILL_THRESHOLD_FRAMES = int(REFILL_THRESHOLD_MINUTES * 60 * TARGET_FPS)

CACHE_FILE = "/tmp/mandelbrot_targets.json"
DOUBLES_CACHE_FILE = "/tmp/mandelbrot_doublebrots_v3.json"
SCAN_SAMPLES = 2000
SCAN_KEEP = 50
SCAN_MIN_SEP = 0.02             # min distance between kept candidates

BAILOUT_MAG2 = 256.0
CYCLE = 4.0
BRIGHTNESS = 0.75

# 6 muted palettes. Each is a set of stops (dark → light) interpolated via a
# triangle-fold so the loop is dark-light-dark, no hue-rainbow cycling.
PALETTES = [
    ("ice", np.array([
        [ 10,  18,  38], [ 22,  52,  92], [ 55, 120, 150],
        [150, 195, 210], [232, 234, 218],
    ], dtype=np.float64)),
    ("ember", np.array([
        [ 18,  10,   8], [ 70,  22,  18], [140,  58,  30],
        [210, 135,  70], [245, 225, 190],
    ], dtype=np.float64)),
    ("sage", np.array([
        [ 14,  22,  18], [ 38,  68,  50], [ 90, 130,  90],
        [170, 195, 150], [235, 238, 215],
    ], dtype=np.float64)),
    ("dusk", np.array([
        [ 24,  18,  38], [ 60,  52,  92], [130, 100, 130],
        [200, 160, 160], [240, 225, 210],
    ], dtype=np.float64)),
    ("mono-warm", np.array([
        [ 20,  18,  15], [ 65,  55,  45], [130, 110,  85],
        [195, 175, 140], [240, 230, 210],
    ], dtype=np.float64)),
    # Desaturated rainbow — hits every hue but at ~45% sat so it stays chill.
    ("rainbow-mute", np.array([
        [ 40,  22,  32], [110,  58,  48], [150, 130,  58],
        [ 70, 130,  90], [ 60,  90, 150], [130,  80, 150],
        [215, 195, 210],
    ], dtype=np.float64)),
]

# Double palettes: concatenate two single palettes into one long LUT so a
# single triangle-fold walks through both in sequence. Used when the tour
# slot is a "double-deep" mini-brot, to match more drama with more color.
DOUBLE_PALETTES = [
    ("ice+ember",     np.vstack([PALETTES[0][1], PALETTES[1][1]])),
    ("sage+dusk",     np.vstack([PALETTES[2][1], PALETTES[3][1]])),
    ("ember+mono",    np.vstack([PALETTES[1][1], PALETTES[4][1]])),
    ("ice+rainbow",   np.vstack([PALETTES[0][1], PALETTES[5][1]])),
    ("rainbow+sage",  np.vstack([PALETTES[5][1], PALETTES[2][1]])),
]


def post(payload: dict, timeout: float = 10.0) -> None:
    req = urllib.request.Request(
        f"http://{IP}/post",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read()


def prime() -> None:
    post({"Command": "Channel/SetIndex", "SelectIndex": 3})
    post({"Command": "Draw/ResetHttpGifId"})


def mandel_iter(C: np.ndarray, max_iter: int) -> tuple[np.ndarray, np.ndarray]:
    """Return (esc, final_mag2). esc = max_iter if never escaped."""
    Z = np.zeros_like(C)
    esc = np.full(C.shape, float(max_iter), dtype=np.float64)
    final_mag2 = np.zeros(C.shape, dtype=np.float64)
    alive = np.ones(C.shape, dtype=bool)
    for i in range(max_iter):
        Z[alive] = Z[alive] * Z[alive] + C[alive]
        mag2 = Z.real * Z.real + Z.imag * Z.imag
        newly = alive & (mag2 > BAILOUT_MAG2)
        if newly.any():
            esc[newly] = i
            final_mag2[newly] = mag2[newly]
            alive &= ~newly
        if not alive.any():
            break
    return esc, final_mag2


def newton_nucleus(seed_c: complex, period: int,
                   max_iter: int = 80, tol: float = 1e-14) -> complex | None:
    """Newton-iterate to a period-p nucleus. Returns c or None if diverges."""
    c = seed_c
    for _ in range(max_iter):
        z, d = 0 + 0j, 0 + 0j
        for _ in range(period):
            d = 2 * z * d + 1
            z = z * z + c
        if abs(d) < 1e-18 or abs(c) > 4:
            return None
        dc = z / d
        c -= dc
        if abs(dc) < tol:
            break
    # Verify converged to a genuine root
    z = 0 + 0j
    for _ in range(period):
        z = z * z + c
    return c if abs(z) < 1e-8 else None


def actual_period(c: complex, max_p: int) -> int | None:
    z = 0 + 0j
    for i in range(1, max_p + 1):
        z = z * z + c
        if abs(z) < 1e-6:
            return i
    return None


def find_nuclei(min_period: int = 3, max_period: int = 9,
                seeds_per_period: int = 400, dedup_tol: float = 1e-5,
                seed: int = 1) -> list[tuple[int, complex]]:
    """Return [(period, c), ...] — one entry per unique mini-brot nucleus."""
    rng = np.random.default_rng(seed)
    found: list[tuple[int, complex]] = []
    for p in range(min_period, max_period + 1):
        n_this = 0
        for _ in range(seeds_per_period):
            s = complex(rng.uniform(-2.0, 0.5), rng.uniform(-1.1, 1.1))
            c = newton_nucleus(s, p)
            if c is None:
                continue
            if abs(c.real) > 2.0 or abs(c.imag) > 1.3:
                continue
            true_p = actual_period(c, p)
            if true_p != p:
                continue
            if any(abs(c - c2) < dedup_tol for _, c2 in found):
                continue
            found.append((p, c))
            n_this += 1
        print(f"  period {p}: {n_this} nuclei", flush=True)
    return found


def find_landing_depth(cx: float, cy: float, target_ext: float = 0.5,
                       tol: float = 0.2, grid: int = 32,
                       n_levels: int = 60) -> tuple[float | None, float]:
    """Find the half-width at which the mini-brot 'lands' in the frame.

    Scans log-spaced halves from START_HALF_WIDTH down to 1e-10. Picks the
    depth whose exterior fraction is closest to `target_ext`. Returns
    (None, _) if no level is within `tol` of the target (nucleus doesn't
    produce a visually partial frame — e.g. we're flying through empty
    space or straight into interior).
    """
    halves = np.geomspace(START_HALF_WIDTH, 1e-10, n_levels)
    best_half: float | None = None
    best_ext = 0.0
    best_diff = 2.0
    for half in halves:
        zf = START_HALF_WIDTH / half
        mi = min(1500, int(80 + 120 * np.log10(max(1.0, zf))))
        xs = np.linspace(cx - half, cx + half, grid, dtype=np.float64)
        ys = np.linspace(cy - half, cy + half, grid, dtype=np.float64)
        C = xs[None, :] + 1j * ys[:, None]
        _, fm2 = mandel_iter(C, mi)
        ext = float((fm2 > BAILOUT_MAG2).mean())
        diff = abs(ext - target_ext)
        if diff < best_diff:
            best_diff = diff
            best_half = float(half)
            best_ext = ext
    if best_diff > tol:
        return None, best_ext
    return best_half, best_ext


def scan_targets(**_: object) -> list[tuple[str, float, float, float, float]]:
    """Find mini-brot nuclei, pick the arrival depth for each (where the
    mini-brot lands in-frame at ~50% exterior fill), return targets."""
    print("finding mini-brot nuclei via Newton iteration...", flush=True)
    t0 = time.monotonic()
    nuclei = find_nuclei()
    print(f"  total: {len(nuclei)} unique nuclei "
          f"(periods {min(p for p,_ in nuclei)}–{max(p for p,_ in nuclei)})",
          flush=True)

    print("picking arrival depth (ext frac ≈ 0.5) per nucleus...", flush=True)
    targets: list[tuple[str, float, float, float, float]] = []
    rejected = 0
    for idx, (p, c) in enumerate(nuclei):
        h, ext = find_landing_depth(c.real, c.imag)
        if h is None:
            rejected += 1
            continue
        targets.append((f"p{p:02d}-{idx:03d}", c.real, c.imag, h, float(p)))

    # Rank: deeper zoom (smaller h) first → more dramatic
    targets.sort(key=lambda t: t[3])
    print(f"  {len(targets)} targets kept, {rejected} rejected in "
          f"{time.monotonic()-t0:.1f}s", flush=True)
    print(f"  depth range: {targets[0][3]:.1e} .. {targets[-1][3]:.1e}",
          flush=True)
    return targets


def find_doublebrots(parents: list[tuple[str, float, float, float, float]],
                     seeds_per_parent: int = 96
                     ) -> list[tuple[str, float, float, float, float]]:
    """For each parent mini-brot, search its neighborhood for a sub-mini-brot
    at periods `parent_period + 3..+4` via Newton. Keep those that land
    meaningfully deeper than the parent AND within ~half a screen of the
    parent (so the pan from parent to child is visually tight, not a
    cross-screen teleport).
    """
    doubles: list[tuple[str, float, float, float, float]] = []
    for idx, (_, pcx, pcy, p_half, p_period_f) in enumerate(parents):
        p_period = int(p_period_f)
        seed_window = p_half * 2.0           # broad enough to seed Newton
        accept_dist = p_half * 0.7           # pan ≤ ~0.35 screen at p_half
        rng = np.random.default_rng(idx + 10_000)
        for gap in (3, 4):
            sub_p = p_period + gap
            if sub_p > 14:
                continue
            for _ in range(seeds_per_parent):
                s = complex(pcx + rng.uniform(-seed_window, seed_window),
                            pcy + rng.uniform(-seed_window, seed_window))
                c = newton_nucleus(s, sub_p)
                if c is None:
                    continue
                if abs(c.real) > 2.0 or abs(c.imag) > 1.3:
                    continue
                if (abs(c.real - pcx) > accept_dist
                        or abs(c.imag - pcy) > accept_dist):
                    continue
                if actual_period(c, sub_p) != sub_p:
                    continue
                if any(abs(c.real - d[4]) < 1e-7 and abs(c.imag - d[5]) < 1e-7
                       for d in doubles):
                    continue
                h, _ = find_landing_depth(c.real, c.imag)
                if h is None or h > p_half * 0.3:
                    continue
                doubles.append((
                    f"d{sub_p:02d}-{idx:03d}",
                    float(pcx), float(pcy), float(p_half),        # parent
                    float(c.real), float(c.imag), float(h),       # child
                    float(sub_p),
                ))
                break  # one sub-brot per (parent, gap) is plenty
        if (idx + 1) % 50 == 0:
            print(f"  scanned {idx+1}/{len(parents)} parents, "
                  f"{len(doubles)} doubles so far", flush=True)
    doubles.sort(key=lambda t: t[6])   # sort by child landing depth
    return doubles


def load_or_scan() -> tuple[list, list]:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            targets = [tuple(t) for t in json.load(f)]
    else:
        targets = scan_targets()
        with open(CACHE_FILE, "w") as f:
            json.dump(targets, f, indent=1)

    if os.path.exists(DOUBLES_CACHE_FILE):
        with open(DOUBLES_CACHE_FILE) as f:
            doubles = [tuple(t) for t in json.load(f)]
    else:
        print("scanning double-deep mini-brots near each parent...",
              flush=True)
        t0 = time.monotonic()
        doubles = find_doublebrots(targets)
        print(f"  {len(doubles)} doubles in {time.monotonic()-t0:.1f}s",
              flush=True)
        if doubles:
            print(f"  child depth range: {doubles[0][6]:.1e} .. "
                  f"{doubles[-1][6]:.1e}", flush=True)
        with open(DOUBLES_CACHE_FILE, "w") as f:
            json.dump(doubles, f, indent=1)
    return targets, doubles


def render(cx: float, cy: float, half: float, max_iter: int,
           palette: np.ndarray) -> bytes:
    xs = np.linspace(cx - half, cx + half, W, dtype=np.float64)
    ys = np.linspace(cy - half, cy + half, H, dtype=np.float64)
    C = xs[None, :] + 1j * ys[:, None]
    esc, fm2 = mandel_iter(C, max_iter)

    exterior = fm2 > BAILOUT_MAG2
    smooth = esc.copy()
    if exterior.any():
        smooth[exterior] = (
            esc[exterior] + 1.0
            - np.log2(np.log2(fm2[exterior]) * 0.5)
        )

    t = np.zeros_like(smooth)
    ex_vals = smooth[exterior]
    if ex_vals.size > 1:
        order = np.argsort(ex_vals)
        ranks = np.empty(ex_vals.size, dtype=np.float64)
        ranks[order] = np.arange(ex_vals.size)
        t[exterior] = ranks / (ex_vals.size - 1)

    u = (t * CYCLE) % 1.0
    u_fold = 1.0 - np.abs(2.0 * u - 1.0)
    pos = u_fold * (len(palette) - 1)
    idx = np.clip(pos.astype(np.int32), 0, len(palette) - 2)
    frac = (pos - idx)[..., None]
    color = palette[idx] + frac * (palette[idx + 1] - palette[idx])

    rgb = (color * BRIGHTNESS).clip(0, 255).astype(np.uint8)
    rgb[~exterior] = 0
    return rgb.tobytes()


def push_frame(pic_id: int, frame: bytes) -> float:
    data = base64.b64encode(frame).decode()
    t0 = time.monotonic()
    post({
        "Command": "Draw/SendHttpGif",
        "PicNum": 1, "PicWidth": 64, "PicOffset": 0,
        "PicID": pic_id, "PicSpeed": int(1000 / TARGET_FPS),
        "PicData": data,
    }, timeout=15.0)
    return time.monotonic() - t0


def _params_target(t: float, cx: float, cy: float, end_half: float):
    half = START_HALF_WIDTH * ((end_half / START_HALF_WIDTH) ** t)
    zoom_factor = START_HALF_WIDTH / half
    max_iter = int(80 + 120 * np.log10(max(1.0, zoom_factor)))
    return cx, cy, half, max_iter


def _params_double(t: float,
                   pcx: float, pcy: float, ph: float,
                   ccx: float, ccy: float, chh: float):
    """Continuous zoom with parent→child pan baked into the orbit. Zoom is
    two-phase geometric — START→ph by t=0.5 (parent's landing), ph→chh by
    t=1.0 (child's landing). Pan is smoothstep-eased over the same first
    half so camera slides from parent to child while we zoom in, with
    zero velocity at both endpoints. No discrete pan phase."""
    if t < 0.5:
        u = t * 2.0
        half = START_HALF_WIDTH * ((ph / START_HALF_WIDTH) ** u)
    else:
        u = (t - 0.5) * 2.0
        half = ph * ((chh / ph) ** u)
    pan_t = min(1.0, t * 2.0)
    s = pan_t * pan_t * (3.0 - 2.0 * pan_t)
    cx = pcx + s * (ccx - pcx)
    cy = pcy + s * (ccy - pcy)
    zoom_factor = START_HALF_WIDTH / half
    max_iter = int(80 + 120 * np.log10(max(1.0, zoom_factor)))
    return cx, cy, half, max_iter


def generate_tour_frames(targets, doubles, n_tour: int, doubles_pct: int,
                         doublec_pct: int, loop_forever: bool):
    """Yield (frame_bytes, header_or_none) across the whole tour. `header`
    is a preformatted log line carried on the first frame of each target
    and None for the rest, so the pusher can announce targets as they
    actually appear on-screen (not when they're rendered, which may be
    tens of minutes earlier)."""
    loop_n = 0
    single_n = 0
    dc_pct = max(0, min(100, doublec_pct))
    target_dt = 1.0 / TARGET_FPS
    total = max(1, int(round(SECONDS_PER_TARGET / target_dt)))
    while True:
        tour = build_tour(targets, doubles, n_tour, doubles_pct)
        for i, (kind, t) in enumerate(tour):
            if kind == "double":
                name, pcx, pcy, ph, ccx, ccy, chh, _p = t
                pname, palette = DOUBLE_PALETTES[
                    (i + loop_n) % len(DOUBLE_PALETTES)]
                header = (f"\n── DOUBLE {name} "
                          f"parent=({pcx:+.6f},{pcy:+.6f}) → "
                          f"child=({ccx:+.6f},{ccy:+.6f}) "
                          f"palette={pname} ──")
                for n in range(total + 1):
                    t_u = min(1.0, n * target_dt / SECONDS_PER_TARGET)
                    cx_, cy_, half, mi = _params_double(
                        t_u, pcx, pcy, ph, ccx, ccy, chh)
                    frame = render(cx_, cy_, half, mi, palette)
                    yield frame, (header if n == 0 else None)
            else:
                name, cx, cy, end_half, _p = t
                use_dc = (single_n * dc_pct) // 100 < \
                    ((single_n + 1) * dc_pct) // 100
                if use_dc:
                    pname, palette = DOUBLE_PALETTES[
                        (single_n + loop_n) % len(DOUBLE_PALETTES)]
                else:
                    pname, palette = PALETTES[
                        (single_n + loop_n) % len(PALETTES)]
                single_n += 1
                header = (f"\n── {name} ({cx:+.6f}, {cy:+.6f}) "
                          f"palette={pname} ──")
                for n in range(total + 1):
                    t_u = min(1.0, n * target_dt / SECONDS_PER_TARGET)
                    cx_, cy_, half, mi = _params_target(
                        t_u, cx, cy, end_half)
                    frame = render(cx_, cy_, half, mi, palette)
                    yield frame, (header if n == 0 else None)
        if not loop_forever:
            return
        loop_n += 1


def run_pipeline(gen) -> None:
    """Bursty producer/consumer. Renderer fills the queue up to
    MAX_BUFFER_FRAMES as fast as the CPU allows, then blocks on an event
    until the pusher has drained the queue down to REFILL_THRESHOLD_FRAMES.
    Pusher always runs at TARGET_FPS, doing nothing but pop + HTTP POST.

    Laptop CPU profile: ~1 min hot (filling 30 min of frames) per ~30 min
    of playback."""
    import queue as _queue
    q: _queue.Queue = _queue.Queue(maxsize=MAX_BUFFER_FRAMES)
    stop = threading.Event()
    refill = threading.Event()
    refill.set()  # kick the first burst immediately

    def renderer() -> None:
        it = iter(gen)
        exhausted = False
        while not exhausted and not stop.is_set():
            refill.wait()
            refill.clear()
            if stop.is_set():
                return
            burst_start = time.monotonic()
            produced = 0
            while q.qsize() < MAX_BUFFER_FRAMES and not stop.is_set():
                try:
                    item = next(it)
                except StopIteration:
                    exhausted = True
                    break
                while not stop.is_set():
                    try:
                        q.put(item, timeout=5.0)
                        break
                    except _queue.Full:
                        continue
                produced += 1
            if produced > 0:
                dt = time.monotonic() - burst_start
                mins = q.qsize() / TARGET_FPS / 60.0
                print(f"  [renderer] burst {produced} frames in "
                      f"{dt:.1f}s ({produced / max(dt, 0.01):.0f} fps) → "
                      f"buffer {q.qsize()} frames ({mins:.1f} min) — "
                      "sleeping", flush=True)

    rt = threading.Thread(target=renderer, daemon=True)
    rt.start()

    pic_id = 1
    target_dt = 1.0 / TARGET_FPS
    deadline = time.monotonic()
    try:
        while True:
            try:
                item = q.get(timeout=30.0)
            except _queue.Empty:
                if not rt.is_alive():
                    break
                continue
            frame, header = item
            if header:
                print(header, flush=True)
            if pic_id > 1 and pic_id % 32 == 1:
                post({"Command": "Draw/ResetHttpGifId"})
                pic_id = 1
            push_frame(pic_id, frame)
            pic_id += 1
            if (q.qsize() <= REFILL_THRESHOLD_FRAMES
                    and not refill.is_set()):
                refill.set()
            deadline += target_dt
            sleep = deadline - time.monotonic()
            if sleep > 0:
                time.sleep(sleep)
            else:
                deadline = time.monotonic()
    finally:
        stop.set()
        refill.set()
        rt.join(timeout=2.0)


def build_tour(targets: list, doubles: list, n: int, doubles_pct: int = 25
               ) -> list[tuple[str, tuple]]:
    """Interleave double-deep targets at `doubles_pct` of slots (0–100)."""
    tour: list[tuple[str, tuple]] = []
    ti = di = 0
    pct = 0 if not doubles else max(0, min(100, doubles_pct))
    for i in range(n):
        use_double = (i * pct) // 100 < ((i + 1) * pct) // 100
        if use_double:
            tour.append(("double", doubles[di % len(doubles)]))
            di += 1
        else:
            tour.append(("single", targets[ti % len(targets)]))
            ti += 1
    return tour


def main() -> None:
    n_tour = NUM_IN_TOUR
    loop_forever = False
    doubles_pct = 25
    doublec_pct = 25
    for a in sys.argv[1:]:
        if a == "--scan":
            for f in (CACHE_FILE, DOUBLES_CACHE_FILE):
                if os.path.exists(f):
                    os.remove(f)
            load_or_scan()
            return
        if a == "--scan-doubles":
            if os.path.exists(DOUBLES_CACHE_FILE):
                os.remove(DOUBLES_CACHE_FILE)
            load_or_scan()
            return
        if a == "--loop":
            loop_forever = True
        elif a.startswith("--doubles="):
            doubles_pct = int(a.split("=", 1)[1])
        elif a.startswith("--doublec="):
            doublec_pct = int(a.split("=", 1)[1])
        elif a.isdigit():
            n_tour = int(a)

    targets, doubles = load_or_scan()
    print(f"cached: {len(targets)} singles, {len(doubles)} doubles; "
          f"tour of {n_tour}, doubles={doubles_pct}%, "
          f"doublec={doublec_pct}%; buffer "
          f"{MAX_BUFFER_MINUTES:.0f}min / refill at "
          f"{REFILL_THRESHOLD_MINUTES:.0f}min "
          f"({MAX_BUFFER_FRAMES}/{REFILL_THRESHOLD_FRAMES} frames)",
          flush=True)

    print(f"priming {IP}...", flush=True)
    prime()

    gen = generate_tour_frames(targets, doubles, n_tour, doubles_pct,
                               doublec_pct, loop_forever)
    run_pipeline(gen)


if __name__ == "__main__":
    main()
