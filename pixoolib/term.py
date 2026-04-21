"""TerminalDriver — ANSI truecolor half-block renderer, stdlib only.

64x64 pixoo → 32 rows x 64 cols terminal cells. Each cell is a ▀ where
fg = top pixel, bg = bottom pixel.
"""
from __future__ import annotations

import select
import sys
import termios
import tty

from .frame import Frame
from .runtime import Event

ENTER_ALT = "\x1b[?1049h"
EXIT_ALT = "\x1b[?1049l"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"
CURSOR_HOME = "\x1b[H"
CLEAR_SCREEN = "\x1b[2J"
RESET = "\x1b[0m"

ARROW = {"[A": "up", "[B": "down", "[C": "right", "[D": "left"}


class TerminalDriver:
    def __init__(self) -> None:
        self._saved_termios = None
        self._started = False

    def start(self) -> None:
        if not sys.stdout.isatty():
            raise RuntimeError("terminal driver requires a TTY")
        self._saved_termios = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        sys.stdout.write(ENTER_ALT + HIDE_CURSOR + CLEAR_SCREEN + CURSOR_HOME)
        sys.stdout.flush()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        sys.stdout.write(RESET + SHOW_CURSOR + EXIT_ALT)
        sys.stdout.flush()
        if self._saved_termios is not None:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._saved_termios)
        self._started = False

    def render(self, frame: Frame) -> None:
        p = frame.pixels
        buf = [CURSOR_HOME]
        last_t = last_b = None
        for row in range(32):
            top_base = row * 2 * 64 * 3
            bot_base = (row * 2 + 1) * 64 * 3
            for col in range(64):
                ti = top_base + col * 3
                bi = bot_base + col * 3
                t = (p[ti], p[ti + 1], p[ti + 2])
                b = (p[bi], p[bi + 1], p[bi + 2])
                if t != last_t or b != last_b:
                    buf.append(
                        f"\x1b[38;2;{t[0]};{t[1]};{t[2]};48;2;{b[0]};{b[1]};{b[2]}m"
                    )
                    last_t, last_b = t, b
                buf.append("\u2580")
            buf.append(RESET + "\n")
            last_t = last_b = None
        sys.stdout.write("".join(buf))
        sys.stdout.flush()

    def events(self) -> list[Event]:
        out: list[Event] = []
        fd = sys.stdin.fileno()
        while select.select([fd], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                if select.select([fd], [], [], 0.01)[0]:
                    seq = sys.stdin.read(2)
                    out.append(Event(kind="key", key=ARROW.get(seq, f"esc-{seq}")))
                else:
                    out.append(Event(kind="key", key="escape"))
            elif ch == "\x03":
                out.append(Event(kind="key", key="ctrl+c"))
            elif ch in ("\r", "\n"):
                out.append(Event(kind="key", key="enter"))
            else:
                out.append(Event(kind="key", key=ch))
        return out
