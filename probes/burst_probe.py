"""Probe: interleave a burst-animation upload into a live push stream.

Tick cadence is 250ms (4 slots/sec):
  - 3 of every 4 slots: live push — single-frame, monotonic PicID
  - 1 of every 4 slots: burst push — one offset of a fixed PicID=BURST_ID

We pre-upload burst offsets 0..N-2 interleaved. We HOLD offset N-1 until
T=40s, then push it to trigger the device's swap to the burst animation.
After 3s of burst playback we push a fresh live frame to preempt back.

Central question: does the device accept burst-offset appends between
live-animation PicIDs? Monotonic rule may or may not allow it.

Usage: python3 programs/burst_probe.py
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")
from pixoolib.client import PixooClient
from pixoolib.digits import draw_text, text_width
from pixoolib.frame import Frame
from programs.frame_stress import labeled_frame, pick_ip

BURST_ID     = 9_999_999     # must stay > every live PicID in the test
LIVE_START   = 1_000
POST_BURST_LIVE = BURST_ID + 10  # live resumes above burst after swap-back
N_BURST      = 10
BURST_SPEED  = 80            # ms/frame → 12.5fps playback
LIVE_SPEED   = 200           # PicSpeed for 1-frame "GIFs"
TICK_DT      = 0.25          # 4 slots/sec
TRIGGER_AT_S = 15.0          # short warm-up so the burst is easy to catch
BURST_HOLD_S = 10.0          # ~12 burst loops → unmissable


def live_frame(n: int) -> Frame:
    """Live = dark grey background, big yellow 'L' + tick counter."""
    f = Frame()
    f.clear((20, 20, 30))
    # Huge "L" glyph on the left — hand-drawn, 20 px tall
    for y in range(10, 50):
        for x in range(8, 12):
            f.set(x, y, (255, 220, 40))
    for y in range(46, 50):
        for x in range(8, 28):
            f.set(x, y, (255, 220, 40))
    # Tick counter on the right (2x scaled digits are overkill; single-scale)
    s = f"{n:04d}"
    w = text_width(s)
    draw_text(f, s, 64 - w - 2, 30, (200, 220, 255))
    return f


def burst_frame(idx: int) -> Frame:
    """Burst = full-screen saturated color per frame + huge centered digit.
    Designed to be unmistakable next to the grey 'L' live frames."""
    palette = [
        (255, 0, 0),      (255, 120, 0),    (255, 220, 0),
        (140, 230, 0),    (0, 200, 80),     (0, 200, 220),
        (0, 100, 255),    (120, 0, 240),    (230, 0, 200),
        (255, 255, 255),
    ]
    r, g, b = palette[(idx - 1) % len(palette)]
    f = Frame()
    f.clear((r, g, b))
    # Huge centered digit (5x7 font scaled ×4 → 20×28 glyph, 2 chars max)
    s = str(idx)
    scale = 4
    glyph_w = text_width(s) * scale
    x0 = (64 - glyph_w) // 2
    y0 = (64 - 7 * scale) // 2
    _draw_scaled(f, s, x0, y0, (0, 0, 0), scale)
    return f


def _draw_scaled(f: Frame, text: str, x: int, y: int,
                 rgb: tuple[int, int, int], scale: int) -> None:
    from pixoolib.digits import _GLYPHS, W
    cx = x
    for ch in text:
        glyph = _GLYPHS.get(ch)
        if glyph is None:
            cx += W * scale
            continue
        for row, bits in enumerate(glyph):
            for col, c in enumerate(bits):
                if c != "#":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        f.set(cx + col * scale + dx, y + row * scale + dy,
                              rgb)
        cx += W * scale


def main() -> None:
    ip = pick_ip()
    c = PixooClient(ip)
    print(f"target {ip}; BURST_ID={BURST_ID}, N={N_BURST}, "
          f"trigger at T={TRIGGER_AT_S}s", flush=True)
    c.prime()
    c.reset_gif_id()

    burst_frames = [burst_frame(i + 1) for i in range(N_BURST)]

    # Live PicID starts well BELOW BURST_ID so every burst offset satisfies
    # the monotonic rule (BURST_ID > any live PicID in flight). Once burst
    # fires, live must jump above BURST_ID to stay monotonic.
    live_pic_id = LIVE_START
    next_burst_offset = 0          # 0..N_BURST-2 during warm-up
    burst_triggered = False

    t0 = time.monotonic()
    deadline = t0
    tick = 0

    while True:
        elapsed = time.monotonic() - t0

        # Trigger: at T=40s, push the final offset → device should swap
        if elapsed >= TRIGGER_AT_S and not burst_triggered:
            print(f"  T={elapsed:5.1f}s  TRIGGER: push BURST offset "
                  f"{N_BURST - 1}/{N_BURST}", flush=True)
            c.post({
                "Command":   "Draw/SendHttpGif",
                "PicNum":    N_BURST,
                "PicWidth":  64,
                "PicOffset": N_BURST - 1,
                "PicID":     BURST_ID,
                "PicSpeed":  BURST_SPEED,
                "PicData":   burst_frames[N_BURST - 1].to_base64(),
            })
            burst_triggered = True
            # Hold so we can observe the swap
            print(f"  T={elapsed:5.1f}s  >>> WATCH BURST LOOP for "
                  f"{BURST_HOLD_S:.0f}s <<<", flush=True)
            time.sleep(BURST_HOLD_S)
            # Preempt back to live — must jump above BURST_ID now
            live_pic_id = POST_BURST_LIVE
            print(f"  T={time.monotonic() - t0:5.1f}s  SWAP BACK: live "
                  f"push PicID={live_pic_id}", flush=True)
            c.post({
                "Command":   "Draw/SendHttpGif",
                "PicNum":    1,
                "PicWidth":  64,
                "PicOffset": 0,
                "PicID":     live_pic_id,
                "PicSpeed":  LIVE_SPEED,
                "PicData":   live_frame(9999).to_base64(),
            })
            print(f"  T={time.monotonic() - t0:5.1f}s  back to live; "
                  "holding 5s to observe", flush=True)
            time.sleep(5.0)
            return

        # Normal tick: pick live or burst
        tick_kind = tick % 4
        if tick_kind == 3 and next_burst_offset < N_BURST - 1:
            # Burst append
            frame = burst_frames[next_burst_offset]
            print(f"  T={elapsed:5.1f}s  BURST offset "
                  f"{next_burst_offset}/{N_BURST - 1}", flush=True)
            try:
                c.post({
                    "Command":   "Draw/SendHttpGif",
                    "PicNum":    N_BURST,
                    "PicWidth":  64,
                    "PicOffset": next_burst_offset,
                    "PicID":     BURST_ID,
                    "PicSpeed":  BURST_SPEED,
                    "PicData":   frame.to_base64(),
                })
                next_burst_offset += 1
            except Exception as exc:
                print(f"  BURST FAIL: {exc!r}", flush=True)
                return
        else:
            # Live push
            live_pic_id += 1
            try:
                c.post({
                    "Command":   "Draw/SendHttpGif",
                    "PicNum":    1,
                    "PicWidth":  64,
                    "PicOffset": 0,
                    "PicID":     live_pic_id,
                    "PicSpeed":  LIVE_SPEED,
                    "PicData":   live_frame(tick).to_base64(),
                })
                if tick % 12 == 0:
                    print(f"  T={elapsed:5.1f}s  live tick={tick} "
                          f"PicID={live_pic_id}", flush=True)
            except Exception as exc:
                print(f"  LIVE FAIL: {exc!r}", flush=True)
                return

        tick += 1
        deadline += TICK_DT
        sleep = deadline - time.monotonic()
        if sleep > 0:
            time.sleep(sleep)
        else:
            deadline = time.monotonic()


if __name__ == "__main__":
    main()
