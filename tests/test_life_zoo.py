"""Life zoo (programs/life_zoo.py) pinned with stdlib unittest only.

No hardware, no network, no random: every test drives the CA state machine
directly (toroidal grid, age/ghost bookkeeping) with hand-derived oracles.
"""
from __future__ import annotations

import unittest

from programs.life_zoo import (
    ALIVE_AGE_MAX,
    GHOST_AGE_MAX,
    PATTERNS,
    TICK_HZ,
    LifeZoo,
    _parse,
)
from pixoolib.frame import HEIGHT, WIDTH

# One update() call with dt = 1/TICK_HZ steps exactly one generation: the
# tick gate is `if self._tick_dt < 1.0/TICK_HZ: return`, and 1/15 < 1/15 is
# False. Phase gate needs ~10s of accumulated dt to fire; single/double
# ticks never get close.
TICK = 1.0 / TICK_HZ


def _scenario(lz: LifeZoo, cells: set):
    """Reset state and place live cells (fresh age 1, zero ghosts)."""
    lz._grid = [[0] * WIDTH for _ in range(HEIGHT)]
    lz._age = [[0] * WIDTH for _ in range(HEIGHT)]
    lz._ghost = [[0] * WIDTH for _ in range(HEIGHT)]
    lz._tick_dt = 0.0
    lz._phase_t = 0.0
    for x, y in cells:
        lz._grid[y][x] = 1
        lz._age[y][x] = 1


def _live_set(lz: LifeZoo) -> set:
    return {(x, y) for y in range(HEIGHT) for x in range(WIDTH) if lz._grid[y][x]}


class ParseTest(unittest.TestCase):
    def test_parse_two_by_two_mirrors_grid(self):
        self.assertEqual(_parse(["X.", ".X"]), [(0, 0), (1, 1)])

    def test_parse_empty(self):
        self.assertEqual(_parse([]), [])

    def test_parse_dotted_row_contributes_nothing(self):
        self.assertEqual(_parse(["X.", ".."]), [(0, 0)])
        self.assertEqual(_parse([".", "..", "..."]), [])


class StillLifeBlockTest(unittest.TestCase):
    def test_block_survives_one_tick_with_age_2(self):
        block = {(20, 20), (21, 20), (20, 21), (21, 21)}
        lz = LifeZoo()
        lz.setup()
        _scenario(lz, block)

        lz.update(TICK, [])

        self.assertEqual(_live_set(lz), block)
        for x, y in block:
            with self.subTest(cell=(x, y)):
                self.assertEqual(lz._age[y][x], 2, "age increments 1 -> 2")


class GliderTest(unittest.TestCase):
    def test_glider_translates_plus_1_1_after_four_ticks(self):
        seed = {(21, 20), (22, 21), (20, 22), (21, 22), (22, 22)}
        expected = {(21, 23), (22, 21), (22, 23), (23, 22), (23, 23)}
        lz = LifeZoo()
        lz.setup()
        _scenario(lz, seed)

        for _ in range(4):
            lz.update(TICK, [])

        self.assertEqual(_live_set(lz), expected,
                         "seed translated by exactly (+1, +1)")


class DeathAndGhostTest(unittest.TestCase):
    def _isolated_dead_cell(self, ghost: int) -> LifeZoo:
        lz = LifeZoo()
        lz.setup()
        _scenario(lz, {(30, 30)})  # no neighbours: dies of underpopulation
        lz._age[30][30] = 5
        lz._ghost[30][30] = ghost
        return lz

    def test_death_resets_age_and_decrements_ghost(self):
        lz = self._isolated_dead_cell(ghost=10)

        lz.update(TICK, [])

        self.assertEqual(lz._age[30][30], 0, "dead cell's age resets to 0")
        self.assertEqual(lz._ghost[30][30], 9, "ghost decrements by exactly 1")

    def test_ghost_floor_at_zero_never_negative(self):
        lz = self._isolated_dead_cell(ghost=0)

        lz.update(TICK, [])

        self.assertEqual(lz._ghost[30][30], 0, "floor-at-zero guard holds")


class AgeCapTest(unittest.TestCase):
    def test_alive_age_never_exceeds_max_already_at_cap(self):
        block = {(20, 20), (21, 20), (20, 21), (21, 21)}
        lz = LifeZoo()
        lz.setup()
        _scenario(lz, block)
        for x, y in block:
            lz._age[y][x] = ALIVE_AGE_MAX  # already at the cap pre-tick

        lz.update(TICK, [])

        for x, y in block:
            with self.subTest(cell=(x, y)):
                self.assertEqual(lz._age[y][x], ALIVE_AGE_MAX,
                                 "pre-existing cap survives the tick uncapped")
        self.assertTrue(all(lz._age[y][x] <= ALIVE_AGE_MAX for x, y in block))

    def test_alive_age_clamps_to_max_from_below(self):
        block = {(20, 20), (21, 20), (20, 21), (21, 21)}
        lz = LifeZoo()
        lz.setup()
        _scenario(lz, block)
        for x, y in block:
            lz._age[y][x] = ALIVE_AGE_MAX - 1

        lz.update(TICK, [])

        for x, y in block:
            with self.subTest(cell=(x, y)):
                self.assertEqual(lz._age[y][x], ALIVE_AGE_MAX,
                                 "min() clamps to ALIVE_AGE_MAX")


class PatternsTableTest(unittest.TestCase):
    def test_six_patterns_each_a_valid_5_tuple(self):
        self.assertEqual(len(PATTERNS), 6)
        for p in PATTERNS:
            with self.subTest(pattern=p):
                self.assertIsInstance(p, tuple)
                self.assertEqual(len(p), 5)
                name, cells, ox, oy, phase = p
                self.assertIsInstance(name, str)
                self.assertIsInstance(cells, list)
                self.assertIsInstance(ox, int)
                self.assertIsInstance(oy, int)
                self.assertIsInstance(phase, float)

    def test_every_pattern_round_trips_through_parse(self):
        for p in PATTERNS:
            name, cells, _, _, _ = p
            with self.subTest(name=name):
                self.assertTrue(cells, f"{name} must have at least one live cell")
                max_x = max(x for x, _ in cells)
                max_y = max(y for _, y in cells)
                rows = ["." * (max_x + 1) for _ in range(max_y + 1)]
                for x, y in cells:
                    rows[y] = rows[y][:x] + "X" + rows[y][x + 1:]
                self.assertEqual(sorted(_parse(rows)), sorted(cells),
                                 "cell_list is exactly _parse of its ASCII grid")


if __name__ == "__main__":
    unittest.main()
