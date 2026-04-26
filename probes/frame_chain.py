"""Double-buffer test: upload batch A (PicID=1, frames 1-60), let it play,
upload batch B (PicID=2, frames 61-120) while A loops. Device should swap
to B when B's last offset lands.

Usage: python3 programs/frame_chain.py [SPEED=80] [HOLD=30]
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, ".")
from pixoolib.client import PixooClient
from programs.frame_stress import labeled_frame, pick_ip

N = 60


def upload_batch(c: PixooClient, pic_id: int, start_idx: int, total: int,
                 speed: int) -> float:
    """Upload N frames labeled start_idx..start_idx+N-1, all under pic_id.
    `total` is the denominator shown on each frame (120 here)."""
    t0 = time.monotonic()
    for i in range(N):
        frame = labeled_frame(start_idx + i, total)
        c.post({
            "Command":   "Draw/SendHttpGif",
            "PicNum":    N,
            "PicWidth":  64,
            "PicOffset": i,
            "PicID":     pic_id,
            "PicSpeed":  speed,
            "PicData":   frame.to_base64(),
        }, timeout=15.0)
    return time.monotonic() - t0


def main() -> None:
    speed = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    hold  = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0

    ip = pick_ip()
    total = N * 2
    print(f"target {ip}, chain 2×{N}={total} @ {speed}ms, hold={hold}s",
          flush=True)
    c = PixooClient(ip)
    c.prime()
    c.reset_gif_id()

    print(f"\n── batch A: PicID=1, frames 1..{N} ──", flush=True)
    dt_a = upload_batch(c, pic_id=1, start_idx=1, total=total, speed=speed)
    print(f"  uploaded in {dt_a:.1f}s (device should now loop 1..{N})",
          flush=True)

    print(f"\n── batch B: PicID=2, frames {N+1}..{total} (uploading while A "
          "plays) ──", flush=True)
    dt_b = upload_batch(c, pic_id=2, start_idx=N + 1, total=total, speed=speed)
    print(f"  uploaded in {dt_b:.1f}s (device should swap to {N+1}..{total})",
          flush=True)

    print(f"\nholding {hold}s — watch for swap from 1..60 to 61..120",
          flush=True)
    time.sleep(hold)


if __name__ == "__main__":
    main()
