"""Privacy gate (SPEC v0.1 §45 Gate G): the public repo never carries real
customer data.

The private Business Judgment Corpus lives outside this repo, at a
config-provided slice_root (~/.local/share/zuaef/client-service). This gate
asserts the tracked public tree contains no real evidence ledger, customer
state, or interaction receipt outside the synthetic fixture namespace
(tests/fixtures/synthetic_client_service/), and no PII markers.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = "fixtures/synthetic_client_service"

# 11-digit mainland mobile number — the clearest customer PII signal this
# gate must catch. Source-path detection is handled by
# test_private_corpus_files_only_in_synthetic_namespace; fictionality of the
# synthetic fixture by test_synthetic_evidence_is_fictional.
_PHONE = re.compile(r"1[3-9]\d{9}")


def _tracked() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=True,
    )
    return out.stdout.splitlines()


def test_private_corpus_files_only_in_synthetic_namespace() -> None:
    tracked = _tracked()
    for path in tracked:
        name = Path(path).name
        if name in ("evidence_ledger.jsonl",):
            assert SYNTHETIC in path, f"real evidence ledger leaked: {path}"

    for path in tracked:
        if "state/customers" in path and SYNTHETIC not in path:
            raise AssertionError(f"customer state outside synthetic namespace: {path}")
        if "/interactions/" in path and SYNTHETIC not in path:
            raise AssertionError(f"interaction receipt outside synthetic namespace: {path}")


def test_synthetic_evidence_is_fictional() -> None:
    ledger = REPO_ROOT / "tests" / "fixtures" / "synthetic_client_service" / "evidence" / "evidence_ledger.jsonl"
    for line in ledger.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        assert record["evidence_id"].startswith("EVD-SYN-"), record["evidence_id"]
        assert record["source_type"] == "synthetic", record["evidence_id"]


# Paths this feature owns in the public repo; BUILD_MANIFEST.json and other
# repo-wide listings are excluded — they are path/hash artifacts, not PII
# surfaces, and would otherwise make the gate regex noisy. We scan disk
# files (not git ls-files) so untracked new sources are still gated.
_OWNED_RELPATHS = (
    "plugins/zuaef-client-service",
    "examples/client_service_case.py",
    "examples/profiles/client-service-beauty.toml",
    "tests/fixtures/synthetic_client_service",
)


def _owned_disk_files() -> list[Path]:
    files: list[Path] = []
    for rel in _OWNED_RELPATHS:
        path = REPO_ROOT / rel
        if path.is_dir():
            files.extend(p for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            files.append(path)
    files.extend(
        p for p in (REPO_ROOT / "tests").glob("test_client_service_*.py") if p.is_file()
    )
    return files


def test_no_pii_in_owned_source_surface() -> None:
    scanned = 0
    for path in _owned_disk_files():
        if not path.suffix in (".py", ".yaml", ".toml", ".json", ".jsonl", ".md"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        scanned += 1
        if _PHONE.search(text):
            raise AssertionError(f"possible PII in public file: {path.relative_to(REPO_ROOT)}")
    assert scanned > 0, "privacy scan found no owned source files"
