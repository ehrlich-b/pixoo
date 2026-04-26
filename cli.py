#!/usr/bin/env python3
"""pixoo — tiny CLI for Divoom Pixoo-64 on the LAN. Stdlib only."""
from __future__ import annotations

import argparse
import importlib
import json
import pkgutil
import sys
import urllib.error

import programs
from pixoolib import state
from pixoolib.client import PixooClient
from pixoolib.discover import discover, enrich_verbose, pick
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


def _fmt_weather(w: dict | None) -> str:
    if not w or w.get("error_code") not in (0, None):
        return "-"
    t = w.get("CurTemp")
    cond = w.get("Weather", "") or ""
    hum = w.get("Humidity")
    if t is None:
        return "-"
    return f"{float(t):5.1f}C {cond[:8]:<8} h={hum}"


def cmd_scan(args: argparse.Namespace) -> None:
    devs = discover()
    if not devs:
        return
    if args.verbose:
        devs = enrich_verbose(devs)
        hdr = ("IP", "CH", "BRI", "CLOCK", "PWR", "TEMP/COND", "MAC")
        rows = [hdr]
        for d in devs:
            w = _fmt_weather(d.get("weather"))
            rows.append((
                d["ip"],
                str(d.get("channel", "?")),
                str(d.get("Brightness", "?")),
                str(d.get("CurClockId", "?")),
                str(d.get("PowerOnChannelId", "?")),
                w,
                d.get("mac") or "-",
            ))
    else:
        hdr = ("IP", "CH", "BRI", "CLOCK", "PWR")
        rows = [hdr]
        for d in devs:
            rows.append((
                d["ip"],
                str(d.get("channel", "?")),
                str(d.get("Brightness", "?")),
                str(d.get("CurClockId", "?")),
                str(d.get("PowerOnChannelId", "?")),
            ))
    widths = [max(len(r[i]) for r in rows) for i in range(len(hdr))]
    for i, row in enumerate(rows):
        line = "  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row))
        print(line)
        if i == 0:
            print("  ".join("-" * widths[j] for j in range(len(widths))))
    print(f"\n{len(devs)} device(s)")


def cmd_blink(args: argparse.Namespace) -> None:
    import signal
    import time

    c = PixooClient(args.ip)
    try:
        conf = c.all_conf()
    except Exception as e:
        print(f"{args.ip}: cannot reach device: {e}", file=sys.stderr)
        sys.exit(1)
    orig = int(conf.get("Brightness", 100))
    level = max(0, min(100, args.level))
    if orig == level:
        print(f"{args.ip}: already at brightness {orig}, bumping to {level - 5}")
        level = max(0, orig - 5)

    def restore() -> None:
        for attempt in range(4):
            try:
                c.set_brightness(orig)
                print(f"{args.ip}: restored to {orig}")
                return
            except Exception as e:
                if attempt == 3:
                    print(f"{args.ip}: failed to restore (try manually "
                          f"`./pixoo brightness {orig}` with PIXOO_IP={args.ip}): {e}",
                          file=sys.stderr)
                time.sleep(0.3)

    # SIGTERM → SystemExit so the finally block runs.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(130))

    print(f"{args.ip}: brightness {orig} -> {level} for {args.seconds}s (Ctrl-C to stop early)")
    try:
        c.set_brightness(level)
        time.sleep(args.seconds)
    except KeyboardInterrupt:
        print(f"\n{args.ip}: interrupted")
    finally:
        restore()


def cmd_raw(args: argparse.Namespace) -> None:
    payload = json.loads(args.json)
    print(json.dumps(get_client().post(payload), indent=2))


def _program_in_module(mod) -> type[Program] | None:
    for attr in vars(mod).values():
        if isinstance(attr, type) and issubclass(attr, Program) and attr is not Program:
            return attr
    return None


def _discover_programs() -> list[tuple[str, type[Program]]]:
    """All `programs.<name>` modules that contain a Program subclass, alphabetized.
    Modules that fail to import (missing optional deps, syntax errors) are skipped
    silently — they can't be run anyway."""
    found: list[tuple[str, type[Program]]] = []
    for info in pkgutil.iter_modules(programs.__path__):
        if info.ispkg or info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"programs.{info.name}")
        except Exception:
            continue
        cls = _program_in_module(mod)
        if cls is not None:
            found.append((info.name, cls))
    found.sort(key=lambda t: t[0])
    return found


def _resolve_program(name: str) -> type[Program]:
    try:
        mod = importlib.import_module(f"programs.{name}")
    except ImportError as e:
        print(f"no such program: {name} ({e})", file=sys.stderr)
        sys.exit(1)
    cls = _program_in_module(mod)
    if cls is None:
        print(f"no Program subclass found in programs/{name}.py", file=sys.stderr)
        sys.exit(1)
    return cls


def cmd_list(_: argparse.Namespace) -> None:
    progs = _discover_programs()
    if not progs:
        print("no programs found in programs/", file=sys.stderr)
        sys.exit(1)
    width = max(len(name) for name, _ in progs)
    print("programs (./pixoo run <name>):")
    for name, cls in progs:
        desc = cls.DESCRIPTION or "(no description)"
        print(f"  {name:<{width}}  {desc}")
    probes = _discover_probes()
    if probes:
        pwidth = max(len(name) for name, _ in probes)
        print("\nprobes (./pixoo probe <name>):")
        for name, desc in probes:
            print(f"  {name:<{pwidth}}  {desc or '(no description)'}")


