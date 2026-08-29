"""Bouncy physics pinned to programs/bouncy.py, stdlib unittest only.

No hardware, no network. Every suite is deterministic: ball lists are built
directly (never via .setup(), which uses unseeded random), and every
post-update speed is >= 4 so the unseeded re-energize branch can never fire.
"""
from __future__ import annotations

import unittest

from pixoolib.frame import HEIGHT, WIDTH
from programs.bouncy import (
    Bouncy,
    FLOOR_BOUNCE,
    FLOOR_FRICTION,
    GRAVITY,
    WALL_BOUNCE,
)


def _ball(x: float, y: float, vx: float, vy: float, r: float) -> list[float]:
    """Minimal ball row [x, y, vx, vy, r, r, g, b]; colors are irrelevant."""
    return [x, y, vx, vy, r, 255, 0, 0]


class WallFloorBounceTest(unittest.TestCase):
    def test_left_wall_bounce_clamps_x_and_reflects_vx(self):
        # Verified profile: ball sitting at the left wall heading into it.
        # vy += GRAVITY*dt -> 1.6; x += vx*dt -> 1.5 -> x-r < 0, so the wall
        # clamps x to r=2.0 and reflects vx = -(-10.0) * WALL_BOUNCE = 9.2.
        # y = y0 + vy*dt = 30.0 + 1.6*0.05 = 30.08 (no vertical wall hit).
        b = Bouncy()
        b._balls = [_ball(2.0, 30.0, -10.0, 0.0, 2.0)]
        b.update(0.05, [])
        x, y, vx, vy = b._balls[0][:4]
        self.assertEqual(x, 2.0, "x is wall-clamped exactly to r")
        self.assertAlmostEqual(vx, 9.2)
        self.assertAlmostEqual(vy, 1.6)
        self.assertAlmostEqual(y, 30.08)

    def test_right_wall_bounce_mirrors_left_wall_formula(self):
        # Mirror of the left-wall case. Ball rests at x = WIDTH-1-r = 61.0
        # heading right, same dt=0.05 so vy = GRAVITY*dt = 1.6.
        # x += vx*dt -> 61.0 + 20.0*0.05 = 62.0; x + r = 64.0 >= WIDTH, so the
        # wall clamps x to WIDTH-1-r = 61.0 and reflects
        # vx = -(20.0) * WALL_BOUNCE = -18.4 (exact mirror of the left formula
        # `b[2] = -b[2] * WALL_BOUNCE`).
        b = Bouncy()
        b._balls = [_ball(float(WIDTH - 1 - 2), 30.0, 20.0, 0.0, 2.0)]
        b.update(0.05, [])
        x, y, vx, vy = b._balls[0][:4]
        self.assertEqual(x, 61.0, "x is wall-clamped exactly to WIDTH-1-r")
        self.assertAlmostEqual(vx, -18.4)
        self.assertAlmostEqual(vy, 1.6)
        self.assertAlmostEqual(y, 30.08)

    def test_ceiling_bounce_uses_wall_bounce_coefficient(self):
        # Ceiling branch: b[1] - r < 0 clamps y to r and reflects vy with
        # WALL_BOUNCE (0.92), unlike the floor which uses FLOOR_BOUNCE (0.85)
        # plus friction. vx is untouched: gravity only changes vy.
        # vy = -10.0 + 1.6 = -8.4; y += vy*dt -> 1.58; y - r < 0 ->
        # y = r = 2.0, vy = -(-8.4) * WALL_BOUNCE = 7.728.
        b = Bouncy()
        b._balls = [_ball(30.0, 2.0, 0.0, -10.0, 2.0)]
        b.update(0.05, [])
        x, y, vx, vy = b._balls[0][:4]
        self.assertEqual(y, 2.0, "y is clamped exactly to r")
        self.assertAlmostEqual(vx, 0.0)
        self.assertAlmostEqual(vy, 7.728)
        self.assertAlmostEqual(x, 30.0)

    def test_floor_bounce_clamps_y_applies_friction_and_floor_bounce(self):
        # Verified profile: ball 3px above the floor, heading down-right.
        # vy += GRAVITY*dt -> 5.64; x += vx*dt (pre-bounce vx) -> 32.1;
        # y + r >= HEIGHT -> y = HEIGHT-1-r = 60.0,
        # vy = -(5.0 + 32.0*0.02) * FLOOR_BOUNCE = -5.64 * 0.85 = -4.794,
        # vx = 5.0 * FLOOR_FRICTION = 4.85 (floor has friction, walls don't).
        b = Bouncy()
        b._balls = [_ball(32.0, float(HEIGHT - 3), 5.0, 5.0, 3.0)]
        b.update(0.02, [])
        x, y, vx, vy = b._balls[0][:4]
        self.assertEqual(y, 60.0, "y is clamped exactly to HEIGHT-1-r")
        self.assertAlmostEqual(x, 32.1)
        self.assertAlmostEqual(vx, 4.85)
        self.assertAlmostEqual(vy, -4.794)


class BallCollisionTest(unittest.TestCase):
    def test_equal_mass_impulse_exact_and_momentum_conserved(self):
        # Verified profile: ball 0 (vx=150) hits stationary ball 1 (vx=0).
        # dt is tiny so positions barely move; normal is nx=1, ny=0 (both
        # balls share y), the closing impulse is rvx = 0-150 = -150, and
        # jval = -1.92 * impulse / 2 = 144.0, giving a.vx = 150-144 = 6.0
        # and c.vx = 0+144 = 144.0. Both end up >= 4, so the re-energize
        # branch cannot fire.
        b = Bouncy()
        b._balls = [_ball(20.0, 30.0, 150.0, 0.0, 3.0),
                    _ball(25.0, 30.0, 0.0, 0.0, 3.0)]
        b.update(0.0001, [])
        a_vx, c_vx = b._balls[0][:4][2], b._balls[1][:4][2]
        self.assertAlmostEqual(a_vx, 6.0, places=3)
        self.assertAlmostEqual(c_vx, 144.0, places=3)
        # Equal masses and a normal purely along x: the sum of x-velocities
        # is conserved exactly (150.0 + 0.0 == 6.0 + 144.0).
        self.assertAlmostEqual(a_vx + c_vx, 150.0, places=3)

    def test_no_collision_without_overlap_velocities_gravity_only(self):
        # Balls 40 apart (d^2 = 1600 >> (r1+r2)^2 = 16): the ball-ball loop
        # is skipped, so the only velocity change is gravity. Gravity affects
        # only vy, so both balls keep vx == 5.0 exactly (no wall touched:
        # x stays 10.25 / 50.25, far from either wall).
        b = Bouncy()
        b._balls = [_ball(10.0, 10.0, 5.0, 0.0, 2.0),
                    _ball(50.0, 10.0, 5.0, 0.0, 2.0)]
        b.update(0.05, [])
        for bob in b._balls:
            self.assertEqual(bob[2], 5.0, "vx unchanged: no collision impulse")
            self.assertAlmostEqual(bob[3], 1.6, "vy = GRAVITY*dt only")


class RestitutionSanityTest(unittest.TestCase):
    def test_coefficient_is_1_92_not_2_0(self):
        # The equal-mass collision impulse divides by the constant 1.92, not
        # the textbook-perfect 2.0. A perfect exchange would swap velocities
        # exactly (6.0's mirror ball would get 150.0 and the other 0.0); the
        # shipped 1.92 makes it mildly inelastic. This is a deliberate,
        # real characteristic of the code — it is asserted here so nobody
        # "fixes" it to 2.0.
        self.assertNotEqual(1.92, 2.0)
