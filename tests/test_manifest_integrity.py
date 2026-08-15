"""Package integrity: the delivery tree must match BUILD_MANIFEST.json exactly.

Validation scope is the manifest-declared file set (per the frozen SPEC, never a
full tree walk — runtime state like .state-proof/** must not trip integrity).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]


def _manifest() -> dict:
    return json.loads((REPO_ROOT / "BUILD_MANIFEST.json").read_text(encoding="utf-8"))


def test_manifest_paths_exist_with_matching_bytes_and_hash():
    manifest = _manifest()
    assert manifest["files"], "manifest must not be empty"
    for entry in manifest["files"]:
        path = REPO_ROOT / entry["path"]
        assert path.is_file(), f"manifest file missing: {entry['path']}"
        data = path.read_bytes()
        assert len(data) == entry["bytes"], f"size drift: {entry['path']}"
        assert hashlib.sha256(data).hexdigest() == entry["sha256"], f"hash drift: {entry['path']}"


def test_manifest_covers_all_committed_source_and_tests():
    """No unlisted runtime-required file: source, tests, examples, spec."""
    tracked = sorted(
        str(p.relative_to(REPO_ROOT))
        for p in (REPO_ROOT / "src").rglob("*.py")
    ) + sorted(
        str(p.relative_to(REPO_ROOT))
        for p in (REPO_ROOT / "tests").rglob("*.py")
    )
    listed = {entry["path"] for entry in _manifest()["files"]}
    missing = [p for p in tracked if p not in listed]
    assert not missing, f"files missing from manifest: {missing}"


def test_manifest_entries_are_relative_and_contained():
    for entry in _manifest()["files"]:
        rel = Path(entry["path"])
        assert not rel.is_absolute()
        assert ".." not in rel.parts
