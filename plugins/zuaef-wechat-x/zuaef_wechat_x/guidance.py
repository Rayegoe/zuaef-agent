"""Plugin-shipped writing guides.

Each guide ships inside the plugin package and is returned by the
``read_guidance`` tool — bundled files are not auto-loaded by the Skills
capability, so this tool is the only model-reachable path to them. A missing
file is a packaging bug and fails loudly.
"""

from __future__ import annotations

from pathlib import Path

_GUIDANCE_DIR = Path(__file__).resolve().parent / "guidance"

GUIDANCE_FILES: dict[str, str] = {
    "wechat-template": "wechat-template.md",
    "x-thread-template": "x-thread-template.md",
    "image-guidelines": "image-guidelines.md",
}


def load_guidance(kind: str) -> str:
    filename = GUIDANCE_FILES.get(kind)
    if filename is None:
        raise KeyError(kind)
    path = _GUIDANCE_DIR / filename
    if not path.is_file():
        raise RuntimeError(f"zuaef-wechat-x guidance file missing: {path}")
    return path.read_text(encoding="utf-8").strip()
