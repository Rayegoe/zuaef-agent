"""Capability guidance loader.

Each format's guidance file ships inside the plugin package and is injected
as capability instructions — the model reads it only when it loads the
capability (deferred loading), never before. A missing file is a packaging
bug and fails composition at factory time.
"""

from __future__ import annotations

from pathlib import Path

_GUIDANCE_DIR = Path(__file__).resolve().parent / "guidance"


def load_guidance(name: str) -> str:
    path = _GUIDANCE_DIR / name
    if not path.is_file():
        raise RuntimeError(f"zuaef-artifacts guidance file missing: {path}")
    return path.read_text(encoding="utf-8").strip()
