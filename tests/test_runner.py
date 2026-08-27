"""Runner loop behaviour, stdlib unittest only.

Pins the exact global call ordering of pixoolib.runtime.Runner.run() plus the
quit-check, dt, setup-error, and KeyboardInterrupt paths. Every run() is made
fully deterministic by mocking pixoolib.runtime.time.monotonic and
pixoolib.runtime.time.sleep (run() is an unconditional while True that
real-sleeps at the bottom of every full iteration).
"""
from __future__ import annotations

import unittest
from unittest import mock

from pixoolib.frame import Frame
from pixoolib.runtime import QUIT_KEYS, Event, Program, Runner


class FakeDriver:
    """Records start/stop/render into a SHARED log so cross-driver ordering
    can be asserted; supports a scripted events() return sequence (each list
    entry is the value for one events() call), defaulting to [].
    """

    def __init__(self, name, log, events_seq=None):
        self.name = name
        self.log = log
        self.events_seq = list(events_seq) if events_seq is not None else []
        self._calls = 0

    def start(self):
        self.log.append(f"{self.name}.start")

    def stop(self):
        self.log.append(f"{self.name}.stop")

    def render(self, frame):
        self.log.append(f"{self.name}.render")

    def events(self):
        idx = self._calls
        self._calls += 1
        if idx < len(self.events_seq):
            return self.events_seq[idx]
        return []


class FakeProgram(Program):
    """Records update/render into the shared log; captures dt/events per
    update; optional setup()/update() exceptions. setup() is tracked as a
    separate counter (not in the shared log) so ordering assertions match the
    verified 8-item driver/render trace from CONTEXT, which excludes setup.
    """

    def __init__(self, log, setup_error=None, update_error=None):
        super().__init__()
        self.log = log
        self.setup_calls = 0
        self.update_dts = []
        self.update_events = []
        self._setup_error = setup_error
        self._update_error = update_error

    def setup(self):
        self.setup_calls += 1
        if self._setup_error is not None:
            raise self._setup_error

    def update(self, dt, events):
        self.log.append("program.update")
        self.update_dts.append(dt)
        self.update_events.append(list(events))
        if self._update_error is not None:
            raise self._update_error

    def render(self):
        self.log.append("program.render")
        return Frame.black()


