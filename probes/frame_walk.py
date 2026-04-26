"""Walk N down from 60 to 10, one clean PicID per trial, long holds.

Resets PicID counter before each trial so prior frames can't leak across.
Holds for HOLD seconds so you can count the full cycle on the device.

Usage: python3 programs/frame_walk.py [START=60] [STEP=10] [STOP=10]
                                      [SPEED=80] [HOLD=15]
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")
from pixoolib.client import PixooClient
from programs.frame_stress import labeled_frame, pick_ip


def main() -> None:
    args = sys.argv[1:]
    start = int(args[0]) if len(args) > 0 else 60
    step  = int(args[1]) if len(args) > 1 else 10
    stop  = int(args[2]) if len(args) > 2 else 10
    speed = int(args[3]) if len(args) > 3 else 80
    hold  = float(args[4]) if len(args) > 4 else 15.0

    ip = pick_ip()
    print(f"target {ip}, walk N {start} -> {stop} step -{step}, "
          f"speed={speed}ms, hold={hold}s", flush=True)
    c = PixooClient(ip)
    c.prime()

    n = start
    while n >= stop:
        # Full reset between trials — no cross-PicID memory leak
        c.reset_gif_id()
        print(f"\n── N={n} (PicSpeed={speed}ms, cycle={n*speed/1000:.1f}s) ──",
              flush=True)
        t0 = time.monotonic()
        for i in range(n):
            frame = labeled_frame(i + 1, n)
            c.post({
                "Command":   "Draw/SendHttpGif",
                "PicNum":    n,
                "PicWidth":  64,
                "PicOffset": i,
                "PicID":     1,           # fresh every trial (after reset)
                "PicSpeed":  speed,
                "PicData":   frame.to_base64(),
            }, timeout=15.0)
        dt = time.monotonic() - t0
        print(f"  uploaded {n} frames in {dt:.1f}s; "
              f"holding {hold}s for observation", flush=True)
        time.sleep(hold)
        n -= step


if __name__ == "__main__":
    main()
