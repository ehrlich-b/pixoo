# pixoo — Divoom Pixoo-64 programmable display

A Python CLI plus program runtime for driving a Divoom Pixoo-64 over its LAN
HTTP API. The Pixoo is a 64×64 RGB LED panel with no userspace — we treat it
as a network-attached framebuffer. Host runs code, frames push to the device.

## Current state

Stdlib-only CLI (`./pixoo`) with:
- `discover` — port-scans the local /24, fingerprints via `Channel/GetIndex`,
  menu-picks one, caches to `.pixoo-state.json`.
- `info` — dumps `Channel/GetAllConf`.
- `text <msg>` — pushes a text overlay. Auto-primes the HTTP frame buffer
  (channel 3 + `ResetHttpGifId` + black frame) on first use after a
  channel switch, because `Draw/SendHttpText` is silently ignored otherwise.
- `channel <0-4>`, `brightness <0-100>`, `clear`, `raw '<json>'`.

State cached in `.pixoo-state.json` (gitignored). `PIXOO_IP` env var overrides
the cached IP for one-shot use.

No pip deps. Python 3.14 available locally.

## Device quirks (hard-won)

Keep this list honest — these are the things that will burn time.

- **Text needs a primed buffer.** `Draw/SendHttpText` returns `error_code: 0`
  even when it does nothing. It only renders after the device is on channel 3
  and has received at least one `Draw/SendHttpGif` frame since the last
  channel switch. `PixooClient.prime()` handles this; `ensure_primed()`
  tracks it via state.
- **Channel 3 without HTTP content = rainbow corners.** That's the "custom
  channel, no content" fallback pattern. If you see it, the priming didn't
  happen. Not a bug in your program.
- **PicID must increase monotonically** across `Draw/SendHttpGif` calls. Reset
  via `Draw/ResetHttpGifId` at session start, or when the counter grows large.
- **Frame rate ceiling ~12–15 fps over WiFi.** A frame is ~12KB of base64
  RGB. Don't pursue 30fps on the device; throttle device pushes separately
  from simulation tick.
- **Onboard mic is firmware-walled.** The mic only drives built-in EQ /
  noise-meter channels. No API exposes samples/dB/spectrum. Any audio-
  reactive program we build captures on the host.
- **No push / callback from the device.** Pure client-pull. No buttons, no
  sensors, no webhooks. Input events live on the host.
- **Channels:** 0=faces, 1=cloud, 2=visualizer, 3=custom (HTTP buffer
  target), 4=blackscreen.
- **Docs:** official at http://doc.divoom-gz.com/web/#/12 (partial, often
  out of date). Best practical API reference is the OpenAPI spec in
  github.com/r12f/divoom. Community Python lib is `pixoo` on PyPI — handles
  PicID bookkeeping and Pillow→frame conversion; worth vendoring when we
  add image/GIF push.

## Planned architecture

**Program ↔ Driver split.** A `Program` produces frames and consumes input
events; it doesn't know whether output is a real Pixoo or a terminal
simulation. A `Driver` consumes frames and produces input events; it doesn't
know what program is running.

```
Program.update(dt, events) ──▶ Frame ──▶ Driver.render(frame)
                   ▲                          │
                   └──── Driver.events() ◀────┘
```

**Drivers:**
- `PixooDriver` — HTTP frame push, rate-limited ~12fps, handles PicID.
- `TerminalDriver` — Textual app, half-block pixel renderer (two Pixoo rows
  per terminal row using ▀ with different fg/bg), key and mouse dispatch.
- `MirrorDriver` — both at once.

**Why Textual?** Python's closest analog to Bubble Tea. Reactive widgets,
keybindings, mouse, async, good devtools. A 64-column half-block display
is ~64×32 terminal cells — close to square aspect, very readable.

**Frame rate decoupling.** Simulation tick runs at native rate (e.g. 120Hz
for physics). Terminal paints at 60fps. Pixoo pushes at 12fps with frame-
skip when unchanged. Program doesn't see or care about this.

## Planned file layout