def _discover_probes() -> list[tuple[str, str]]:
    """Non-Program scripts under probes/. Description = first line of module docstring."""
    import pathlib
    root = pathlib.Path(__file__).parent / "probes"
    if not root.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for path in sorted(root.glob("*.py")):
        if path.name.startswith("_"):
            continue
        desc = ""
        try:
            with path.open() as fp:
                src = fp.read(1024)
            if src.startswith('"""'):
                end = src.find('"""', 3)
                if end > 3:
                    desc = src[3:end].strip().splitlines()[0]
        except OSError:
            pass
        out.append((path.stem, desc))
    return out


def cmd_probe(args: argparse.Namespace) -> None:
    import pathlib
    import subprocess
    if not args.probe:
        probes = _discover_probes()
        if not probes:
            print("no probes found in probes/", file=sys.stderr)
            sys.exit(1)
        width = max(len(name) for name, _ in probes)
        for name, desc in probes:
            print(f"  {name:<{width}}  {desc or '(no description)'}")
        return
    root = pathlib.Path(__file__).parent / "probes"
    path = root / f"{args.probe}.py"
    if not path.exists():
        print(f"no such probe: {args.probe}", file=sys.stderr)
        sys.exit(1)
    sys.exit(subprocess.call([sys.executable, str(path), *args.probe_args]))


def _menu_pick_program() -> str:
    progs = _discover_programs()
    if not progs:
        print("no programs found in programs/", file=sys.stderr)
        sys.exit(1)
    width = max(len(name) for name, _ in progs)
    for i, (name, cls) in enumerate(progs, 1):
        desc = cls.DESCRIPTION or ""
        print(f"  [{i:>2}] {name:<{width}}  {desc}")
    try:
        choice = input("pick [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(1)
    if choice.isdigit() and 1 <= int(choice) <= len(progs):
        return progs[int(choice) - 1][0]
    for name, _ in progs:
        if name == choice:
            return name
    print(f"no such program: {choice}", file=sys.stderr)
    sys.exit(1)


def cmd_run(args: argparse.Namespace) -> None:
    from pixoolib.term import TerminalDriver

    name = args.program or _menu_pick_program()
    prog_cls = _resolve_program(name)
    # --snap alone runs headless (no TTY required); --mirror forces terminal on.
    use_term = args.mirror or not (args.device or args.snap)
    use_device = args.device or args.mirror
    drivers = []
    if use_term:
        drivers.append(TerminalDriver())
    if use_device:
        from pixoolib.device import PixooDriver

        drivers.append(PixooDriver(get_client()))
        state.set_primed(True)  # PixooDriver.start() primes the buffer
    if args.snap:
        from pixoolib.snapshot import SnapshotDriver

        drivers.append(SnapshotDriver(args.snap))
    params: dict[str, str] = {}
    for kv in args.arg or []:
        k, sep, v = kv.partition("=")
        if not sep:
            print(f"bad --arg {kv!r}: expected KEY=VALUE", file=sys.stderr)
            sys.exit(1)
        params[k] = v
    Runner(prog_cls(**params), drivers, fps=args.fps).run()


def main() -> None:
    p = argparse.ArgumentParser(prog="pixoo")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("discover", help="scan LAN and pick a device")
    sub.add_parser("info", help="dump current device config")
    sub.add_parser("clear", help="clear any pushed text")
    sub.add_parser("list", help="list available programs and probes")

    sc = sub.add_parser("scan", help="scan LAN and print a table (no menu, no save)")
    sc.add_argument("-v", "--verbose", action="store_true",
                    help="also fetch weather + MAC for each device")

    bl = sub.add_parser("blink", help="dim and restore brightness to identify a device")
    bl.add_argument("ip", help="target Pixoo IP")
    bl.add_argument("--seconds", type=float, default=3.0,
                    help="how long to hold the dimmed state (default 3)")
    bl.add_argument("--level", type=int, default=10,
                    help="brightness 0-100 during the blink (default 10)")

    pr = sub.add_parser("probe", help="run a script from probes/<name>.py")
    pr.add_argument("probe", nargs="?", help="probe module name; omit to list")
    pr.add_argument("probe_args", nargs=argparse.REMAINDER,
                    help="args forwarded to the probe script")

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
    rn.add_argument("program", nargs="?", help="program module name; omit to menu-pick")
    rn.add_argument("--device", action="store_true", help="push to Pixoo only")
    rn.add_argument("--mirror", action="store_true", help="terminal + Pixoo")
    rn.add_argument("--snap", nargs="?", const="/tmp/pixoo-latest.png",
                    metavar="PATH",
                    help="write latest frame PNG to PATH (default /tmp/pixoo-latest.png); "
                         "implies headless unless --mirror is also set")
    rn.add_argument("--fps", type=float, default=30.0)
    rn.add_argument("--arg", action="append", default=[], metavar="KEY=VALUE",
                    help="program param, repeatable (e.g. --arg n=3)")

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
        "list": cmd_list,
        "probe": cmd_probe,
        "scan": cmd_scan,
        "blink": cmd_blink,
    }[cmd](args)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        print(f"network error: {e}", file=sys.stderr)
        sys.exit(1)
