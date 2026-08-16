"""Regenerate BUILD_MANIFEST.json for the current delivery tree.

Scope is the manifest-declared file set: source, tests, examples, spec, docs,
config. Runtime state (workspace artifacts, .zuaef-state, .state-proof, .venv)
never enters the manifest.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

INCLUDE_GLOBS = [
    ".agents/skills/**/*.md",
    ".env.example",
    ".gitignore",
    "*.md",
    "examples/*.py",
    "pyproject.toml",
    "uv.lock",
    "spec/*.md",
    "src/zuaef_agent/*.py",
    "tests/*.py",
    "tests/fixture_plugins/**/*.py",
    "tests/fixture_plugins/**/*.md",
    "tests/fixture_plugins/*.toml",
    "tools/*.py",
    "workspace/knowledge/index.md",
]


def main() -> None:
    files: list[dict] = []
    for pattern in INCLUDE_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if not path.is_file():
                continue
            data = path.read_bytes()
            files.append(
                {
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    seen = set()
    unique = []
    for entry in files:
        if entry["path"] not in seen:
            seen.add(entry["path"])
            unique.append(entry)
    manifest = {
        "artifact": "zuaef-agent-core-refactor-v1.1",
        "version": "0.1.1",
        "validation": {
            "pytest": "see latest run",
            "gate": "spec/capability-proof-gate.md",
        },
        "files": unique,
    }
    target = REPO_ROOT / "BUILD_MANIFEST.json"
    target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {target} with {len(unique)} files")


if __name__ == "__main__":
    main()
