"""state.py + session.py behavior, stdlib unittest only.

No network, no hardware, no real state file: every test points
pixoolib.state.STATE_FILE at a scratch path inside tests/ and guarantees
cleanup even on failure. The real .pixoo-state.json at the project root is
snapshotted before and after and shown unchanged (it must not even be
touched by these tests).
"""
from __future__ import annotations

import hashlib
import os
import unittest
from pathlib import Path

import pixoolib.session as session
import pixoolib.state as state

SCRATCH = Path(__file__).resolve().parent / ".zz_scratch_state.json"


def _raise_if_called(*args, **kwargs):
    raise AssertionError("should never have been called")


def _snapshot_real_state() -> tuple:
    """(exists, mtime_ns, sha256) of the real .pixoo-state.json, or (False, None, None)."""
    real = Path(state.__file__).resolve().parent.parent / ".pixoo-state.json"
    if not real.exists():
        return (False, None, None)
    st = real.stat()
    return (True, st.st_mtime_ns, hashlib.sha256(real.read_bytes()).hexdigest())


BEFORE = _snapshot_real_state()


class SessionStateTest(unittest.TestCase):
    def setUp(self):
        self._original_state_file = state.STATE_FILE
        if SCRATCH.exists():
            SCRATCH.unlink()
        state.STATE_FILE = SCRATCH
        self.addCleanup(self._restore_state)

    def _restore_state(self):
        state.STATE_FILE = self._original_state_file
        if SCRATCH.exists():
            SCRATCH.unlink()

    def test_load_missing_file_returns_none(self):
        self.assertFalse(SCRATCH.exists())
        self.assertIsNone(state.load())

    def test_save_load_round_trip(self):
        state.save({"ip": "9.9.9.9"})
        self.assertEqual(state.load(), {"ip": "9.9.9.9"})

    def test_set_primed_merges_not_clobbers(self):
        state.save({"ip": "1.2.3.4"})
        state.set_primed(True)
        self.assertEqual(state.load(), {"ip": "1.2.3.4", "primed": True})

    def test_get_client_env_fast_path_never_touches_state_or_discovery(self):
        saved = os.environ.get("PIXOO_IP")
        os.environ["PIXOO_IP"] = "10.0.0.5"
        try:
            original_discover = session.discover
            session.discover = _raise_if_called
            try:
                c = session.get_client()
            finally:
                session.discover = original_discover
            self.assertEqual(c.ip, "10.0.0.5")
            # fast path never state.save()s, so scratch must still be absent
            self.assertFalse(SCRATCH.exists())
        finally:
            if saved is None:
                os.environ.pop("PIXOO_IP", None)
            else:
                os.environ["PIXOO_IP"] = saved

    def test_ensure_primed_already_primed_skips_prime(self):
        state.save({"primed": True})

        class FakeClient:
            def prime(self):
                raise AssertionError("prime() should not be called when already primed")

        session.ensure_primed(FakeClient())  # must not raise

    def test_ensure_primed_primes_when_primed_false(self):
        state.save({"primed": False})
        calls = []

        class FakeClient:
            def prime(self):
                calls.append(1)

        session.ensure_primed(FakeClient())
        self.assertEqual(len(calls), 1)
        self.assertEqual(state.load(), {"primed": True})

    def test_ensure_primed_primes_when_missing_and_merges_existing_keys(self):
        state.save({"ip": "5.5.5.5"})
        calls = []

        class FakeClient:
            def prime(self):
                calls.append(1)

        session.ensure_primed(FakeClient())
        self.assertEqual(len(calls), 1)
        self.assertEqual(state.load(), {"ip": "5.5.5.5", "primed": True})


def _report_real_state_after():
    after = _snapshot_real_state()
    print("\nREAL .pixoo-state.json safety proof:")
    print(f"  before suite: exists={BEFORE[0]} mtime_ns={BEFORE[1]} sha256={BEFORE[2]}")
    print(f"  after suite:  exists={after[0]} mtime_ns={after[1]} sha256={after[2]}")
    if not BEFORE[0] and not after[0]:
        print("  RESULT: did not exist before and does not exist after — untouched")
    elif BEFORE == after:
        print("  RESULT: identical before and after — untouched")
    else:
        print("  RESULT: CHANGED — real state file was touched! FAILURE")
    assert BEFORE == after, "real .pixoo-state.json changed across the suite"


unittest.addModuleCleanup(_report_real_state_after)
