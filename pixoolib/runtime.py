"""Program base class, input Event type, and the Runner loop."""
from __future__ import annotations

import time
import math
import sys
from dataclasses import dataclass
from typing import Optional, Protocol

from .frame import Frame


@dataclass
class Event:
    kind: str  # "key", "click", "scroll"
    key: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    dx: Optional[int] = None
    dy: Optional[int] = None


QUIT_KEYS = {"q", "ctrl+c", "escape"}


class Driver(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def render(self, frame: Frame) -> None: ...
    def events(self) -> list[Event]: ...


class Program:
    """Override update() / render(). setup() is optional.

    Programs receive CLI --arg KEY=VALUE pairs as a plain str→str dict on
    self.params. Use `int(self.params.get("n", default))` etc in setup().
    Keeping the parsing on the program side keeps the CLI type-agnostic."""

    DESCRIPTION: str = ""
    FPS = 30.0
    MAX_WORLDS = 1
    DEVICE_BRIGHTNESS = None

    def __init__(self, **params: str) -> None:
        self.params: dict[str, str] = params

    def setup(self) -> None:
        pass

    def update(self, dt: float, events: list[Event]) -> None:
        pass

    def render(self) -> Frame:
        raise NotImplementedError

    def render_worlds(self) -> list[Frame]:
        return [self.render()]

    def status(self) -> str:
        return self.DESCRIPTION + " | q / Esc to quit"


class Runner:
    def __init__(self, program: Program, drivers: list[Driver], fps: float = 30.0):
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("fps must be finite and greater than zero")
        self.program = program
        self.drivers = drivers
        self.target_dt = 1.0 / fps

    def run(self, duration: float | None = None) -> None:
        if duration is not None and (not math.isfinite(duration) or duration <= 0):
            raise ValueError("duration must be finite and greater than zero")
        started = []
        try:
            # Reject invalid program parameters before taking over a terminal
            # or changing a device. Starting drivers belongs inside cleanup.
            self.program.setup()
            for driver in self.drivers:
                started.append(driver)
                driver.start()
            began = last = time.monotonic()
            while True:
                events = [event for d in self.drivers for event in d.events()]
                if any(e.kind == "key" and e.key in QUIT_KEYS for e in events):
                    return
                now = time.monotonic()
                if duration is not None and now - began >= duration:
                    return
                self.program.update(now - last, events)
                last = now
                frames = self.program.render_worlds()
                for driver in self.drivers:
                    if hasattr(driver, "render_worlds"):
                        driver.render_worlds(frames)
                    else:
                        index = getattr(driver, "world_index", 0)
                        driver.render(frames[index])
                slack = self.target_dt - (time.monotonic() - now)
                if slack > 0:
                    time.sleep(slack)
        except KeyboardInterrupt:
            pass
        finally:
            # A failed stop must not prevent restoration of the terminal or
            # shutdown of independent device workers.
            for driver in reversed(started):
                try:
                    driver.stop()
                except Exception as exc:
                    print(f"driver cleanup failed: {exc}", file=sys.stderr)
