# Pixoo-64 program ideas

Brainstorm universe. Status/priority lives in `TODO.md` — this file is just
"what would be cool to build someday." A program is a `programs/*.py` with a
`Program` subclass; the bar is low. `./pixoo list` reads everything that
lands here.

## Ground rules

- 64×64 is tiny. Big shapes need low detail; small shapes can be precise.
  Text is basically unusable below 8px — lean on color and motion.
- Device push ceiling is ~5fps sustained, ~12fps from a preloaded loop. Run
  simulation at native rate; render to frame at 30fps; `PixooDriver`
  throttles device pushes separately.
- Programs import only from `pixoolib`. Stdlib first; numpy only if a
  program genuinely needs numeric lift.
- Each `Program` subclass has a one-line `DESCRIPTION` so `./pixoo list`
  reads like a menu.

## Cellular automata & math

- `life` — Conway's Game of Life, cycle classic seeds (glider gun,
  R-pentomino, random soup), reset on stasis/oscillation.
- `langton` — Langton's ant. Many steps per frame, ant as red pixel, reset
  when it escapes the highway.
- `eca` — Elementary cellular automaton. Cycle iconic rules (30, 90, 110,
  184, 54, 73); new row at bottom, scroll up.
- `sandpile` — Abelian sandpile. Drop grains at center; long-run produces
  a fractal.
- `dla` — Diffusion-limited aggregation. Random walkers stick on contact;
  grows a snowflake/coral shape.
- `reaction` — Gray-Scott reaction-diffusion. Spots, stripes, labyrinths
  depending on parameters. Needs numpy.
- `forest_fire` — Forest fire CA. Growth + lightning, self-organized
  criticality.
- `boids` — Flocking, ~40 particles, separation/alignment/cohesion.
- `wireworld` — Brian's Brain / Wireworld with hand-placed oscillators
  and gates so it actually computes.
- `ulam` — Ulam prime spiral. Walk integers outward on a square spiral,
  light up primes, famous diagonals emerge.
- `schelling` — Schelling segregation. Two-color agents, each wants
  ≥30% same-color neighbors; unhappy ones migrate; self-organizes.

## Fractals

- `mandelbrot_zoom` — SHIPPED (standalone script, not a `Program`).
  Landmark tour with double-zooms, bursty 40-min frame buffer.
- `julia` — Julia set with `c` drifting along a nice path; the set breathes.
- `newton` — Newton's method basins of attraction for a cubic.
- `ifs` — Iterated function systems: Barnsley fern, Sierpinski, dragon via
  chaos game.
- `lsystem` — L-system tree / Koch / dragon. Grow one step per frame.

## Physics

- `pendulum` — Double pendulum with trail of bob 2. Two pendulums offset
  by 1e-6 to show chaos divergence.
- `cradle` — Newton's cradle. Five balls, momentum transfer.
- `galton` — Bean machine. Beads fall, bounce on pegs, pile up Gaussian.
- `magnet_pendulum` — Pendulum over 3 magnets; color pixels by which
  magnet catches them (chaos basin map).
- `nbody` — 2D N-body gravity. Stable figure-8 orbit or chaotic init.
- `waves` — 2D wave equation on a 64×64 drum skin.
- `heat` — Heat equation. Hotspot diffuses; colormap → temperature.
- `spring_mesh` — 16×16 spring cloth projected to screen, pinned corners.
- `sand` — Falling-sand powder-toy. Sand/water/fire/stone with simple
  rules, mouse paints. Noita but tiny.

## "Random things that end up Gaussian"

- `galton` — see above, canonical example.
- `random_walks` — Many 1D random walkers; histogram their positions.
  Central limit theorem visualized.
- `buffon` — Buffon's needle drops approximating π in real time.
- `clt_sums` — Sums of N uniform variables collapsing to a Gaussian as
  N grows.

## Space

- `solar_system` — Top-down solar system. Planets move at real relative
  speeds, ~1 day per frame. Can't do orbits and body sizes both to scale.
- `starfield` — Classic demoscene starfield flying through space.

## Algorithms

- `sort_viz` — Sorting algorithm visualizer. Cycle bubble/insertion/
  quicksort/radix/merge. Bars encode value, highlight = compare/swap.
- `defrag` — "Defragmenter". 64×64 starts as a scrambled grid of 4×4
  tiles colored by a spectrum; sort to rainbow order using a real
  block-sort algorithm. Show read/write heads moving.
- `maze` — Generate (recursive backtracker / Prim's) → solve (A* / BFS) →
  dissolve → repeat.
- `pathfind` — A* or Dijkstra on a grid with random obstacles; frontier
  expansion animates.
- `tsp` — Traveling salesman. 20 random cities, random tour, run 2-opt /
  simulated annealing, watch edge crossings disappear.

## Chess / games

- `chess_games` — 56×56 board up top, 8-row black/white eval gauge along
  the bottom. Cycle Immortal / Opera / Fischer-Spassky 6 /
  Kasparov-Topalov 99. No text (unreadable at this resolution).
- `snake_ai` — Snake AI playing itself (Hamiltonian cycle or BFS with
  safety heuristics). Never dies, fills the board.
- `pong_ai` — Two AIs playing pong forever.
- `tetris_ai` — Dellacherie-style heuristic placer.

## Demoscene / classic FX

- `fire` — Classic 90s demoscene fire. Seed bottom, propagate up with
  cooling + jitter.
- `plasma` — Animated plasma from sums of sine fields.
- `metaballs` — Metaballs with threshold contouring.
- `tunnel` — Texture-mapped tunnel.
- `matrix` — Matrix rain with green glyphs.
- `rotozoom` — Rotating/zooming texture.
- `raymarch` — Tiny SDF ray-marcher (sphere + plane is enough).
- `flow_field` — 300 particles riding a Perlin-noise vector field,
  short trailing lines.

## Audio (host-captured)

- `spectrum` — FFT bars from host mic (sounddevice + numpy).
- `scope` — Oscilloscope waveform.
- `beat` — Energy-based beat detector; whole screen pulses on beat.

## Ambient / data

- `clock` — Analog clock. 2px hour hand, 1px minute, red second.
- `word_clock` — "IT IS HALF PAST TWO" style. Hard at 64×64; deferred.
- `weather` — Current weather icon + temperature. Needs API key.
- `ping_heatmap` — Ping a grid of hosts; color cells by latency.

## Fun / playable

- `dot` — Smoke test: arrow keys move a colored pixel.
- `ball` — SHIPPED. Bouncing ball at 45°.
- `pong` — Playable pong (keyboard).
- `snake` — Playable snake (keyboard).
- `life_zoo` — Game of Life with curated Gosper glider gun, pulsar, etc.

## Cut

- `earth_rotate` — 64×64 too small for recognizable continents.
- `dvd_logo` — per your call.
- `buddhabrot` — needs significant precompute; low priority, not cut but
  parked.

## Possibly later

- Home Assistant integration (presence → program switch).
- Web dashboard to pick programs remotely.
- Beat-matching: `beat.py` drives another program's time dilation.
- Multi-device: sync multiple Pixoos over the LAN.
