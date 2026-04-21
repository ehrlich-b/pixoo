"""Find the per-PicID frame-count ceiling on this Pixoo-64.

Ramps N upward. For each N it uploads one PicID containing frames
labeled 0001..NNNN at 80ms playback (12fps). If any POST raises,
prints the last safe N and exits.

Usage: python3 programs/frame_stress.py [START=32] [STEP=8] [MAX=256] [SPEED=80]
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")
from pixoolib.anim import upload_animation
from pixoolib.client import PixooClient
from pixoolib.digits import draw_text, text_width
from pixoolib.frame import Frame
from pixoolib.state import load_state  # noqa: F401  (ok if absent)


def labeled_frame(idx: int, n: int) -> Frame:
    """64x64 frame: 'NNNN' big on top, 'N=MM' tiny label below."""
    f = Frame()
    f.clear((12, 12, 24))
    # large current-frame number, centered
    label = f"{idx:04d}"
    w = text_width(label) * 2  # 2x upscale
    x0 = (64 - w) // 2
    draw_text_scaled(f, label, x0, 14, (220, 240, 255), scale=2)
    # denominator, centered below, 1x
    denom = f"N={n:03d}"
    w2 = text_width(denom)
    draw_text(f, denom, (64 - w2) // 2, 42, (180, 180, 120))
    return f


def draw_text_scaled(f: Frame, text: str, x: int, y: int,
                     rgb, scale: int) -> None:
    """Upscale-by-nearest-neighbor draw: render to a tiny frame, copy x/y."""
    from pixoolib.digits import _GLYPHS, W, H
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
                        f.set(cx + col * scale + dx, y + row * scale + dy, rgb)
        cx += W * scale


def pick_ip() -> str:
    import json
    import os
    env = os.environ.get("PIXOO_IP")
    if env:
        return env
    if os.path.exists(".pixoo-state.json"):
        with open(".pixoo-state.json") as fh:
            return json.load(fh)["ip"]
    raise SystemExit("no IP: set PIXOO_IP or run ./pixoo discover")


def main() -> None:
    args = sys.argv[1:]
    start = int(args[0]) if len(args) > 0 else 32
    step  = int(args[1]) if len(args) > 1 else 8
    maxn  = int(args[2]) if len(args) > 2 else 256
    speed = int(args[3]) if len(args) > 3 else 80

    ip = pick_ip()
    print(f"target {ip}, start={start} step={step} max={maxn} speed={speed}ms")
    c = PixooClient(ip)

    c.prime()
    c.reset_gif_id()

    pic_id = 1
    last_ok = 0
    n = start
    while n <= maxn:
        pic_id += 1
        print(f"\n── N={n}  PicID={pic_id} ──", flush=True)
        frames = [labeled_frame(i + 1, n) for i in range(n)]
        t0 = time.monotonic()
        try:
            for i, frame in enumerate(frames):
                tp0 = time.monotonic()
                c.post({
                    "Command":   "Draw/SendHttpGif",
                    "PicNum":    n,
                    "PicWidth":  64,
                    "PicOffset": i,
                    "PicID":     pic_id,
                    "PicSpeed":  speed,
                    "PicData":   frame.to_base64(),
                }, timeout=15.0)
                dt = (time.monotonic() - tp0) * 1000
                if i == 0 or (i + 1) % 20 == 0 or i == n - 1:
                    print(f"  off={i+1}/{n}  {dt:.0f}ms", flush=True)
        except Exception as exc:
            print(f"  FAIL at offset {i+1}/{n}: {exc!r}")
            print(f"\n*** last safe N = {last_ok} ***")
            return
        total = time.monotonic() - t0
        print(f"  uploaded N={n} in {total:.1f}s "
              f"({total / n * 1000:.0f}ms/frame avg)")
        last_ok = n
        # hold so the animation can be observed
        time.sleep(6.0)
        n += step
    print(f"\nreached max without crashing; last safe N = {last_ok}")


if __name__ == "__main__":
    main()
