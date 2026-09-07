#!/usr/bin/env python3
"""Exercise every Program offline and export a frame gallery plus timing evidence.

python3 tools/audit_programs.py --output /tmp/pixoo-review
No hardware access or third-party dependencies. Timings exclude gallery export.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib
import json
import platform
import random
import statistics
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cli import _program_in_module
from pixoolib.frame import Frame
from pixoolib.snapshot import write_png


def audit(name: str, fps: int, seconds: int, output: Path) -> dict:
    result = {"name": name, "fps": fps, "seconds": seconds, "status": "ok", "samples": []}
    try:
        cls = _program_in_module(importlib.import_module(f"programs.{name}"))
        if cls is None:
            raise ValueError("module has no Program subclass")
        result["description"] = cls.DESCRIPTION
        random.seed(12345)
        program = cls()
        started = time.perf_counter()
        program.setup()
        result["setup_ms"] = round((time.perf_counter() - started) * 1000, 3)
        durations = []
        hashes = set()
        sample_ticks = {0, fps, min(5, seconds) * fps, seconds * fps}
        for tick in range(seconds * fps + 1):
            started = time.perf_counter()
            if tick:
                program.update(1 / fps, [])
            frame = program.render()
            durations.append((time.perf_counter() - started) * 1000)
            if not isinstance(frame, Frame) or len(frame.pixels) != 64 * 64 * 3:
                raise ValueError("render must produce a 64x64 RGB Frame")
            hashes.add(hashlib.sha256(frame.pixels).hexdigest())
            if tick in sample_ticks:
                filename = f"{name}-{fps}fps-{tick}.png"
                write_png(str(output / filename), frame, scale=1)
                lit = sum(any(frame.pixels[i:i + 3]) for i in range(0, len(frame.pixels), 3))
                result["samples"].append({"seconds": tick / fps, "image": filename, "lit_pixels": lit})
        ordered = sorted(durations)
        result.update(mean_ms=round(statistics.mean(durations), 3),
                      p95_ms=round(ordered[int(.95 * (len(ordered) - 1))], 3),
                      max_ms=round(max(durations), 3), unique_frames=len(hashes),
                      frames=len(durations))
    except Exception:
        result["status"] = "error"
        result["error"] = traceback.format_exc()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/pixoo-review"))
    parser.add_argument("--seconds", type=int, default=15)
    parser.add_argument("--fps", type=int, nargs="+", default=[30, 5])
    parser.add_argument("--program", action="append", help="limit to a named program; repeatable")
    args = parser.parse_args()
    if args.seconds < 1 or any(fps < 1 for fps in args.fps):
        parser.error("seconds and fps must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    names = args.program or [p.stem for p in sorted((root / "programs").glob("*.py")) if not p.stem.startswith("_")]
    results = []
    for name in names:
        for fps in args.fps:
            result = audit(name, fps, args.seconds, args.output)
            results.append(result)
            print(f"{name:18} {fps:2}fps {result['status']:5} p95={result.get('p95_ms', '-')}ms", flush=True)
            (args.output / "results.json").write_text(json.dumps({
                "python": platform.python_version(), "platform": platform.platform(),
                "seed": 12345, "note": "Offline synthetic dt; clock uses wall time; no device or terminal I/O in timings.",
                "results": results}, indent=2) + "\n")
    cards = []
    for result in results:
        samples = "".join(f'<figure><img src="{html.escape(s["image"])}"><figcaption>{s["seconds"]:g}s</figcaption></figure>' for s in result["samples"])
        error = f'<pre>{html.escape(result["error"])}</pre>' if "error" in result else ""
        cards.append(f'<article><h2>{html.escape(result["name"])} · {result["fps"]}fps</h2><p>{html.escape(result.get("description", ""))}</p><div>{samples}</div><p>{result["status"]} · p95 {result.get("p95_ms", "-")}ms</p>{error}</article>')
    (args.output / "index.html").write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Pixoo program review</title><style>body{font:16px system-ui;background:#141720;color:#eee;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(580px,1fr));gap:16px}article{background:#202532;padding:16px;border-radius:8px}h2{margin:0}article>div{display:flex;flex-wrap:wrap;gap:8px}figure{margin:0}img{width:128px;height:128px;image-rendering:pixelated}figcaption{color:#aab}pre{white-space:pre-wrap}</style><h1>Pixoo program review</h1><p>Seed 12345; elapsed time is simulated. Each tick calls update and render. No device connection. The clock uses actual wall time.</p><main>''' + "\n".join(cards) + "</main></html>\n")
    failures = sum(r["status"] != "ok" for r in results)
    print(f"{len(results)} runs, {failures} failures; gallery: {args.output / 'index.html'}")
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
