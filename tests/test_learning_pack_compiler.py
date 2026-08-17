"""Pack Compiler contract tests (SPEC: writing-intelligence-compilation).

Covers the 30 required scenarios from the spec's "Required Tests" section:
minimal-fixture happy paths (with and without benchmark), every validation
failure mode, legacy cross-check mismatches, benchmark join failures,
determinism, capability-level evidence loadability, output hygiene, and
transactional target preservation. The final class checks the REAL compiled
snapshot committed under benchmarks/editorial-learning/compiled/ (and, when
the external pack is present on this host, recompiles it for a byte-identical
diff — a documented conditional, not an unconditional skip).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Set as AbstractSet
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
BENCH = REPO / "benchmarks" / "editorial-learning"
COMPILER = BENCH / "scripts" / "compile_learning_pack.py"
sys.path[:0] = [
    str(REPO / "plugins" / "zuaef-ace-writing"),
    str(REPO / "src"),
]
# sys.path bootstrapping is required because the ACE plugin is an editable
# install; pyright cannot resolve it without the venv, hence the ignore.
from zuaef_ace_writing.editorial import (  # pyright: ignore[reportMissingImports]
    EditorialEvidenceStore,
)

REAL_PACK = Path("/home/barry/下载/zuaef-writing-learning-pack-v0.1/zuaef-writing-learning-pack")
ACTIONS = [
    "return_to_observation", "delay_interpretation", "shift_perspective",
    "retrieve_concrete_memory", "break_trajectory",
]


def run_compiler(pack, sources, techniques, out, benchmark=None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(COMPILER), "--pack", str(pack),
           "--curated-sources", str(sources), "--curated-techniques", str(techniques),
           "--out", str(out)]
    if benchmark is not None:
        cmd += ["--benchmark", str(benchmark)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


# --- fixture factory -----------------------------------------------------------

FIXTURE_SOURCES = {
    "sanlian-a": ("sanlian/01-note.md", "raw/sanlian-a.md", "https://example.com/a"),
    "sanlian-b": ("sanlian/02-note.md", "raw/sanlian-b.md", "https://example.com/b"),
    "iterater": ("research/01-it.md", "raw/iterater.md", "https://example.com/it"),
    "tetra": ("research/02-te.md", "raw/tetra.md", "https://example.com/te"),
    "wpb": ("research/03-wp.md", "raw/wpb.md", "https://example.com/wp"),
    "re3": ("research/04-re.md", "raw/re3.md", "https://example.com/re"),
}


def write_fixture_pack(root: Path, *, extra_sources: dict | None = None,
                       legacy_url_override: str | None = None,
                       legacy_tech_override: dict | None = None,
                       raw_missing: AbstractSet[str] = frozenset()) -> Path:
    pack = root / "pack"
    for sid, (curated, raw, _url) in FIXTURE_SOURCES.items():
        target = pack / curated
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# curated note for {sid}\ncontent line\n", encoding="utf-8")
        raw_target = pack / raw
        raw_target.parent.mkdir(parents=True, exist_ok=True)
        if sid in raw_missing:
            # honor raw_missing even when a previous fixture write already
            # created this raw file (pytest tmp_path is reused across writes)
            raw_target.unlink(missing_ok=True)
        else:
            raw_target.write_text(f"raw snapshot {sid}\nline2\n", encoding="utf-8")
    sources = {
        sid: url for sid, (_c, _r, url) in FIXTURE_SOURCES.items()
    }
    for sid, url in (extra_sources or {}).items():
        note = pack / f"sanlian/{sid}.md"
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(f"# {sid}\n", encoding="utf-8")
        rawf = pack / f"raw/{sid}.md"
        rawf.parent.mkdir(parents=True, exist_ok=True)
        rawf.write_text(f"raw {sid}\n", encoding="utf-8")
        sources[sid] = url
    if legacy_url_override:
        sources[legacy_url_override] = "https://example.com/MISMATCHED"
    (pack / "data").mkdir(parents=True, exist_ok=True)
    with (pack / "data" / "sources.jsonl").open("w", encoding="utf-8") as fh:
        for sid, url in sources.items():
            fh.write(json.dumps({"id": sid, "url": url}) + "\n")
    legacy_techs = []
    for i in range(1, 21):
        tid = f"T{i:03d}"
        rec = technique_fixture(i)
        legacy_techs.append({
            "id": tid, "name": rec["name"],
            "source": list(rec["sources"]), "maps_to": rec["action"],
        })
    if legacy_tech_override:
        for rec in legacy_techs:
            if rec["id"] == legacy_tech_override["id"]:
                rec.update(legacy_tech_override)
    with (pack / "data" / "techniques.jsonl").open("w", encoding="utf-8") as fh:
        for rec in legacy_techs:
            fh.write(json.dumps(rec) + "\n")
    return pack


def technique_fixture(i: int) -> dict:
    tid = f"T{i:03d}"
    benchmark_sources = ["iterater", "tetra", "wpb", "re3"]
    source = benchmark_sources[i % 4]
    if i in (1, 2):
        sources = ["sanlian-a", source]
        primary = "sanlian-a"
    elif i == 3:
        sources = ["sanlian-b"]
        primary = "sanlian-b"
    else:
        sources = [source]
        primary = source
    action = ACTIONS[i % 5]
    if i % 3 == 0:
        mode, triggers, contexts = "context", [], ["ctx_available"]
    elif i % 3 == 1:
        mode, triggers, contexts = "sensor", ["summary_pressure" if i % 2 else "template_connectors"], []
    else:
        mode, triggers, contexts = "hybrid", ["abstract_noun_density"], ["material_observed"]
    return {
        "id": tid, "name": f"fixture_move_{i}", "condition": ["cond-a", "cond-b"],
        "action": action, "instruction": f"instruction for {tid}",
        "preserve": ["claims"], "anti_pattern": ["drift"], "domain": ["nonfiction"],
        "sources": sources, "primary_source": primary,
        "confidence": {"level": "medium", "basis": ["curated_methodology"]},
        "activation": {"mode": mode, "trigger_signals": triggers,
                       "context_signals": contexts, "situation_tags": ["drafting"]},
        "rationale": f"rationale {tid}",
    }


def write_curated(root: Path, pack: Path, *, techniques=None, sources=None,
                  mutate_techniques=None, mutate_sources=None) -> tuple[Path, Path]:
    curated_dir = root / "curated"
    curated_dir.mkdir(parents=True, exist_ok=True)
    source_records = sources if sources is not None else [
        {"id": sid, "source_type": "copyrighted-study-note" if sid.startswith("sanlian") else "research-paper",
         "url": url, "curated_path": FIXTURE_SOURCES[sid][0], "raw_path": FIXTURE_SOURCES[sid][1],
         "raw_required": True}
        for sid, url in ((s, FIXTURE_SOURCES[s][2]) for s in FIXTURE_SOURCES)
    ]
    if mutate_sources:
        source_records = mutate_sources(source_records)
    sp = curated_dir / "sources.jsonl"
    with sp.open("w", encoding="utf-8") as fh:
        for rec in source_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tech_records = techniques if techniques is not None else [
        technique_fixture(i) for i in range(1, 21)
    ]
    if mutate_techniques:
        tech_records = mutate_techniques(tech_records)
    tp = curated_dir / "techniques.jsonl"
    with tp.open("w", encoding="utf-8") as fh:
        for rec in tech_records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return sp, tp


def write_benchmark(root: Path, *, rows=None) -> Path:
    rows = rows or [
        {"task_id": f"T{i:02d}", "sequence": i, "source": ["iterater", "tetra", "wpb", "re3"][i % 4]}
        for i in range(1, 21)
    ]
    root.mkdir(parents=True, exist_ok=True)
    path = root / "benchmark.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for rec in rows:
            fh.write(json.dumps(rec) + "\n")
    return path


@pytest.fixture()
def fixture(tmp_path: Path):
    pack = write_fixture_pack(tmp_path)
    sp, tp = write_curated(tmp_path, pack)
    bench = write_benchmark(tmp_path)
    return tmp_path, pack, sp, tp, bench


# --- 1-2: happy paths ------------------------------------------------------------


class TestHappyPaths:
    def test_happy_path_with_benchmark(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        out = tmp_path / "compiled"
        result = run_compiler(pack, sp, tp, out, benchmark=bench)
        assert result.returncode == 0, result.stderr
        names = {p.name for p in out.iterdir()}
        assert names == {"sources.jsonl", "techniques.jsonl", "evidence.jsonl",
                         "sequential_inputs.jsonl", "manifest.json"}
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["counts"] == {"sources": 6, "techniques": 20, "evidence": 20,
                                      "sequential_inputs": 20}
        assert manifest["benchmark_provided"] is True

    def test_pack_only(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        out = tmp_path / "compiled"
        result = run_compiler(pack, sp, tp, out)
        assert result.returncode == 0, result.stderr
        assert not (out / "sequential_inputs.jsonl").exists()
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["benchmark_provided"] is False
        assert manifest["counts"]["sequential_inputs"] == 0
        assert manifest["inputs"]["benchmark_sha256"] is None

    def test_optional_raw_missing_normalized_to_null(self, tmp_path):
        pack = write_fixture_pack(tmp_path, raw_missing={"sanlian-a"})
        sp, tp = write_curated(
            tmp_path, pack,
            mutate_sources=lambda recs: [
                {**r, "raw_required": False} if r["id"] == "sanlian-a" else r for r in recs
            ],
        )
        out = tmp_path / "compiled"
        result = run_compiler(pack, sp, tp, out)
        assert result.returncode == 0, result.stderr
        sources = [json.loads(line) for line in (out / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
        a = next(s for s in sources if s["id"] == "sanlian-a")
        assert a["raw_path"] is None and a["raw_sha256"] is None and a["raw_locator"] is None
        b = next(s for s in sources if s["id"] == "sanlian-b")
        assert b["raw_sha256"]


# --- 3-15: curated validation failures ----------------------------------------------


def _assert_fail(result, needle=""):
    assert result.returncode != 0, f"expected failure, got success: {result.stdout}"
    assert "COMPILE FAILED" in result.stderr
    if needle:
        assert needle in result.stderr


class TestValidationFailures:
    def test_missing_curated_source_file(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v1", pack,
            mutate_sources=lambda recs: [
                {**r, "curated_path": "sanlian/absent.md"} if r["id"] == "sanlian-a" else r
                for r in recs
            ],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "curated file missing")

    def test_required_raw_missing(self, tmp_path):
        pack = write_fixture_pack(tmp_path, raw_missing={"iterater"})
        sp, tp = write_curated(tmp_path, pack)
        _assert_fail(run_compiler(pack, sp, tp, tmp_path / "out"), "required raw file missing")

    def test_malformed_curated_sources_jsonl(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        bad = tmp_path / "bad_sources.jsonl"
        bad.write_text('{"id": "x"\n', encoding="utf-8")
        _assert_fail(run_compiler(pack, bad, tp, tmp_path / "out"), ":1: malformed JSON")

    def test_malformed_curated_techniques_jsonl(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        bad = tmp_path / "bad_tech.jsonl"
        bad.write_text("not-json\n", encoding="utf-8")
        _assert_fail(run_compiler(pack, sp, bad, tmp_path / "out"), ":1: malformed JSON")

    def test_duplicate_source_id(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v2", pack,
            mutate_sources=lambda recs: [*recs, dict(recs[0])],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "duplicate source id")

    def test_duplicate_technique_id(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v3", pack,
            mutate_techniques=lambda recs: [*recs, dict(recs[0])],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "duplicate technique id")

    def test_missing_t020(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v4", pack,
            mutate_techniques=lambda recs: recs[:-1],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "missing technique id")

    def test_invalid_action(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v5", pack,
            mutate_techniques=lambda recs: [
                {**r, "action": "rewrite_everything"} if r["id"] == "T001" else r for r in recs
            ],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "not in frozen five")

    def test_invalid_trigger_signal(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v6", pack,
            mutate_techniques=lambda recs: [
                {**r, "activation": {**r["activation"], "trigger_signals": ["vibe_check"]}}
                if r["id"] == "T002" else r for r in recs
            ],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "not in frozen five sensors")

    def test_invalid_activation_combination(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v7", pack,
            mutate_techniques=lambda recs: [
                {**r, "activation": {**r["activation"], "trigger_signals": ["summary_pressure"]}}
                if r["id"] == "T003" else r for r in recs  # T003 fixture is context mode
            ],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "mode=context requires empty")

    def test_unknown_technique_source_id(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v8", pack,
            mutate_techniques=lambda recs: [
                {**r, "sources": ["ghost-source"]} if r["id"] == "T001" else r for r in recs
            ],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "unknown source")

    def test_primary_source_not_in_sources(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        sp2, tp2 = write_curated(
            tmp_path / "v9", pack,
            mutate_techniques=lambda recs: [
                {**r, "primary_source": "sanlian-b"} if r["id"] == "T005" else r for r in recs
            ],
        )
        _assert_fail(run_compiler(pack, sp2, tp2, tmp_path / "out"), "primary_source")


# --- 16-19: legacy cross-check failures -----------------------------------------------


class TestLegacyMismatch:
    def test_legacy_source_url_mismatch(self, fixture, tmp_path):
        pack = write_fixture_pack(tmp_path, legacy_url_override="tetra")
        sp, tp = write_curated(tmp_path, pack)
        _assert_fail(run_compiler(pack, sp, tp, tmp_path / "out"), "legacy url mismatch")

    def test_legacy_name_mismatch(self, fixture, tmp_path):
        pack = write_fixture_pack(
            tmp_path, legacy_tech_override={"id": "T001", "name": "wrong_name"}
        )
        sp, tp = write_curated(tmp_path, pack)
        _assert_fail(run_compiler(pack, sp, tp, tmp_path / "out"), "legacy name mismatch")

    def test_legacy_source_mismatch(self, fixture, tmp_path):
        pack = write_fixture_pack(
            tmp_path, legacy_tech_override={"id": "T001", "source": ["re3"]}
        )
        sp, tp = write_curated(tmp_path, pack)
        _assert_fail(run_compiler(pack, sp, tp, tmp_path / "out"), "legacy source mismatch")

    def test_legacy_maps_to_mismatch(self, fixture, tmp_path):
        pack = write_fixture_pack(
            tmp_path, legacy_tech_override={"id": "T001", "maps_to": "break_trajectory"}
        )
        sp, tp = write_curated(tmp_path, pack)
        _assert_fail(run_compiler(pack, sp, tp, tmp_path / "out"), "maps_to mismatch")


# --- 20-23: benchmark join failures ------------------------------------------------------


class TestBenchmarkJoin:
    def test_bad_source_join(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        rows = [json.loads(line) for line in bench.read_text(encoding="utf-8").splitlines()]
        rows[0]["source"] = "nonexistent-source"
        bad = write_benchmark(tmp_path / "b1", rows=rows)
        _assert_fail(run_compiler(pack, sp, tp, tmp_path / "out", benchmark=bad),
                     "no exact match")

    def test_sequence_gap(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        rows = [json.loads(line) for line in bench.read_text(encoding="utf-8").splitlines()]
        rows[5]["sequence"] = 21
        bad = write_benchmark(tmp_path / "b2", rows=rows)
        _assert_fail(run_compiler(pack, sp, tp, tmp_path / "out", benchmark=bad),
                     "sequence must be strictly 1..20")

    def test_task_id_duplicate(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        rows = [json.loads(line) for line in bench.read_text(encoding="utf-8").splitlines()]
        rows[7]["task_id"] = rows[6]["task_id"]
        bad = write_benchmark(tmp_path / "b3", rows=rows)
        _assert_fail(run_compiler(pack, sp, tp, tmp_path / "out", benchmark=bad),
                     "task_id must be exactly T01..T20")

    def test_source_with_zero_candidates(self, fixture, tmp_path):
        pack = write_fixture_pack(tmp_path, extra_sources={"empty-src": "https://example.com/empty"})
        sp, tp = write_curated(tmp_path, pack)
        # curated layer must also declare the extra source or source-set check fails first
        sp2, _ = write_curated(
            tmp_path / "v10", pack,
            mutate_sources=lambda recs: [*recs, {
                "id": "empty-src", "source_type": "research-paper",
                "url": "https://example.com/empty",
                "curated_path": "sanlian/empty-src.md", "raw_path": "raw/empty-src.md",
                "raw_required": True,
            }],
        )
        bench = write_benchmark(tmp_path / "b4", rows=[
            {"task_id": f"T{i:02d}", "sequence": i,
             "source": "empty-src" if i == 1 else ["iterater", "tetra", "wpb", "re3"][i % 4]}
            for i in range(1, 21)
        ])
        _assert_fail(run_compiler(pack, sp2, tp, tmp_path / "out", benchmark=bench),
                     "no candidate techniques")


# --- 24-28: determinism & output hygiene ---------------------------------------------------


class TestDeterminismAndHygiene:
    def test_deterministic_bytes_across_two_runs(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        out1, out2 = tmp_path / "a", tmp_path / "b"
        assert run_compiler(pack, sp, tp, out1, benchmark=bench).returncode == 0
        assert run_compiler(pack, sp, tp, out2, benchmark=bench).returncode == 0
        for name in out1.iterdir():
            assert name.read_bytes() == (out2 / name.name).read_bytes(), name.name

    def test_evidence_loads_through_real_store(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        out = tmp_path / "compiled"
        assert run_compiler(pack, sp, tp, out, benchmark=bench).returncode == 0
        store = EditorialEvidenceStore(out / "evidence.jsonl")
        corpus = [e for e in store._entries if e.source_type == "corpus_observation"]
        assert len(corpus) == 20
        assert all(e.weight == 0.75 and e.approved_by == "pack-curation:v0.1" for e in corpus)

    def test_no_human_patch_in_compiled(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        out = tmp_path / "compiled"
        assert run_compiler(pack, sp, tp, out, benchmark=bench).returncode == 0
        text = (out / "evidence.jsonl").read_text(encoding="utf-8")
        assert "human_patch" not in text

    def test_no_absolute_path_in_compiled(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        out = tmp_path / "compiled"
        assert run_compiler(pack, sp, tp, out, benchmark=bench).returncode == 0
        for f in out.iterdir():
            assert "/home/" not in f.read_text(encoding="utf-8") and str(tmp_path) not in f.read_text(encoding="utf-8")

    def test_no_raw_body_field_in_compiled(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        out = tmp_path / "compiled"
        assert run_compiler(pack, sp, tp, out, benchmark=bench).returncode == 0
        for name in ("sources.jsonl", "techniques.jsonl", "evidence.jsonl", "sequential_inputs.jsonl"):
            for line in (out / name).read_text(encoding="utf-8").splitlines():
                rec = json.loads(line)
                assert not ({"body", "full_text", "raw_text", "raw_body", "text"} & set(rec)), name

    def test_failed_compile_preserves_existing_target(self, fixture, tmp_path):
        root, pack, sp, tp, bench = fixture
        out = tmp_path / "compiled"
        assert run_compiler(pack, sp, tp, out, benchmark=bench).returncode == 0
        before = {p.name: p.read_bytes() for p in out.iterdir()}
        # now break an input and recompile to the SAME target
        sp_bad, tp_bad = write_curated(
            tmp_path / "v11", pack,
            mutate_techniques=lambda recs: [
                {**r, "action": "nope"} if r["id"] == "T001" else r for r in recs
            ],
        )
        result = run_compiler(pack, sp_bad, tp_bad, out, benchmark=bench)
        assert result.returncode != 0
        after = {p.name: p.read_bytes() for p in out.iterdir()}
        assert after == before, "failed compile polluted the existing target"
        # republish over existing target also works
        assert run_compiler(pack, sp, tp, out, benchmark=bench).returncode == 0
        assert {p.name: p.read_bytes() for p in out.iterdir()} == before
        assert not any(p.name.startswith("compiled.") for p in tmp_path.iterdir())


# --- 30: real compiled snapshot ----------------------------------------------------------


class TestRealCompiledSnapshot:
    def test_snapshot_counts_and_abi(self):
        compiled = BENCH / "compiled"
        sources = [json.loads(line) for line in (compiled / "sources.jsonl").read_text(encoding="utf-8").splitlines()]
        techs = [json.loads(line) for line in (compiled / "techniques.jsonl").read_text(encoding="utf-8").splitlines()]
        evidence = [json.loads(line) for line in (compiled / "evidence.jsonl").read_text(encoding="utf-8").splitlines()]
        sequential = [json.loads(line) for line in (compiled / "sequential_inputs.jsonl").read_text(encoding="utf-8").splitlines()]
        assert (len(sources), len(techs), len(evidence), len(sequential)) == (14, 20, 20, 20)
        assert [t["id"] for t in techs] == [f"T{i:03d}" for i in range(1, 21)]
        assert all(s["raw_sha256"] for s in sources)  # v0.1: all raw required and present
        assert [s["task_id"] for s in sequential] == [f"T{i:02d}" for i in range(1, 21)]
        assert sequential[0]["prior_task_ids"] == []
        assert sequential[-1]["prior_task_ids"] == [f"T{i:02d}" for i in range(1, 20)]
        EditorialEvidenceStore(compiled / "evidence.jsonl")
        manifest = json.loads((compiled / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["counts"] == {"sources": 14, "techniques": 20, "evidence": 20,
                                      "sequential_inputs": 20}

    def test_real_pack_recompile_is_byte_identical(self, tmp_path):
        """Conditional on the external pack being present on this host (documented
        condition — not an unconditional skip): recompiling the real inputs must
        reproduce the committed snapshot byte-for-byte."""
        if not REAL_PACK.is_dir():
            pytest.skip(f"external pack not present: {REAL_PACK}")
        out = tmp_path / "recompiled"
        result = run_compiler(
            REAL_PACK,
            BENCH / "curated" / "sources.jsonl",
            BENCH / "curated" / "techniques.jsonl",
            out,
            benchmark=BENCH / "benchmark.jsonl",
        )
        assert result.returncode == 0, result.stderr
        compiled = BENCH / "compiled"
        for f in compiled.iterdir():
            assert f.read_bytes() == (out / f.name).read_bytes(), f.name
