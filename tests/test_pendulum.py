"""Pendulum integrator invariants — stdlib unittest only.

Tests only the pure pieces of programs.pendulum: _deriv, _rk4_step and the
physics constants. No Frame, no device, no clock, no wall-clock timing.

State is the 4-tuple s = (t1, w1, t2, w2): two bob angles and two angular
velocities. DAMP is nonzero, so the system dissipates — energy is NOT
conserved, and RULE: no test below ever asserts conservation.
"""
from __future__ import annotations

import math
import random
import unittest

from programs.pendulum import (
    G, L1, L2, M1, M2, DAMP, SIM_DT,
    _deriv, _rk4_step,
)

# Energy is O(1..3); double-precision rounding on those values is ~1e-16 and
# RK4's local truncation error scales as SIM_DT^5 ~ 1e-12, so 1e-9 is a
# generous margin that absorbs every floating-point wrinkle we could see
# while still being orders of magnitude smaller than the ~1e-4..1e-3
# per-step energy gain a sign-flipped damping term would produce.
ENERGY_EPSILON = 1e-9


def _total_energy(s):
    """Kinetic + potential energy of the double pendulum (up to an
    additive constant; V's reference is both rods horizontal)."""
    t1, w1, t2, w2 = s
    t = (
        0.5 * M1 * (L1 * w1) ** 2
        + 0.5 * M2 * (
            (L1 * w1) ** 2
            + (L2 * w2) ** 2
            + 2 * L1 * L2 * w1 * w2 * math.cos(t1 - t2)
        )
    )
    v = -(M1 + M2) * G * L1 * math.cos(t1) - M2 * G * L2 * math.cos(t2)
    return t + v


class EquilibriumTest(unittest.TestCase):
    def test_deriv_at_rest_is_all_zeros(self):
        # Derivation by hand: with both angles and both velocities zero,
        # every term vanishes:
        #   - sin(t1) = sin(t2) = 0 kills the two gravity terms in dw1.
        #   - d = t1 - t2 = 0, so sd = sin(0) = 0 kills the coupling term
        #      -2*sd*M2*(...) in dw1 and the whole dw2 numerator
        #      (both are explicitly multiplied by sd).
        #   - the damping terms -DAMP*w1, -DAMP*w2 are zero at rest.
        #   - the returned angular velocities are literally w1 and w2 = 0.
        # One component may come out as -0.0 (e.g. -G*(2M1+M2)*sin(0) =
        # -0.0), which compares equal to 0.0, so compare elementwise with ==.
        self.assertEqual(_deriv((0.0, 0.0, 0.0, 0.0)), (0.0, 0.0, 0.0, 0.0))

    def test_rk4_keeps_hanging_rest_state(self):
        # A pendulum hanging straight down at rest must stay exactly there.
        # Every k_i of the RK4 butcher tableau is the zero deriv, so the
        # combined step is (0,0,0,0).
        self.assertEqual(_rk4_step((0.0, 0.0, 0.0, 0.0), SIM_DT),
                         (0.0, 0.0, 0.0, 0.0))


class OddSymmetryTest(unittest.TestCase):
    """Negating the whole state (both angles AND both velocities) mirrors the
    system, so _deriv(-s) == -_deriv(s) componentwise.

    Justification from the equations: sin is odd and cos is even, the
    coupling term uses sd * (even w*w terms), both w*w self-energy terms are
    even, and the damping term is LINEAR in w (so it flips with w). There is
    no even-in-w cross term and no cos(t1)-of-anything-odd anywhere, so every
    component is an odd function of the whole state. A wrong sign anywhere in
    _deriv breaks this property, which is what makes the test strong.
    """

    STATES = [
        (0.5, 0.3, -0.7, -0.2),
        (2.0, 0.0, 1.0, 0.0),
        (-1.3, 2.7, 0.9, -1.1),
        (3.1, -0.6, -2.4, 0.05),
        (0.0, 1.0, 0.0, -1.0),
        (0.0, 0.0, 0.0, 0.0),
    ]

    def test_deriv_is_odd_in_the_state(self):
        for s in self.STATES:
            neg_s = tuple(-x for x in s)
            for neg, pos in zip(_deriv(neg_s), _deriv(s)):
                self.assertTrue(math.isclose(-neg, pos, rel_tol=1e-12,
                                             abs_tol=1e-12),
                                msg=f"odd symmetry failed for s={s}")


