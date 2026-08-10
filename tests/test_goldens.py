"""Deterministic frame-renderer goldens for built-in animations.

Each golden records the SHA-256 of the exact 64x64x3 RGB buffer the program's
render() produces after each update() tick. The expected hashes below are
computed ONCE and hard-coded. If an intentional change alters any output,
regenerate the whole table with the exact command:

    PIXOO_REGEN_GOLDENS=1 python3 -m unittest tests.test_goldens -v

(or the `make regen-goldens` alias). This rewrites the GOLDENS table in this
file in place, then run the suite again (without the env var) to confirm the
new output is stable.

The block comment markers below must stay byte-identical to _MARK_START /
_MARK_END: _rewrite_table() replaces the FIRST marker-to-marker span
(count=1), and the table comment is the first occurrence in the file (it sits
above the string-literal definitions). If you reorder the file, re-verify.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import unittest
from pathlib import Path

from pixoolib.frame import Frame
from programs.hilbert import Hilbert
from programs.langton import Langton
from programs.sandpile import Sandpile

REGEN = os.environ.get("PIXOO_REGEN_GOLDENS") == "1"

# name -> Program class; params are passed as --arg KEY=VALUE strings
_PROGS = {
    "langton": Langton,
    "sandpile": Sandpile,
    "hilbert": Hilbert,
}

# <<< PIXOO GOLDEN TABLE START >>>
# Regen: PIXOO_REGEN_GOLDENS=1 python3 -m unittest tests.test_goldens -v
GOLDENS = {
    "hilbert": {
        "frames": [
            "5ed908168ec63647cdcf210a3c2a48c59cdf87278c6c8092fad9da3d88edcf86",
            "22648a6d1b3197351b6a39e3e4277e290f051e0782d5cd191a9704a96c413e16",
            "8363c83ef4e7dc7326539743b5b8b1fbfa442d1919da0845594c041f80aeb4ca",
            "c16a9d96868f5c7b3ebd0db87b19eab806040e9941966a9d5099f0abf2d695b3",
            "f39dc593f8745038ddc96f4dcf82241d7ca654eb08a2041f92a11302dd5d2900",
            "93b7111f29956f6d39041e9b0ff9f793d91349fae2de0fd1bb06d49ffbb2c7a7"
        ],
        "n": 6,
        "params": {
            "grow_per_frame": "73",
            "seed": "123",
            "steps": "511"
        }
    },
    "langton": {
        "frames": [
            "bc646b072fc3d039c659091e3e11ef73ee42671c1d5b2263726e84bbbd9a6f75",
            "b127085960622cd65c31797d1c9b7a5d074a5251e9bbb72b8ca1fc10ba8f0bb9",
            "cc396d6bdb3626ba514c074c1655c87ad504995484e5ad6fc3c10d9098c3a00b",
            "412e960b8670f9061d97e3e1f852c13a052e9311e39f723a06dd467da8841cb5",
            "4d87c2777c448e91a63364ea0088f62b46a2f48f8efaedeac5ce1e6175ae6da6",
            "ec157ffb447a034344994c74e8a6dcfa4a31f1f140b251a5e69ad5ff2091ec4d"
        ],
        "n": 6,
        "params": {
            "seed": "5",
            "steps": "997",
            "steps_per_frame": "137"
        }
    },
    "sandpile": {
        "frames": [
            "1919ebb284a5795d8b138b792bf5840b1fa4072b1ca2fb448d51ed93171e7253",
            "8fa64ecf3d41e43ff1f6c8d673ba24584ca2708f6c00e6c3bae6fc458df5a9fe",
            "29d32f5045ff90d869d8508e79e404ea0869351a02cedb184dab8a87ee7c2eac",
            "854a3fecb1f60716da742022300b054e6ab616ea962a3fd5e0d064c4fe48ff90",
            "3dc29f414da9a6eccc9b39686af1aba8dfe156f9764b255f81274a52f131f8f8",
            "e0f5d3c4fc8987f207ce39d2d3e16c33f495de785a0f93bba85506701737cd44"
        ],
        "n": 6,
        "params": {
            "drops_per_frame": "37",
            "seed": "7",
            "steps": "222"
        }
    }
}
# <<< PIXOO GOLDEN TABLE END >>>


def _sha256(frame: Frame) -> str:
    return hashlib.sha256(bytes(frame.pixels)).hexdigest()


def _render(name: str, n: int) -> list[str]:
    spec = GOLDENS[name]
    prog = _PROGS[name](**spec["params"])
    prog.setup()
    out = []
    for _ in range(n):
        prog.update(1.0, [])
        out.append(_sha256(prog.render()))
    return out


_MARK_START = "# <<< PIXOO GOLDEN TABLE START >>>"
_MARK_END = "# <<< PIXOO GOLDEN TABLE END >>>"


def _rewrite_table() -> None:
    """Rewrite the GOLDENS literal in this file so regen is one command away."""
    path = Path(__file__)
    src = path.read_text()
    block = (
        _MARK_START + "\n"
        + "# Regen: PIXOO_REGEN_GOLDENS=1 python3 -m unittest tests.test_goldens -v\n"
        + "GOLDENS = " + json.dumps(GOLDENS, indent=4, sort_keys=True) + "\n"
        + _MARK_END
    )
    pattern = re.compile(re.escape(_MARK_START) + r".*?" + re.escape(_MARK_END), re.S)
    new_src, n = pattern.subn(block, src, count=1)
    if n != 1:
        raise RuntimeError("golden table markers not found exactly once in test file")
    path.write_text(new_src)


class TestFrameGoldens(unittest.TestCase):
    def _check(self, name: str) -> None:
        spec = GOLDENS[name]
        got = _render(name, spec["n"])
        if REGEN:
            spec["frames"] = got
            _rewrite_table()
            return
        expected = spec["frames"]
        self.assertGreater(len(expected), 0, f"{name} golden table is empty — regenerate")
        self.assertEqual(len(got), len(expected), f"{name} frame count mismatch")
        for i, (g, e) in enumerate(zip(got, expected)):
            self.assertEqual(
                g, e,
                f"{name} frame {i} hash mismatch:\n  got {g}\n  exp {e}",
            )

    def test_langton(self) -> None:
        self._check("langton")

    def test_sandpile(self) -> None:
        self._check("sandpile")

    def test_hilbert(self) -> None:
        self._check("hilbert")


if __name__ == "__main__":
    unittest.main()
