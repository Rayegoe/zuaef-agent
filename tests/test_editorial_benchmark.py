"""Editorial-learning benchmark layer contract tests.

Pins the repository policy set by the operator (2026-08-17):
- committed tasks carry bounded excerpts + FULL-text sha256 + provenance;
- the evidence pool loads through the real EditorialEvidenceStore;
- seed snapshot matches the capability's builtin seeds;
- promote_patch enforces strict T01->T20 sequential promotion;
- results/ starts empty (no fabricated runs).

These tests run against the committed artifacts; data/raw is only needed to
REGENERATE them (build_tasks.py), not to verify what is committed.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
BENCH = REPO / "benchmarks" / "editorial-learning"
sys.path[:0] = [
    str(REPO / "plugins" / "zuaef-ace-writing"),
    str(REPO / "src"),
]
from editorial_capability import (
    COGNITIVE_ACTIONS,
    EditorialEvidenceStore,
    seed_evidence,
)

VALID_SENSORS = {
    "template_connectors", "summary_pressure", "uniform_paragraphs",
    "low_concrete_anchor_density", "abstract_noun_density",
}


def _tasks() -> list[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((BENCH / "tasks").glob("T*.json"))
    ]


class TestCommittedTasks:
    def test_twenty_tasks_present(self):
        tasks = _tasks()
        assert [t["task_id"] for t in tasks] == [f"T{i:02d}" for i in range(1, 21)]

    def test_excerpts_bounded_and_full_hashes_present(self):
        for t in _tasks():
            assert len(t["before"]["excerpt"]) <= 1500, t["task_id"]
            assert len(t["after"]["excerpt"]) <= 1500, t["task_id"]
            assert len(t["before"]["sha256"]) == 64
            assert len(t["after"]["sha256"]) == 64

    def test_provenance_complete_per_task(self):
        for t in _tasks():
            prov = t["provenance"]
            assert prov["record_id"] and prov["license"] and prov["selection_rule"]
            assert prov["dataset"] in (
                "IteraTeR (human_doc_level)",
                "TETRA (professional edits of ACL papers)",
                "WritingPreferenceBench (Chinese)",
                "Re3-Sci",
            )

    def test_sources_match_allocation(self):
        by_seq = {t["sequence"]: t["source"] for t in _tasks()}
        assert all(by_seq[i] == "iterater" for i in range(1, 7))
        assert all(by_seq[i] == "tetra" for i in range(7, 11))
        assert all(by_seq[i] == "wpb" for i in range(11, 17))
        assert all(by_seq[i] == "re3" for i in range(17, 21))

    def test_no_full_text_committed(self):
        """Excerpt + sha256 but no complete document fields in committed JSON."""
        for t in _tasks():
            assert "text" not in t["before"] and "text" not in t["after"]

    def test_t10_is_no_intervention_negative(self):
        t10 = _tasks()[9]
        assert t10["delta"]["intent"] == "none_expected"
        assert t10["learning"]["evidence_ids"] == []


class TestEvidencePool:
    def test_human_patches_load_through_real_store(self):
        store = EditorialEvidenceStore(BENCH / "evidence" / "human_patches.jsonl")
        human = [e for e in store._entries if e.source_type == "human_patch"]
        assert len(human) == len(store._entries) - 6  # exactly seeds + patches
        assert all(e.action in COGNITIVE_ACTIONS for e in human)
        triggers = {s for e in human for s in e.trigger_signals}
        assert triggers <= VALID_SENSORS

    def test_human_patches_outrank_seeds_in_retrieval(self):
        store = EditorialEvidenceStore(BENCH / "evidence" / "human_patches.jsonl")
        top = store.retrieve(signals={"abstract_noun_density": 1.0}, tags=["drafting"], limit=1)
        assert top[0].source_type == "human_patch"

    def test_seed_snapshot_matches_capability(self):
        snap = [
            json.loads(line)
            for line in (BENCH / "evidence" / "seed_snapshot.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        live = [json.loads(s.model_dump_json()) for s in seed_evidence()]
        assert snap == live

    def test_human_patch_ids_unique(self):
        ids = [
            json.loads(line)["id"]
            for line in (BENCH / "evidence" / "human_patches.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(ids) == len(set(ids))


class TestProvenance:
    def test_sources_ledger_complete(self):
        entries = [
            json.loads(line)
            for line in (BENCH / "provenance" / "sources.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(entries) == 4
        for e in entries:
            assert e["url"] and e["license"] and e["license_note"]
            assert e["license"] != "unknown"

    def test_benchmark_index_matches_tasks(self):
        index = [
            json.loads(line)
            for line in (BENCH / "benchmark.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(index) == 20
        by_id = {t["task_id"]: t for t in _tasks()}
        for row in index:
            assert row["evidence_ids"] == by_id[row["task_id"]]["learning"]["evidence_ids"]


class TestPromoteSequence:
    def test_out_of_order_rejected_and_sequential_promotes(self, tmp_path):
        ev = tmp_path / "evidence.jsonl"
        script = BENCH / "scripts" / "promote_patch.py"
        run = lambda *a: subprocess.run(
            [sys.executable, str(script), *a], capture_output=True, text=True, check=False
        )
        assert run("--init", "--out", str(ev)).returncode == 0
        # T03 before T01: refused
        out = run("--task", "T03", "--out", str(ev))
        assert out.returncode != 0 and "sequence violation" in out.stderr
        # T01 then T05 (T02-T04 have no patches): allowed
        assert run("--task", "T01", "--out", str(ev)).returncode == 0
        assert run("--task", "T05", "--out", str(ev)).returncode == 0
        # idempotent
        again = run("--task", "T01", "--out", str(ev))
        assert again.returncode == 0 and "nothing to promote" in again.stdout
        # file still valid for the capability
        store = EditorialEvidenceStore(ev)
        assert sum(1 for e in store._entries if e.source_type == "human_patch") == 12

    def test_results_start_empty(self):
        for mode in ("base", "static", "adaptive"):
            runs = list((BENCH / "results" / mode).glob("T*_run.json"))
            assert runs == [], f"fabricated results in {mode}: {runs}"


class TestRebuild:
    """Committed sha256 fields must match a fresh deterministic rebuild.

    Skipped automatically when data/raw is absent (CI without datasets);
    locally it pins tasks/ to the raw evidence.
    """

    def test_committed_hashes_match_rebuild(self):
        derived = REPO / "data" / "derived" / "tasks_full"
        if not derived.is_dir():
            pytest.skip("data/derived absent — run fetch_sources.py + build_tasks.py")
        for committed in _tasks():
            full = json.loads((derived / f"{committed['task_id']}.json").read_text(encoding="utf-8"))
            for field, text in (
                ("before", full["before"]),
                ("after", full["after"]),
            ):
                expect = hashlib.sha256(text.encode("utf-8")).hexdigest()
                assert committed[field]["sha256"] == expect, committed["task_id"]