class EnergyDissipationTest(unittest.TestCase):
    def test_energy_never_increases_and_strictly_decreases(self):
        s = (2.0, 0.0, 1.0, 0.0)      # released from rest, high up
        e0 = _total_energy(s)
        prev = e0
        for _ in range(8000):          # 8000 * SIM_DT = 40 simulated seconds
            s = _rk4_step(s, SIM_DT)
            e = _total_energy(s)
            # Never increases: allow ENERGY_EPSILON only for float noise.
            self.assertLessEqual(e, prev + ENERGY_EPSILON,
                                 f"energy rose {prev:.6f} -> {e:.6f}")
            prev = e
        # Strictly decreased overall: the pendulum gives up its initial
        # ~2.86 units of energy to damping.
        self.assertLess(e, e0)


class DampingTermTest(unittest.TestCase):
    def test_damping_is_linear_and_even_symmetric_in_w(self):
        # dw1's undamped part depends on w1 only through w1*w1 (it enters
        # solely as the even term w1*w1*L1*cd inside the coupling bracket)
        # plus the explicit -DAMP*w1. So comparing the state (t1,w1,t2,w2)
        # against (t1,-w1,t2,w2), the two undamped parts cancel and the
        # difference isolates exactly the linear damping term:
        #     dw1(w1) - dw1(-w1) = -2*DAMP*w1
        #     dw2(w1) - dw2(-w1) = 0            (dw2's w1 dependence is even)
        t1, w1, t2, w2 = 1.1, 0.7, 1.6, 0.9
        dp = _deriv((t1, w1, t2, w2))
        dn = _deriv((t1, -w1, t2, w2))
        self.assertAlmostEqual(dp[1] - dn[1], -2 * DAMP * w1, places=12)
        self.assertAlmostEqual(dp[3] - dn[3], 0.0, places=15)

    def test_reconstructed_undamped_term_matches(self):
        # Rebuild the undamped dw1/dw2 by hand from the documented equations
        # of motion, then check _deriv applied the damping exactly:
        #   _deriv(...)[1] == undamped_dw1 - DAMP*w1
        t1, w1, t2, w2 = 1.1, 0.7, 1.6, 0.9
        d = t1 - t2
        cd, sd = math.cos(d), math.sin(d)
        denom = 2 * M1 + M2 - M2 * math.cos(2 * d)
        undw1 = (
            -G * (2 * M1 + M2) * math.sin(t1)
            - M2 * G * math.sin(t1 - 2 * t2)
            - 2 * sd * M2 * (w2 * w2 * L2 + w1 * w1 * L1 * cd)
        ) / (L1 * denom)
        undw2 = (
            2 * sd * (
                w1 * w1 * L1 * (M1 + M2)
                + G * (M1 + M2) * math.cos(t1)
                + w2 * w2 * L2 * M2 * cd
            )
        ) / (L2 * denom)
        actual = _deriv((t1, w1, t2, w2))
        self.assertAlmostEqual(actual[1], undw1 - DAMP * w1, places=12)
        self.assertAlmostEqual(actual[3], undw2 - DAMP * w2, places=12)


