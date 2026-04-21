# Pixoo-64 HTTP protocol — measured behavior

What we found 2026-04-20 by probing a Pixoo-64 over WiFi. The public API
doc is sparse and stale; this is ground truth from actual packets, not from
Divoom's documentation.

## Endpoint surface

- **`POST http://<device>/post`** — single JSON endpoint. Every command is a
  JSON body with a `Command` field. Response is a small JSON with
  `error_code` (0 = ok).
- No WebSocket. No callbacks. No sensors. No mDNS. Port 4096 TCP exists on
  older BLE-transport Divoom devices (Pixoo-16/32, Tivoo, Ditoo), **not on
  Pixoo-64.**
- Client-pull only. The device never initiates.

## Per-request size limits

- **~16KB base64 body** works reliably. That's one 64×64 RGB frame
  (12288 raw → 16384 base64).
- **~32KB single body** — device receives it but never replies; urllib
  times out on response read. Firmware can't handle the payload.
- **~160KB single body** — crashes the device into rainbow-corner reboot
  state. Recovery takes 30–60s.

Takeaway: **never send more than ~16KB in one POST.**

## The multi-frame protocol

Multi-frame `Draw/SendHttpGif` is *not* one fat body. It's N separate POSTs,
each one a normal 16KB single-frame upload, glued together by a shared
`PicID`:

```python
for offset in range(N):
    POST /post {
        "Command":   "Draw/SendHttpGif",
        "PicID":     100,        # SAME across all N frames
        "PicNum":    N,          # SAME (total frame count)
        "PicOffset": offset,     # DIFFERENT (0, 1, …, N-1)
        "PicSpeed":  100,        # ms/frame on playback (same each POST)
        "PicData":   <base64 of one 64×64 RGB frame>
    }
```

The device accumulates frames by `PicID`. When all N offsets for a PicID
have arrived, the device starts looping them at `PicSpeed` ms/frame.

## Slot semantics (probed)

Three experiments with solid-color frames to determine exactly what the
device does with offsets. Results:

| Test | Result |
|---|---|
| **Preempt:** push PicID=N+1 while PicID=N is looping | ✅ new animation replaces the old one as soon as its last offset lands |
| **In-place update:** re-POST one offset of an already-complete animation | ❌ silently ignored; the frozen loop keeps playing the old frame |
| **Out-of-order offsets:** send offsets 2, 0, 3, 1 instead of 0, 1, 2, 3 | ✅ device assembles by offset; plays in correct 0→N-1 order regardless |

Implications:
- You **can** queue the next animation while the current one plays. Great
  for double-buffered streaming.
- You **cannot** patch a single frame of a running animation. To update
  any pixel, you must roll a new `PicID` and re-upload all N frames.
- Upload order inside one PicID is flexible. Potentially useful if we ever
  want to prioritize keyframes, though no concrete use today.

## Push rate ceilings

Measured with single-frame POSTs, close-per-request (no keep-alive), PicID
reset every 32 pushes. 326 frames across 2/3/4/5/6 fps runs, zero stalls.

| Target fps | Actual | p50 per-POST | p95 | max |
|---|---|---|---|---|
| 2.0 | 2.00 | 185ms | 212ms | 222ms |
| 3.0 | 3.00 | 176ms | 210ms | 225ms |
| 4.0 | 4.00 | 167ms | 199ms | 209ms |
| 5.0 | 4.98 | 171ms | 191ms | 222ms |
| 6.0 | 5.70 | 167ms | 198ms | 292ms |

**Each POST costs ~170ms flat.** That's the round-trip floor for a ~16KB
body over WiFi. 5fps (200ms intervals) is the last target we hit cleanly;
6fps asks for 167ms which is at the floor with zero slack.

**Upload ceiling: ~5fps. Plan for 4fps with margin.**

Do **not** use HTTP/1.1 keep-alive. Tested: drops to 0.5fps with stalls.
Removing pacing overflows the device's tiny input buffer; close-per-POST is
what gives the device enough time to drain.

## Playback ceiling

The device can render a pre-uploaded animation at higher rates than we can
push live:

- **`PicSpeed` floor: ~80ms/frame** (12fps playback). Below that the device
  stutters.
- **Practical range: 80–100ms/frame** (10–12fps playback).
- **Max frames per PicID:** ~40–60 before the device freezes during upload.
  Community libs cap at 60. `SomethingWithComputers/pixoo` resets PicID
  every 32 frames; we follow that.

