"""Program base class, input Event type, and the Runner loop."""
from __future__ import annotations

import time
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
    """Override update() / render(). setup() is optional."""

    def setup(self) -> None:
        pass

    def update(self, dt: float, events: list[Event]) -> None:
        pass

    def render(self) -> Frame:
        raise NotImplementedError


class Runner:
    def __init__(self, program: Program, drivers: list[Driver], fps: float = 30.0):
        self.program = program
        self.drivers = drivers
        self.target_dt = 1.0 / fps

    def run(self) -> None:
        for d in self.drivers:
            d.start()
        try:
            self.program.setup()
            last = time.monotonic()
            while True:
                events: list[Event] = []
                for d in self.drivers:
                    events.extend(d.events())
                for e in events:
                    if e.kind == "key" and e.key in QUIT_KEYS:
                        return
                now = time.monotonic()
                dt = now - last
                last = now
                self.program.update(dt, events)
                frame = self.program.render()
                for d in self.drivers:
                    d.render(frame)
                slack = self.target_dt - (time.monotonic() - now)
                if slack > 0:
                    time.sleep(slack)
        except KeyboardInterrupt:
            pass
        finally:
            for d in reversed(self.drivers):
                d.stop()