class ConvergenceTest(unittest.TestCase):
    """RK4 is a 4th-order method.

    Compare one step of size h against two steps of size h/2 to the same
    final time. The difference is dominated by the single step's local
    truncation error c*(h**5) versus the two half-steps carrying
    2*c*(h/2)**5 = c*(h**5)/16; halving h shrinks that leading difference
    by 2**5 = 32 — that is why the value sits near 31.5, not 16. (The 16
    framing in the task is the fixed-total-time global-error ratio h**4 ->
    (h/2)**4; either framing confirms 4th order, so the band [16, 64] is
    wide enough to admit both while still kicking out a degraded scheme: an
    order-2 quadrature converges at 2**3 = 8 and order-1 at 4, both far
    below the lower bound.) Measured here: RK4 ~31.5, uniform-weight mutant
    ~8.0.

    This is a numerical-accuracy assertion, NOT a performance assertion —
    no wall-clock time is measured anywhere.
    """

    START = (2.0, 0.0, 1.0, 0.0)
    H = 0.05

    @staticmethod
    def _diff(a, b):
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _error_at(self, s, h):
        one = _rk4_step(s, h)
        two = _rk4_step(_rk4_step(s, h / 2), h / 2)
        return self._diff(one, two)

    def test_order_drops_as_h_halves(self):
        err_h = self._error_at(self.START, self.H)
        err_h2 = self._error_at(self.START, self.H / 2)
        ratio = err_h / err_h2
        self.assertGreater(err_h, err_h2 * 8, "error must shrink when h halves")
        self.assertGreater(ratio, 16.0)
        self.assertLess(ratio, 64.0)


class DeterminismTest(unittest.TestCase):
    def test_pure_deterministic_nomutating(self):
        s = (1.2, -0.4, 2.1, 0.8)
        a = _rk4_step(s, SIM_DT)
        b = _rk4_step(s, SIM_DT)
        self.assertEqual(a, b)
        self.assertEqual(s, (1.2, -0.4, 2.1, 0.8))  # input untouched
        self.assertIsNot(a, b)                       # fresh tuple each call
        self.assertIsInstance(a, tuple)
        self.assertEqual(len(a), 4)


class ChaosTest(unittest.TestCase):
    def test_small_perturbation_diverges(self):
        # Two copies differing by CHAOS_OFFSET = 2e-3 in t1. The displayed
        # multi-copy pendulum relies on this: copies that start essentially
        # on top of each other separate over time into different motion.
        # We only assert divergence (final separation >> initial), never a
        # Lyapunov exponent or any specific rate.
        base = (1.0, 0.3, 1.7, -0.4)
        a = base
        b = (base[0] + 2e-3, base[1], base[2], base[3])
        sep0 = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        for _ in range(3000):
            a = _rk4_step(a, SIM_DT)
            b = _rk4_step(b, SIM_DT)
        sepf = math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))
        self.assertGreater(sepf, sep0 * 10.0)


class LargeAngleTest(unittest.TestCase):
    def test_deriv_finite_way_past_pi(self):
        # Angles well past pi (plus a kick and a large theta2 spread) must
        # produce only finite components — no blow-up in the denominators.
        deriv = _deriv((50.0, -7.3, -33.0, 9.1))
        for v in deriv:
            self.assertTrue(math.isfinite(v))

    def test_denom_never_zero_for_these_masses(self):
        # denom = 2*M1 + M2 - M2*cos(2d). cos ranges over [-1, 1], so denom
        # ranges over [2*M1, 2*M1 + 2*M2]. With M1 = M2 = 1 that is [2, 4]:
        # the denominator is bounded away from zero for ANY angle, so the
        # formulae cannot blow up. Only a non-positive M1 (impossible here)
        # could ever push denom to zero.
        rng = random.Random(1234)
        for _ in range(200):
            t1 = rng.uniform(-1000.0, 1000.0)
            t2 = rng.uniform(-1000.0, 1000.0)
            d = t1 - t2
            denom = 2 * M1 + M2 - M2 * math.cos(2 * d)
            self.assertGreater(denom, 0.0)
            for v in _deriv((t1, 2.0, t2, -2.0)):
                self.assertTrue(math.isfinite(v))


if __name__ == "__main__":
    unittest.main()
