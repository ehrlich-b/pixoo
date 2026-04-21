#!/usr/bin/env python3
"""pixoo — tiny CLI for Divoom Pixoo-64 on the LAN. Stdlib only."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import urllib.error

from pixoolib import state
from pixoolib.discover import discover, pick
from pixoolib.runtime import Program, Runner
from pixoolib.session import ensure_primed, get_client


def cmd_discover(_: argparse.Namespace) -> None:
    d = pick(discover())
    state.save(d)
    print(f"selected {d['ip']} (saved to {state.STATE_FILE.name})")


def cmd_info(_: argparse.Namespace) -> None:
    c = get_client()
    print(f"ip: {c.ip}")
    print(json.dumps(c.all_conf(), indent=2))


def cmd_text(args: argparse.Namespace) -> None:
    c = get_client()
    ensure_primed(c)
    print(json.dumps(c.text(args.text, color=args.color, x=args.x, y=args.y,
                             speed=args.speed, align=args.align)))


def cmd_clear(_: argparse.Namespace) -> None:
    print(json.dumps(get_client().clear_text()))


def cmd_channel(args: argparse.Namespace) -> None:
    print(json.dumps(get_client().set_channel(args.index)))
    state.set_primed(False)  # channel switch invalidates the HTTP frame buffer


def cmd_brightness(args: argparse.Namespace) -> None:
    print(json.dumps(get_client().set_brightness(args.value)))


def cmd_raw(args: argparse.Namespace) -> None:
    payload = json.loads(args.json)
    print(json.dumps(get_client().post(payload), indent=2))


def _resolve_program(name: str) -> type[Program]:
    try:
        mod = importlib.import_module(f"programs.{name}")
    except ImportError as e:
        print(f"no such program: {name} ({e})", file=sys.stderr)
        sys.exit(1)
    for attr in vars(mod).values():
        if isinstance(attr, type) and issubclass(attr, Program) and attr is not Program:
            return attr
    print(f"no Program subclass found in programs/{name}.py", file=sys.stderr)
    sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    from pixoolib.term import TerminalDriver

    prog_cls = _resolve_program(args.program)
    use_term = not args.device  # --device implies no terminal; --mirror uses default
    use_device = args.device or args.mirror
    drivers = []
    if use_term:
        drivers.append(TerminalDriver())
    if use_device:
        from pixoolib.device import PixooDriver

        drivers.append(PixooDriver(get_client()))
        state.set_primed(True)  # PixooDriver.start() primes the buffer
    Runner(prog_cls(), drivers, fps=args.fps).run()


def main() -> None:
    p = argparse.ArgumentParser(prog="pixoo")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("discover", help="scan LAN and pick a device")
    sub.add_parser("info", help="dump current device config")
    sub.add_parser("clear", help="clear any pushed text")

    t = sub.add_parser("text", help="push static/scrolling text")
    t.add_argument("text")
    t.add_argument("--color", default="#FFFFFF")
    t.add_argument("--x", type=int, default=0)
    t.add_argument("--y", type=int, default=28)
    t.add_argument("--speed", type=int, default=10)
    t.add_argument("--align", type=int, default=1, help="1=left 2=middle 3=right")

    ch = sub.add_parser("channel", help="switch built-in channel")
    ch.add_argument("index", type=int,
                    help="0=faces 1=cloud 2=visualizer 3=custom 4=blackscreen")

    br = sub.add_parser("brightness", help="set brightness 0-100")
    br.add_argument("value", type=int)

    r = sub.add_parser("raw", help="POST arbitrary JSON to /post")
    r.add_argument("json", help='e.g. \'{"Command":"Channel/GetAllConf"}\'')

    rn = sub.add_parser("run", help="run a program from programs/<name>.py")
    rn.add_argument("program", help="program module name, e.g. ball")
    rn.add_argument("--device", action="store_true", help="push to Pixoo only")
    rn.add_argument("--mirror", action="store_true", help="terminal + Pixoo")
    rn.add_argument("--fps", type=float, default=30.0)

    args = p.parse_args()
    cmd = args.cmd or "discover"
    {
        "discover": cmd_discover,
        "info": cmd_info,
        "text": cmd_text,
        "clear": cmd_clear,
        "channel": cmd_channel,
        "brightness": cmd_brightness,
        "raw": cmd_raw,
        "run": cmd_run,
    }[cmd](args)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        print(f"network error: {e}", file=sys.stderr)
        sys.exit(1)