So **live upload is bounded at 5fps; pre-uploaded playback is bounded at
12fps.** The gap is real: if we pre-render a 10-frame animation and push it
once, the device displays it at 10fps even though we can only upload 5 raw
frames/sec.

## PicID hygiene

- PicID must be **monotonically increasing** across uploads on the device's
  lifetime, or at least since the last `Draw/ResetHttpGifId`. Reuse will
  not update the slot (see slot semantics above).
- Community pattern: call `Draw/ResetHttpGifId` every 32 pushes to avoid a
  ~300-push firmware freeze. Cheap insurance.
- Simple scheme: monotonic counter in host memory, periodic resets, never
  reuse across restarts until the device has been reset.

## Priming (for text overlays)

`Draw/SendHttpText` returns `error_code: 0` even when it renders nothing.
It only paints after:

1. Channel switched to 3 (custom/HTTP channel).
2. At least one `Draw/SendHttpGif` frame received since that channel switch.

`PixooClient.prime()` does both. If you see rainbow-corners, priming didn't
happen — that's "custom channel, no HTTP buffer content" fallback.

## Streaming architecture (what falls out of the above)

For continuous animation longer than one PicID's worth of frames:

**Double-buffer by PicID.**

```
┌─────────────────┐     while device plays     ┌─────────────────┐
│ uploading       │      PicID=N animation     │ playing         │
│ PicID=N+1       │      host uploads N+1      │ PicID=N (old)   │
│ offsets 0..M-1  │──────────────────────────▶│                 │
└─────────────────┘                             └─────────────────┘
                      when last offset lands,
                      device swaps to N+1 automatically
```

Sizing the chunks is a constraint problem:

- **Upload time per chunk:** M frames × ~200ms = `M × 0.2s`.
- **Playback time per chunk:** M frames × PicSpeed = `M × PicSpeed`.
- **To avoid gaps between chunks, playback ≥ upload** →
  `M × PicSpeed ≥ M × 200ms` → `PicSpeed ≥ 200ms` (5fps playback).

So if we want **gapless infinite streaming**, playback is 5fps, matching
upload. We don't get anything from the device's 10–12fps internal ceiling.

If we accept brief gaps (device plays a stale loop while next chunk
uploads), we can run playback at 10fps:
- M = 10, PicSpeed = 100ms → 1s playback, 2s upload → 1s gap per chunk.
- M = 20, PicSpeed = 100ms → 2s playback, 4s upload → 2s gap per chunk.

Gap isn't a blank screen — it's the current animation looping while the
next is being prepared. So the device always has *something* playing, just
not necessarily fresh content.

**Interactive ceiling for a program with real-time input (e.g. Mandelbrot
pan): 5fps.** Rendering faster than the device can consume is wasted work.

**Bonus lever (untested):**
`Device/PlayTFGif {FileType:2, FileName:"http://host/x.gif"}` tells the
device to pull a GIF from a URL you host. User `satoer` in the community
ran this for 4 weeks without a crash. Could be a path for very long
animations where we rotate a file rather than push frames. Haven't tried
it yet.

## Driver recipe

A `PixooDriver` should:

1. Prime once per session (channel 3 + ResetHttpGifId + one frame).
2. Maintain a monotonic PicID counter.
3. Reset PicID every ~32 pushes via `Draw/ResetHttpGifId`.
4. Use `urllib` with a fresh request per POST (no keep-alive, no
   connection pooling).
5. Rate-limit to ~4fps single-frame OR switch to chunked multi-frame
   double-buffer for smoother output.
6. Drop a frame (don't block the program) if a POST is mid-flight when the
   next tick fires. Program's simulation tick and device push rate are
   independent.
7. On POST error or timeout: back off ~1s, try again. If stalls persist,
   assume device crashed and re-prime.

Never run the driver in lockstep with program simulation. Program ticks at
its native rate (60Hz, 120Hz, whatever it needs); the driver samples the
latest frame when ready to push.

## Things we ruled out

- **Port scanning** the device: reboots it. Probe only port 80 gently.
- **Keep-alive** HTTP: overflows the device buffer; worse than fresh
  connections.
- **One-POST multi-frame** (N frames in one body): crashes past ~16KB.
- **30fps** or even **15fps** live: not achievable over this protocol on
  this firmware.
