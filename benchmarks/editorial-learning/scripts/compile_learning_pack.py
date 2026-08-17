#!/usr/bin/env python3
"""Offline deterministic Pack Compiler (SPEC: writing-intelligence-compilation).

The compiler does ONLY: input validation, legacy candidate cross-check, exact
join, hashing, locators, canonical sort, serialization, transactional publish.
It does NO semantic reasoning, NO technique extraction, NO LLM calls, NO
automatic promotion. Technique semantics come exclusively from the repository
curated layer; the external pack's data/*.jsonl is an integrity reference.

Compiled ABI (five files when --benchmark is given):
  sources.jsonl / techniques.jsonl / evidence.jsonl /
  sequential_inputs.jsonl / manifest.json

Every JSONL record is canonical JSON (sorted keys, compact separators,
ensure_ascii=False) + exactly one trailing newline. No timestamps, no random
ids, no absolute paths — two runs over the same inputs are byte-identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
sys.path[:0] = [
    str(REPO / "plugins" / "zuaef-ace-writing"),
    str(REPO / "src"),
]
from zuaef_ace_writing.editorial import COGNITIVE_ACTIONS, EditorialEvidenceStore

FROZEN_ACTIONS = set(COGNITIVE_ACTIONS)
FROZEN_SENSORS = {
    "template_connectors", "summary_pressure", "uniform_paragraphs",
    "low_concrete_anchor_density", "abstract_noun_density",
}
TECHNIQUE_IDS = [f"T{i:03d}" for i in range(1, 21)]
EVIDENCE_WEIGHT = 0.75
EVIDENCE_APPROVER = "pack-curation:v0.1"
RAW_BODY_KEYS = {"body", "full_text", "raw_text", "raw_body", "text"}


class CompileError(Exception):
    """Fatal input/consistency problem; message names the file and 1-based line."""


def canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_jsonl(path: Path, *, what: str) -> list[tuple[int, dict]]:
    """Parse JSONL; errors carry the file name and 1-based line number."""
    if not path.is_file():
        raise CompileError(f"{what} file not found: {path}")
    records: list[tuple[int, dict]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CompileError(f"{path}:{lineno}: malformed JSON — {exc}") from None
        if not isinstance(rec, dict):
            raise CompileError(f"{path}:{lineno}: record must be a JSON object")
        records.append((lineno, rec))
    return records


def _require(path: Path, lineno: int, rec: dict, key: str, *, kind, nonempty=False):
    if key not in rec:
        raise CompileError(f"{path}:{lineno}: missing required field {key!r}")
    value = rec[key]
    if kind is bool:
        if not isinstance(value, bool):
            raise CompileError(f"{path}:{lineno}: field {key!r} must be boolean")
    elif not isinstance(value, kind):
        raise CompileError(f"{path}:{lineno}: field {key!r} must be {kind.__name__}")
    if nonempty and not value:
        raise CompileError(f"{path}:{lineno}: field {key!r} must be non-empty")
    return value


def _require_str_array(path: Path, lineno: int, rec: dict, key: str, *, nonempty=False):
    value = _require(path, lineno, rec, key, kind=list)
    for item in value:
        if not isinstance(item, str) or not item:
            raise CompileError(f"{path}:{lineno}: field {key!r} must contain non-empty strings")
    if nonempty and not value:
        raise CompileError(f"{path}:{lineno}: field {key!r} must be non-empty")
    return value


# --- curated layer validation ---------------------------------------------------


def validate_curated_sources(path: Path, pack: Path) -> list[dict]:
    records = load_jsonl(path, what="curated sources")
    seen: set[str] = set()
    out: list[dict] = []
    for lineno, rec in records:
        sid = _require(path, lineno, rec, "id", kind=str, nonempty=True)
        if sid in seen:
            raise CompileError(f"{path}:{lineno}: duplicate source id {sid!r}")
        seen.add(sid)
        _require(path, lineno, rec, "source_type", kind=str, nonempty=True)
        _require(path, lineno, rec, "url", kind=str, nonempty=True)
        raw_required = _require(path, lineno, rec, "raw_required", kind=bool)
        curated_path = _require(path, lineno, rec, "curated_path", kind=str, nonempty=True)
        if curated_path.startswith("/") or ".." in Path(curated_path).parts:
            raise CompileError(
                f"{path}:{lineno}: curated_path must be pack-relative without '..': {curated_path!r}"
            )
        if not (pack / curated_path).is_file():
            raise CompileError(
                f"{path}:{lineno}: curated file missing from pack: {curated_path!r}"
            )
        raw_path = rec.get("raw_path")
        if raw_required:
            if not isinstance(raw_path, str) or not raw_path:
                raise CompileError(f"{path}:{lineno}: raw_required=true but raw_path missing")
            if raw_path.startswith("/") or ".." in Path(raw_path).parts:
                raise CompileError(f"{path}:{lineno}: raw_path must be pack-relative: {raw_path!r}")
            if not (pack / raw_path).is_file():
                raise CompileError(
                    f"{path}:{lineno}: required raw file missing from pack: {raw_path!r}"
                )
        else:
            raw_path = None  # optional missing normalized later
        out.append(rec)
    return out


def validate_curated_techniques(path: Path, source_ids: set[str]) -> list[dict]:
    records = load_jsonl(path, what="curated techniques")
    seen: set[str] = set()
    out: list[dict] = []
    for lineno, rec in records:
        tid = _require(path, lineno, rec, "id", kind=str, nonempty=True)
        if tid in seen:
            raise CompileError(f"{path}:{lineno}: duplicate technique id {tid!r}")
        seen.add(tid)
        _require(path, lineno, rec, "name", kind=str, nonempty=True)
        _require_str_array(path, lineno, rec, "condition", nonempty=True)
        action = _require(path, lineno, rec, "action", kind=str, nonempty=True)
        if action not in FROZEN_ACTIONS:
            raise CompileError(
                f"{path}:{lineno}: action {action!r} not in frozen five {sorted(FROZEN_ACTIONS)}"
            )
        _require(path, lineno, rec, "instruction", kind=str, nonempty=True)
        _require_str_array(path, lineno, rec, "preserve")
        _require_str_array(path, lineno, rec, "anti_pattern")
        _require_str_array(path, lineno, rec, "domain", nonempty=True)
        sources = _require_str_array(path, lineno, rec, "sources", nonempty=True)
        for sid in sources:
            if sid not in source_ids:
                raise CompileError(f"{path}:{lineno}: technique references unknown source {sid!r}")
        primary = _require(path, lineno, rec, "primary_source", kind=str, nonempty=True)
        if primary not in sources:
            raise CompileError(
                f"{path}:{lineno}: primary_source {primary!r} not a member of sources"
            )
        confidence = rec.get("confidence")
        if not isinstance(confidence, dict):
            raise CompileError(f"{path}:{lineno}: missing required field 'confidence'")
        level = confidence.get("level")
        if level not in ("low", "medium", "high"):
            raise CompileError(f"{path}:{lineno}: confidence.level must be low|medium|high")
        basis = confidence.get("basis")
        if not isinstance(basis, list) or not basis or not all(
            isinstance(b, str) and b for b in basis
        ):
            raise CompileError(
                f"{path}:{lineno}: confidence.basis must be a non-empty string array"
            )
        activation = rec.get("activation")
        if not isinstance(activation, dict):
            raise CompileError(f"{path}:{lineno}: missing required field 'activation'")
        mode = activation.get("mode")
        if mode not in ("sensor", "context", "hybrid"):
            raise CompileError(f"{path}:{lineno}: activation.mode must be sensor|context|hybrid")
        triggers = activation.get("trigger_signals")
        if not isinstance(triggers, list) or not all(isinstance(s, str) for s in triggers):
            raise CompileError(f"{path}:{lineno}: activation.trigger_signals must be a string array")
        for sig in triggers:
            if sig not in FROZEN_SENSORS:
                raise CompileError(
                    f"{path}:{lineno}: trigger signal {sig!r} not in frozen five sensors"
                )
        if mode in ("sensor", "hybrid") and not triggers:
            raise CompileError(f"{path}:{lineno}: activation.mode={mode} requires non-empty trigger_signals")
        if mode == "context" and triggers:
            raise CompileError(f"{path}:{lineno}: activation.mode=context requires empty trigger_signals")
        contexts = activation.get("context_signals")
        if not isinstance(contexts, list) or not all(
            isinstance(c, str) and c for c in contexts
        ):
            raise CompileError(
                f"{path}:{lineno}: activation.context_signals must be an array of non-empty strings"
            )
        if mode in ("context", "hybrid") and not contexts:
            raise CompileError(f"{path}:{lineno}: activation.mode={mode} requires non-empty context_signals")
        tags = activation.get("situation_tags")
        if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
            raise CompileError(f"{path}:{lineno}: activation.situation_tags must be a string array")
        _require(path, lineno, rec, "rationale", kind=str, nonempty=True)
        out.append(rec)
    missing = [tid for tid in TECHNIQUE_IDS if tid not in seen]
    if missing:
        raise CompileError(f"{path}: missing technique id(s): {', '.join(missing)}")
    extra = seen - set(TECHNIQUE_IDS)
    if extra:
        raise CompileError(f"{path}: unexpected technique id(s): {', '.join(sorted(extra))}")
    return out


# --- legacy cross-check -----------------------------------------------------------


def cross_check_legacy(pack: Path, curated_sources: list[dict], curated_techniques: list[dict]) -> None:
    pack_sources_path = pack / "data" / "sources.jsonl"
    pack_techs_path = pack / "data" / "techniques.jsonl"
    legacy_sources = {rec["id"]: (lineno, rec) for lineno, rec in load_jsonl(pack_sources_path, what="pack legacy sources")}
    legacy_techs = {rec["id"]: (lineno, rec) for lineno, rec in load_jsonl(pack_techs_path, what="pack legacy techniques")}

    curated_ids = {r["id"] for r in curated_sources}
    if set(legacy_sources) != curated_ids:
        diff = sorted(set(legacy_sources) ^ curated_ids)
        raise CompileError(f"{pack_sources_path}: legacy/curated source id sets differ: {diff}")
    for rec in curated_sources:
        lineno, legacy = legacy_sources[rec["id"]]
        if legacy.get("url") != rec["url"]:
            raise CompileError(
                f"{pack_sources_path}:{lineno}: legacy url mismatch for {rec['id']!r}: "
                f"{legacy.get('url')!r} != {rec['url']!r}"
            )

    curated_tech_ids = {r["id"] for r in curated_techniques}
    if set(legacy_techs) != curated_tech_ids:
        diff = sorted(set(legacy_techs) ^ curated_tech_ids)
        raise CompileError(f"{pack_techs_path}: legacy/curated technique id sets differ: {diff}")
    for rec in curated_techniques:
        lineno, legacy = legacy_techs[rec["id"]]
        if legacy.get("name") != rec["name"]:
            raise CompileError(
                f"{pack_techs_path}:{lineno}: legacy name mismatch for {rec['id']}: "
                f"{legacy.get('name')!r} != {rec['name']!r}"
            )
        if sorted(legacy.get("source", [])) != sorted(rec["sources"]):
            raise CompileError(
                f"{pack_techs_path}:{lineno}: legacy source mismatch for {rec['id']}: "
                f"{sorted(legacy.get('source', []))} != {sorted(rec['sources'])}"
            )
        if legacy.get("maps_to") != rec["action"]:
            raise CompileError(
                f"{pack_techs_path}:{lineno}: legacy maps_to mismatch for {rec['id']}: "
                f"{legacy.get('maps_to')!r} != {rec['action']!r}"
            )


# --- compiled ABI ------------------------------------------------------------------


def _locator(text: str, path_for_error: Path, rel: str) -> dict:
    lines = text.splitlines()
    if not lines:
        raise CompileError(f"{path_for_error}: file is empty, cannot build locator: {rel}")
    return {"line_start": 1, "line_end": len(lines)}


def build_sources(pack: Path, curated_sources: list[dict]) -> list[dict]:
    out = []
    for rec in curated_sources:
        curated_text = (pack / rec["curated_path"]).read_text(encoding="utf-8")
        node = {
            "id": rec["id"],
            "node_id": f"sources/{rec['id']}",
            "source_type": rec["source_type"],
            "url": rec["url"],
            "curated_path": rec["curated_path"],
            "curated_sha256": sha256_text(curated_text),
            "curated_locator": _locator(curated_text, pack / rec["curated_path"], rec["curated_path"]),
            "raw_required": rec["raw_required"],
        }
        raw_path = rec.get("raw_path")
        if isinstance(raw_path, str) and (pack / raw_path).is_file():
            raw_text = (pack / raw_path).read_text(encoding="utf-8")
            node.update({
                "raw_path": raw_path,
                "raw_sha256": sha256_text(raw_text),
                "raw_locator": _locator(raw_text, pack / raw_path, raw_path),
            })
        else:
            if rec["raw_required"]:
                raise CompileError(f"required raw missing for {rec['id']}")  # already validated; defense
            node.update({"raw_path": None, "raw_sha256": None, "raw_locator": None})
        out.append(node)
    out.sort(key=lambda n: n["id"])
    return out


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


_SORTED_ARRAY_KEYS = (
    "condition", "preserve", "anti_pattern", "domain", "sources",
)


def build_techniques(curated_techniques: list[dict]) -> list[dict]:
    out = []
    for rec in curated_techniques:
        node = dict(rec)
        node["node_id"] = f"techniques/{rec['id']}"
        for key in _SORTED_ARRAY_KEYS:
            node[key] = sorted(rec[key])
        node["confidence"] = {**rec["confidence"], "basis": sorted(rec["confidence"]["basis"])}
        activation = {
            "mode": rec["activation"]["mode"],
            "trigger_signals": sorted(rec["activation"]["trigger_signals"]),
            "context_signals": sorted(rec["activation"]["context_signals"]),
            "situation_tags": sorted(rec["activation"]["situation_tags"]),
        }
        node["activation"] = activation
        out.append(node)
    out.sort(key=lambda n: n["id"])
    return out


def build_evidence(techniques: list[dict]) -> list[dict]:
    out = []
    for t in techniques:
        out.append({
            "id": f"corpus.{t['id']}",
            "source_type": "corpus_observation",
            "source_ref": f"pack:{t['primary_source']}#technique:{t['id']}",
            "situation_tags": t["activation"]["situation_tags"],
            "trigger_signals": t["activation"]["trigger_signals"],
            "action": t["action"],
            "directive": t["instruction"],
            "rationale": t["rationale"],
            "weight": EVIDENCE_WEIGHT,
            "approved_by": EVIDENCE_APPROVER,
            "before_excerpt": "",
            "after_excerpt": "",
        })
    out.sort(key=lambda e: e["id"])
    return out


def build_sequential(benchmark_path: Path | None, techniques: list[dict]) -> list[dict] | None:
    if benchmark_path is None:
        return None
    records = [
        (lineno, rec)
        for lineno, rec in load_jsonl(benchmark_path, what="benchmark")
    ]
    sequences = [rec.get("sequence") for _, rec in records]
    task_ids = [rec.get("task_id") for _, rec in records]
    if sequences != list(range(1, 21)):
        raise CompileError(
            f"{benchmark_path}: benchmark sequence must be strictly 1..20, got {sequences}"
        )
    if task_ids != [f"T{i:02d}" for i in range(1, 21)]:
        raise CompileError(
            f"{benchmark_path}: benchmark task_id must be exactly T01..T20 unique, got {task_ids}"
        )
    by_source: dict[str, list[str]] = {}
    for t in techniques:
        for sid in t["sources"]:
            by_source.setdefault(sid, []).append(t["id"])
    ordered = sorted(records, key=lambda lr: (lr[1]["sequence"], lr[1]["task_id"]))
    out = []
    for index, (_, rec) in enumerate(ordered):
        source = rec.get("source")
        if not isinstance(source, str) or not source:
            raise CompileError(f"{benchmark_path}: record missing 'source' field")
        candidates = by_source.get(source)
        if not candidates:
            raise CompileError(
                f"{benchmark_path}: source {source!r} has no exact match / no candidate techniques "
                f"(fuzzy matching is forbidden)"
            )
        out.append({
            "task_id": rec["task_id"],
            "sequence": rec["sequence"],
            "source": source,
            "candidate_technique_ids": sorted(candidates),
            "candidate_evidence_ids": [f"corpus.{tid}" for tid in sorted(candidates)],
            "prior_task_ids": [r["task_id"] for _, r in ordered[:index]],
            "benchmark_record_sha256": sha256_text(canon(rec)),
        })
    return out


# --- staging / verification / publish ----------------------------------------------


def render(staging: Path, sources: list[dict], techniques: list[dict], evidence: list[dict],
           sequential: list[dict] | None, manifest: dict) -> None:
    staging.mkdir(parents=True)
    files: list[tuple[str, list[dict] | None]] = [
        ("sources.jsonl", sources), ("techniques.jsonl", techniques), ("evidence.jsonl", evidence),
        ("sequential_inputs.jsonl", sequential),
    ]
    for name, records in files:
        if records is None:
            continue
        (staging / name).write_text(
            "".join(canon(r) + "\n" for r in records), encoding="utf-8"
        )
    (staging / "manifest.json").write_text(canon(manifest) + "\n", encoding="utf-8")


def verify_staging(staging: Path, expected: dict[str, int]) -> None:
    for name, count in expected.items():
        path = staging / name
        if not path.is_file():
            raise CompileError(f"staging verification: {name} missing")
        text = path.read_text(encoding="utf-8")
        if "/home/" in text or str(REPO) in text:
            raise CompileError(f"staging verification: absolute path leaked into {name}")
        records = []
        for lineno, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                raise CompileError(f"staging verification: {name}:{lineno} malformed") from None
            if RAW_BODY_KEYS & set(rec):
                raise CompileError(
                    f"staging verification: {name}:{lineno} carries raw body field "
                    f"{sorted(RAW_BODY_KEYS & set(rec))}"
                )
            records.append(rec)
        if len(records) != count:
            raise CompileError(f"staging verification: {name} has {len(records)} records, expected {count}")
        if name == "manifest.json":
            continue
        for lineno, rec in enumerate(records, 1):
            if canon(rec) != json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":")):
                raise CompileError(f"staging verification: {name}:{lineno} not canonical")
    # real capability must accept the evidence file
    EditorialEvidenceStore(staging / "evidence.jsonl")
    # manifest hashes must match staged bytes
    manifest = json.loads((staging / "manifest.json").read_text(encoding="utf-8"))
    for name, info in manifest["files"].items():
        if sha256_file(staging / name) != info["sha256"]:
            raise CompileError(f"staging verification: manifest hash mismatch for {name}")


def transactional_publish(out: Path, staging: Path) -> None:
    parent = out.parent
    parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        os.rename(staging, out)
        return
    backup = parent / f"{out.name}.backup-{os.getpid()}"
    os.rename(out, backup)
    try:
        os.rename(staging, out)
    except OSError:
        os.rename(backup, out)  # rollback
        raise
    shutil.rmtree(backup)


def compile_pack(pack: Path, curated_sources_path: Path, curated_techniques_path: Path,
                 benchmark_path: Path | None, out: Path) -> None:
    pack = pack.expanduser().resolve()
    if not pack.is_dir():
        raise CompileError(f"pack directory not found: {pack}")
    curated_sources = validate_curated_sources(curated_sources_path, pack)
    curated_techniques = validate_curated_techniques(
        curated_techniques_path, {r["id"] for r in curated_sources}
    )
    cross_check_legacy(pack, curated_sources, curated_techniques)

    sources = build_sources(pack, curated_sources)
    techniques = build_techniques(curated_techniques)
    evidence = build_evidence(techniques)
    sequential = build_sequential(benchmark_path, techniques)

    files_map = {
        "sources.jsonl": {"sha256": None, "records": len(sources)},
        "techniques.jsonl": {"sha256": None, "records": len(techniques)},
        "evidence.jsonl": {"sha256": None, "records": len(evidence)},
    }
    if sequential is not None:
        files_map["sequential_inputs.jsonl"] = {"sha256": None, "records": len(sequential)}
    manifest = {
        "schema_version": "1.0",
        "benchmark_provided": benchmark_path is not None,
        "counts": {
            "sources": len(sources), "techniques": len(techniques),
            "evidence": len(evidence),
            "sequential_inputs": len(sequential) if sequential is not None else 0,
        },
        "files": files_map,
        "inputs": {
            "curated_sources_sha256": sha256_file(curated_sources_path),
            "curated_techniques_sha256": sha256_file(curated_techniques_path),
            "pack_sources_sha256": sha256_file(pack / "data" / "sources.jsonl"),
            "pack_techniques_sha256": sha256_file(pack / "data" / "techniques.jsonl"),
            "benchmark_sha256": sha256_file(benchmark_path) if benchmark_path else None,
        },
    }

    staging = out.parent / f"{out.name}.staging-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    try:
        render(staging, sources, techniques, evidence, sequential, manifest)
        # fill manifest hashes from staged bytes, then rewrite manifest + re-verify
        for name, info in files_map.items():
            info["sha256"] = sha256_file(staging / name)
        (staging / "manifest.json").write_text(canon(manifest) + "\n", encoding="utf-8")
        verify_staging(staging, {name: info["records"] for name, info in files_map.items()} | {"manifest.json": 1})
        transactional_publish(out, staging)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    print(
        f"compiled {len(sources)} sources / {len(techniques)} techniques / "
        f"{len(evidence)} evidence / {len(sequential) if sequential else 0} sequential "
        f"-> {out}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pack", required=True)
    ap.add_argument("--curated-sources", required=True)
    ap.add_argument("--curated-techniques", required=True)
    ap.add_argument("--benchmark")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    try:
        compile_pack(
            Path(args.pack),
            Path(args.curated_sources),
            Path(args.curated_techniques),
            Path(args.benchmark) if args.benchmark else None,
            Path(args.out),
        )
    except CompileError as exc:
        print(f"COMPILE FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
