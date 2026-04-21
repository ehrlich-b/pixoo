"""Persistent device-selection state, kept at project root as .pixoo-state.json."""
from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent.parent / ".pixoo-state.json"


def save(d: dict) -> None:
    STATE_FILE.write_text(json.dumps(d, indent=2))


def load() -> dict | None:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None


def set_primed(v: bool) -> None:
    s = load() or {}
    s["primed"] = v
    save(s)
