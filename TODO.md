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

- [x] `programs/life.py` — Conway's Game of Life, cycle seeds.
- [x] `programs/langton.py` — Langton's ant, many steps/frame.
- [x] `programs/eca.py` — elementary CA, cycle iconic rules.
- [x] `programs/starfield.py` — demoscene starfield.
- [x] `programs/fire.py` — classic fire effect.

## Batch 2 — physics

- [x] `programs/pendulum.py` — double pendulum with trail.
- [x] `programs/cradle.py` — Newton's cradle.
- [x] `programs/galton.py` — bean machine, Gaussian pile.
- [x] `programs/nbody.py` — 2D gravity, Chenciner-Montgomery figure-8.
- [x] `programs/sand.py` — falling-sand powder toy.

## Batch 3 — algorithms

- [x] `programs/sort_viz.py` — cycle sorting algorithms.
- [x] `programs/defrag.py` — 4×4 tile defragmenter.
- [x] `programs/maze.py` — generate → solve → repeat.
- [x] `programs/pathfind.py` — A*/Dijkstra frontier.
- [x] `programs/tsp.py` — 2-opt / SA untangler on 20 cities.

## Batch 4 — generative / mesmerizing

- [x] `programs/flow_field.py` — sine-field flow with trailing particles.
- [x] `programs/plasma.py` — sine-field plasma.
- [x] `programs/matrix.py` — green glyph rain.
- [x] `programs/metaballs.py` — threshold-contoured metaballs.
- [x] `programs/dla.py` — diffusion-limited aggregation.

## Batch 5 — emergent math

- [x] `programs/sandpile.py` — abelian sandpile.
- [x] `programs/ulam.py` — Ulam prime spiral.
- [x] `programs/schelling.py` — segregation model.
- [x] `programs/boids.py` — flocking.
- [ ] `programs/reaction.py` — Gray-Scott reaction-diffusion (numpy).

## Batch 6 — fractals & L-systems

- [x] `programs/julia.py` — Julia set with drifting `c`.
- [x] `programs/newton.py` — Newton basins.
- [x] `programs/ifs.py` — Barnsley fern / chaos-game Sierpinski.
- [x] `programs/lsystem.py` — L-system tree / Koch / dragon.

## Batch 7 — chess / self-playing

- [ ] `programs/chess_games.py` — 56×56 board + 8-row eval gauge,
      cycle famous games.
- [x] `programs/snake_ai.py` — BFS self-player.
- [x] `programs/pong_ai.py` — two AIs forever.
- [x] `programs/tetris_ai.py` — Dellacherie heuristic placer.

## Batch 8 — ambient / data

- [x] `programs/clock.py` — analog clock.
- [x] `programs/dot.py` — arrow-key smoke test (if we decide ball isn't it).
- [ ] `programs/ping_heatmap.py` — LAN ping latency grid.
- [ ] `programs/weather.py` — icon + temperature (needs API key).

## Batch 9 — audio (host mic)

- [ ] `programs/spectrum.py` — FFT bars (sounddevice + numpy).
- [ ] `programs/scope.py` — oscilloscope.
- [ ] `programs/beat.py` — beat-reactive pulse.

## Batch 10 — demoscene deeper cuts

- [x] `programs/tunnel.py` — textured tunnel.
- [x] `programs/rotozoom.py` — rotozoomer.
- [x] `programs/raymarch.py` — SDF sphere + plane.
- [x] `programs/waves.py` — 2D wave equation.
- [x] `programs/heat.py` — heat diffusion.
- [x] `programs/spring_mesh.py` — cloth sim.

## Batch 11 — bonus from IDEAS

- [x] `programs/forest_fire.py` — growth + lightning CA.
- [x] `programs/wireworld.py` — copper rings + electron pulses.
- [x] `programs/magnet_pendulum.py` — basin map of attractor.
- [x] `programs/solar_system.py` — top-down 8 planets at scaled periods.
- [x] `programs/random_walks.py` — many 1D walkers + histogram.
- [x] `programs/buffon.py` — needles for π.
- [x] `programs/bear.py` — four-season animated scene with cub + papa.
- [x] `programs/unicorn.py` — sky + rainbow + walking unicorn.
- [x] `programs/attractors.py` — Lorenz attractor with rotating viewpoint.
- [x] `programs/kaleidoscope.py` — 6-fold mirrored sine field.
- [x] `programs/clt_sums.py` — sum of N uniforms approaching Gaussian.
- [x] `programs/life_zoo.py` — curated Life patterns (gun, pulsar, acorn).
- [x] `programs/voronoi.py` — drifting sites + edge highlights.
- [x] `programs/phyllotaxis.py` — golden-angle sunflower spiral grows.
- [x] `programs/truchet.py` — quarter-arc tiles flow into curves.
- [x] `programs/fireworks.py` — rocket bursts with colored particles.
- [x] `programs/harmonograph.py` — coupled-pendulum traces with reseed.
- [x] `programs/lightning.py` — recursive bolts over storm-sky + rain.
- [x] `programs/cube3d.py` — rotating wireframe cube with depth shading.

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
