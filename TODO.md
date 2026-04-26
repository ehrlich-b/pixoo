# Pixoo-64 todo

What to actually build, in roughly the order we'd attack it. `IDEAS.md` is
the brainstorm universe; this file is the work list.

## Shipped

- [x] CLI fast-path: `discover`, `info`, `text`, `channel`, `brightness`,
      `clear`, `raw`.
- [x] `programs/ball.py` — bouncing ball smoke test.
- [x] `mandelbrot_zoom.py` — standalone landmark tour, bursty 40-min frame
      buffer, in-orbit smooth pan for double-zooms.
- [x] Split `programs/` vs `probes/`; Makefile `stress` target updated.
- [x] `./pixoo list` — shows programs + probes with DESCRIPTION / docstring.
- [x] `./pixoo run` (no arg) — numbered menu picker.
- [x] `./pixoo probe <name>` — runs a script from `probes/`.
- [x] `probes/show_ip.py` — paints the cached IP on the device.

## Batch 1 — quick wins (pure stdlib, no deps)

- [ ] `programs/life.py` — Conway's Game of Life, cycle seeds.
- [ ] `programs/langton.py` — Langton's ant, many steps/frame.
- [ ] `programs/eca.py` — elementary CA, cycle iconic rules.
- [ ] `programs/starfield.py` — demoscene starfield.
- [ ] `programs/fire.py` — classic fire effect.

## Batch 2 — physics

- [ ] `programs/pendulum.py` — double pendulum with trail.
- [ ] `programs/cradle.py` — Newton's cradle.
- [ ] `programs/galton.py` — bean machine, Gaussian pile.
- [x] `programs/nbody.py` — 2D gravity, Chenciner-Montgomery figure-8.
- [ ] `programs/sand.py` — falling-sand powder toy, mouse to paint.

## Batch 3 — algorithms

- [ ] `programs/sort_viz.py` — cycle sorting algorithms.
- [ ] `programs/defrag.py` — 4×4 tile defragmenter.
- [ ] `programs/maze.py` — generate → solve → repeat.
- [ ] `programs/pathfind.py` — A*/Dijkstra frontier.
- [ ] `programs/tsp.py` — 2-opt / SA untangler on 20 cities.

## Batch 4 — generative / mesmerizing

- [ ] `programs/flow_field.py` — Perlin flow field with trailing particles.
- [ ] `programs/plasma.py` — sine-field plasma.
- [ ] `programs/matrix.py` — green glyph rain.
- [ ] `programs/metaballs.py` — threshold-contoured metaballs.
- [ ] `programs/dla.py` — diffusion-limited aggregation.

## Batch 5 — emergent math

- [ ] `programs/sandpile.py` — abelian sandpile.
- [ ] `programs/ulam.py` — Ulam prime spiral.
- [ ] `programs/schelling.py` — segregation model.
- [ ] `programs/boids.py` — flocking.
- [ ] `programs/reaction.py` — Gray-Scott reaction-diffusion (numpy).

## Batch 6 — fractals & L-systems

- [ ] `programs/julia.py` — Julia set with drifting `c`.
- [ ] `programs/newton.py` — Newton basins.
- [ ] `programs/ifs.py` — Barnsley fern / chaos-game Sierpinski.
- [ ] `programs/lsystem.py` — L-system tree / Koch / dragon.

## Batch 7 — chess / self-playing

- [ ] `programs/chess_games.py` — 56×56 board + 8-row eval gauge,
      cycle famous games.
- [ ] `programs/snake_ai.py` — Hamiltonian / BFS self-player.
- [ ] `programs/pong_ai.py` — two AIs forever.
- [ ] `programs/tetris_ai.py` — Dellacherie heuristic placer.

## Batch 8 — ambient / data

- [ ] `programs/clock.py` — analog clock.
- [ ] `programs/dot.py` — arrow-key smoke test (if we decide ball isn't it).
- [ ] `programs/ping_heatmap.py` — LAN ping latency grid.
- [ ] `programs/weather.py` — icon + temperature (needs API key).

## Batch 9 — audio (host mic)

- [ ] `programs/spectrum.py` — FFT bars (sounddevice + numpy).
- [ ] `programs/scope.py` — oscilloscope.
- [ ] `programs/beat.py` — beat-reactive pulse.

## Batch 10 — demoscene deeper cuts

- [ ] `programs/tunnel.py` — textured tunnel.
- [ ] `programs/rotozoom.py` — rotozoomer.
- [ ] `programs/raymarch.py` — SDF sphere + plane.
- [ ] `programs/waves.py` — 2D wave equation.
- [ ] `programs/heat.py` — heat diffusion.
- [ ] `programs/spring_mesh.py` — cloth sim.

## Infra / ergonomics backlog

- [ ] `./pixoo run --random` — pick a program uniformly at random.
- [ ] `./pixoo run --playlist` — cycle programs on a timer.
- [ ] `./pixoo stop` — pkill the running daemon (mirrors Makefile `stop`).
- [ ] Program arg-passing — let programs declare argparse specs and receive
      them (e.g. `./pixoo run eca --rule 110`).
- [ ] Dep lazy-install into `.venv/` on first `run` of a program that needs
      numpy / Pillow / sounddevice. (Per CLAUDE.md plan.)

## Cut / parked

- `earth_rotate` — unreadable at 64×64.
- `dvd_logo` — not interesting enough.
- `buddhabrot` — needs offline precompute; defer.
- `word_clock` — text legibility too hard at this resolution.
