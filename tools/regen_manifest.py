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
    "docs/*.md",
    "examples/*.py",
    "examples/budget_lib/*.py",
    "examples/data/*.csv",
    "pyproject.toml",
    "uv.lock",
    "spec/*.md",
    "src/zuaef_agent/*.py",
    "src/zuaef_agent/gateway/*.py",
    "src/zuaef_agent/web/*.py",
    "tests/*.py",
    "tests/fixture_plugins/**/*.py",
    "tests/fixture_plugins/**/*.md",
    "tests/fixture_plugins/*.toml",
    "plugins/**/*.py",
    "plugins/*.toml",
    "plugins/**/*.csv",
    "plugins/**/*.md",
    "profiles/*.toml",
    "examples/profiles/*.toml",
    "tests/fixtures/synthetic_client_service/**/*.jsonl",
    "tests/fixtures/synthetic_client_service/**/*.yaml",
    "tests/fixtures/synthetic_client_service/**/*.yml",
    "tools/*.py",
    "workspace/knowledge/index.md",
    # Editorial-learning benchmark: authoritative source assets only. Generated
    # state (results/**, experiments/**/runs/**, judgments, metrics/REPORT) and
    # the sequential-v1 experiment machinery stay OUT of the manifest scope.
    "benchmarks/editorial-learning/README.md",
    "benchmarks/editorial-learning/benchmark.jsonl",
    "benchmarks/editorial-learning/curated/**",
    "benchmarks/editorial-learning/compiled/**",
    "benchmarks/editorial-learning/scripts/**",
    "benchmarks/editorial-learning/tasks/**",
    "benchmarks/editorial-learning/evidence/**",
    "benchmarks/editorial-learning/provenance/**",
]


def main() -> None:
    files: list[dict] = []
    for pattern in INCLUDE_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if not path.is_file():
                continue
            # Interpreter build artifacts (`__pycache__/*.pyc`) are runtime
            # state, not delivery source: their bytes drift with the Python
            # version/mtime, so locking them into the manifest makes the
            # integrity check environment-fragile. Never include them.
            if "__pycache__" in path.parts or path.suffix == ".pyc":
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