```
pixoo                       bash shim → python3 cli.py
cli.py                      arg parsing, dispatch
pixoolib/
  client.py                 PixooClient (HTTP + typed commands)
  discover.py               LAN /24 scan
  frame.py                  Frame class — 64×64 RGB, PIL bridge, primitives
  runtime.py                Program base, Runner loop, input events
  device.py                 PixooDriver (rate-limited pusher)
  term.py                   TerminalDriver (Textual app + half-block render)
programs/
  dot.py                    arrow-key-movable pixel (smoke test)
  mandelbrot.py             main goal — kb pan, mouse-wheel/arrow zoom
  pendulum.py               double pendulum
  cradle.py                 Newton's cradle
  galton.py                 bean machine
requirements.txt            pillow, textual, numpy — lazy-installed on `run`
```

Fast-path commands (`discover`, `info`, `text`, `channel`, `raw`) stay
stdlib-only so the 95% case has no startup cost. `./pixoo run <program>`
lazily creates `.venv/` and installs deps on first use.

## Roadmap

0. **Ergonomics (done).** Auto-prime on `text`.
1. **Runtime core.** `Frame`, `Program`, `Runner`, `PixooDriver`. Integrate
   `pixoo` pypi lib for image/gif push (PicID bookkeeping).
2. **TerminalDriver.** Textual app with half-block renderer, key+mouse
   dispatch, control-hint panel, fps/connection status bar.
3. **Smoke-test program.** `programs/dot.py` — arrow keys move a colored
   pixel. Proves the whole pipeline end-to-end. This is the canary; if it
   breaks, the runtime is broken.
4. **Mandelbrot.** `programs/mandelbrot.py`. Keyboard pan, mouse-wheel or
   arrow-based zoom, click-to-center. Needs numpy for perf at 64×64.
5. **Physics demos.** `pendulum.py`, `cradle.py`, `galton.py`. Pick-your-own
   order. Each is a couple hundred lines of state + render.
6. **Mirror mode.** `./pixoo run <name> --mirror` sends to both terminal
   and device. Dev ergonomics; nothing structural.

Deferred (not in scope until runtime lands): dashboards, dB meter,
webhook triggers, Home Assistant integration.

## Adding a program

```python
# programs/dot.py
from pixoolib.runtime import Program, Frame

class Dot(Program):
    def setup(self, ctx):
        self.x, self.y = 32, 32

    def update(self, dt, events):
        for ev in events:
            if ev.key == "up":    self.y = max(0, self.y - 1)
            elif ev.key == "down":  self.y = min(63, self.y + 1)
            elif ev.key == "left":  self.x = max(0, self.x - 1)
            elif ev.key == "right": self.x = min(63, self.x + 1)

    def render(self) -> Frame:
        f = Frame.black()
        f.set(self.x, self.y, (255, 255, 255))
        return f
```

Register in `programs/__init__.py`. Programs import only from `pixoolib`,
never from drivers — that's the invariant that keeps them portable.

## Dev workflow

Terminal first, device second. Run `./pixoo run <name>` for fast iteration;
add `--mirror` to also push to the Pixoo when you want to see it live. The
Pixoo has no input, so arrow-key programs only make sense in terminal or
mirror mode.

The `dot` program is the smoke test. If it doesn't respond to arrows in the
terminal, runtime is broken — fix that before anything else.

## Dep policy

- Fast path stays stdlib — zero imports outside cpython.
- `run` path adds Pillow (image/text rasterization), Textual (TUI), numpy
  (numeric programs). Lazy-install into `.venv/` on first `run`.
- Add new deps only when a specific program needs them. No preemptive
  vendoring.

## Owner notes

Bryan — staff engineer, CLI-first, blunt and direct. Bulk preferences in
`~/.claude/CLAUDE.md`. Project-specific:

- The IP is DHCP — `192.168.4.111` at time of writing, but assume it can
  move. Discovery loop exists so we never hardcode.
- Single-sentence commits. No co-author trailers. No emoji.
- Don't alter the fast-path subcommand shapes (`discover`/`info`/`text`/
  `channel`/`raw`) without asking — they're in muscle memory.
- He hates Python deps but tolerates them when justified. Justify each.