class RunnerLoopTest(unittest.TestCase):
    def setUp(self):
        # run() never exits without a quit event and real-sleeps at the bottom
        # of each full iteration; mock both time.* calls so the loop is
        # deterministic (no wall clock, no real sleep) in every test.
        self.monotonic = mock.patch("pixoolib.runtime.time.monotonic").start()
        self.sleep = mock.patch("pixoolib.runtime.time.sleep").start()
        self.addCleanup(mock.patch.stopall)

    def test_global_ordering_trace(self):
        # d2 returns a quit key on its SECOND events() call, d1 always [].
        # Exactly one full frame runs, and stop order is the reverse of start.
        log = []
        d1 = FakeDriver("d1", log)
        d2 = FakeDriver("d2", log, events_seq=[[], [Event(kind="key", key="q")]])
        prog = FakeProgram(log)
        r = Runner(prog, [d1, d2], fps=30.0)

        # Exactly 3 monotonic calls for one full iteration: last (pre-loop),
        # then now + slack inside the loop. The quit iteration calls it 0 times.
        self.monotonic.side_effect = [1.0, 1.1, 1.1]
        r.run()

        self.assertEqual(log, [
            "d1.start",
            "d2.start",
            "program.update",
            "program.render",
            "d1.render",
            "d2.render",
            "d2.stop",
            "d1.stop",
        ])

    def test_quit_triggering_frame_is_never_rendered(self):
        # The loop runs two iterations (d2 quits on its second events() poll)
        # but the quit check happens BEFORE update/render, so only one frame.
        self.assertIn("escape", QUIT_KEYS)
        log = []
        d1 = FakeDriver("d1", log)
        d2 = FakeDriver("d2", log, events_seq=[[], [Event(kind="key", key="escape")]])
        prog = FakeProgram(log)
        r = Runner(prog, [d1, d2], fps=30.0)
        self.monotonic.side_effect = [0.0, 0.0, 0.0]
        r.run()

        self.assertEqual(prog.setup_calls, 1)
        self.assertEqual(len(prog.update_dts), 1, "update must run exactly once")
        self.assertEqual(log.count("program.update"), 1)
        self.assertEqual(log.count("program.render"), 1)
        self.assertEqual(log.count("d1.render"), 1)
        self.assertEqual(log.count("d2.render"), 1)

    def test_non_quit_events_do_not_stop_the_loop(self):
        # A click on the first poll, then empty polls, then a real quit key on
        # the fourth poll. The three intervening non-quit iterations run full
        # frames before the loop finally quits on the click-free quit poll.
        click = Event(kind="click", x=1, y=2)
        log = []
        d1 = FakeDriver(
            "d1", log,
            events_seq=[[click], [], [], [Event(kind="key", key="q")]],
        )
        prog = FakeProgram(log)
        r = Runner(prog, [d1], fps=30.0)

        # 3 full iterations ran -> last (1) + 2 monotonic calls per full
        # iteration (now, slack) = 7 calls total.
        self.monotonic.side_effect = [0.0] * 7
        r.run()

        self.assertEqual(len(prog.update_dts), 3, "non-quit polls must run frames")
        self.assertEqual(prog.update_events[0], [click],
                         "click is forwarded to update() as a plain event")

    def test_dt_is_exact_now_minus_last_from_mocked_monotonic(self):
        # last = 10.0 (pre-loop), now = 12.5 (first iteration's update) -> the
        # dt received must be exactly 12.5 - 10.0 == 2.5, not just "close".
        log = []
        d1 = FakeDriver("d1", log)
        d2 = FakeDriver("d2", log, events_seq=[[], [Event(kind="key", key="q")]])
        prog = FakeProgram(log)
        r = Runner(prog, [d1, d2], fps=30.0)
        self.monotonic.side_effect = [10.0, 12.5, 12.5]  # last, now, slack
        r.run()

        self.assertEqual(len(prog.update_dts), 1)
        self.assertEqual(prog.update_dts[0], 2.5)

    def test_setup_exception_propagates_but_stops_still_run(self):
        # A plain Exception from setup() is NOT caught by `except
        # KeyboardInterrupt`, so it propagates out of run() -- but the finally
        # block still stops both drivers, in reversed order. (Verified against
        # the unmodified source; confirmed by the assertRaises below.)
        log = []
        d1 = FakeDriver("d1", log)
        d2 = FakeDriver("d2", log)
        prog = FakeProgram(log, setup_error=ValueError("boom"))
        r = Runner(prog, [d1, d2], fps=30.0)
        # monotonic is never reached: setup raises before the loop starts.
        with self.assertRaises(ValueError):
            r.run()
        self.assertEqual(log, ["d1.start", "d2.start", "d2.stop", "d1.stop"])

    def test_keyboard_interrupt_from_update_is_swallowed(self):
        # update() raising KeyboardInterrupt on its first call is swallowed by
        # run()'s `except KeyboardInterrupt: pass` -- run() returns normally
        # (does not re-raise) and finally still stops both drivers in reversed
        # order. Note: driver.start() sits OUTSIDE the try, so a KeyboardInterrupt
        # there would not be swallowed; everything from setup() onward is.
        log = []
        d1 = FakeDriver("d1", log)
        d2 = FakeDriver("d2", log)
        prog = FakeProgram(log, update_error=KeyboardInterrupt())
        r = Runner(prog, [d1, d2], fps=30.0)
        # last + now = 2 monotonic calls; update raises before slack/sleep.
        self.monotonic.side_effect = [5.0, 5.0]
        try:
            r.run()
        except BaseException as exc:  # pragma: no cover
            self.fail(f"run() must swallow KeyboardInterrupt, got {exc!r}")
        self.assertEqual(log, ["d1.start", "d2.start", "program.update",
                               "d2.stop", "d1.stop"],
                         "update logged, then KI swallowed, stops reversed")
        self.assertEqual(len(prog.update_dts), 1)


if __name__ == "__main__":
    unittest.main()
