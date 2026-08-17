#!/usr/bin/env python3
"""Sequential human-patch promotion for the editorial-learning benchmark.

The learning proof (Gate F) requires the runtime evidence file to GROW task
by task — never loaded all at once:

    T01  run with seeds only  ->  promote T01 patches
    T02  run with seeds + T01 ->  promote T02 patches
    ...
    T20  run with seeds + T01..T19

This tool enforces that order on the evidence file it maintains:

  promote_patch.py --task T03 --out FILE    append T03's patches, but only if
                                            every earlier task that has
                                            patches is already present
  promote_patch.py --status --out FILE      show T01..T20 promotion state
  promote_patch.py --init --out FILE        truncate to an empty file
                                            (static mode = seeds only, which
                                            the capability loads built-in)

Idempotent: re-promoting a task appends nothing. The file is validated
through the real EditorialEvidenceStore after every write.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
REPO = BENCH.parents[1]
sys.path[:0] = [
    str(REPO / "plugins" / "zuaef-ace-writing"),
    str(REPO / "src"),
]
from zuaef_ace_writing.editorial import EditorialEvidenceStore


def load_pool() -> dict[str, list[dict]]:
    """task_id -> human patch entries, from the benchmark's evidence pool."""
    pool: dict[str, list[dict]] = {}
    bench = [
        json.loads(line)
        for line in (BENCH / "benchmark.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    patches = [
        json.loads(line)
        for line in (BENCH / "evidence" / "human_patches.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    by_id = {p["id"]: p for p in patches}
    for row in bench:
        pool[row["task_id"]] = [by_id[i] for i in row["evidence_ids"] if i in by_id]
    return pool


def read_out(out: Path) -> list[dict]:
    if not out.is_file():
        return []
    return [
        json.loads(line)
        for line in out.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate(out: Path) -> int:
    store = EditorialEvidenceStore(out)  # raises CompositionError on bad content
    return sum(1 for e in store._entries if e.source_type == "human_patch")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", help="task id to promote, e.g. T03")
    ap.add_argument("--out", required=True, help="runtime evidence file to maintain")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--init", action="store_true", help="truncate to empty (static mode)")
    args = ap.parse_args()
    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    pool = load_pool()

    if args.init:
        out.write_text("", encoding="utf-8")
        print(f"initialized empty evidence file: {out} (seeds load built-in)")
        return

    present = {e["id"] for e in read_out(out)}
    if args.status:
        for tid in sorted(pool):
            ids = [p["id"] for p in pool[tid]]
            done = [i for i in ids if i in present]
            state = "promoted" if len(done) == len(ids) else (
                "partial" if done else ("no patches" if not ids else "pending")
            )
            print(f"  {tid}: {state} ({len(done)}/{len(ids)})")
        print(f"  human_patch total in file: {len(present)}")
        return

    if not args.task:
        ap.error("either --task, --status or --init is required")
    tid = args.task.upper()
    if tid not in pool:
        raise SystemExit(f"unknown task {tid}")
    # strict sequence: every earlier task that HAS patches must be fully present
    order = sorted(pool)
    for earlier in order[: order.index(tid)]:
        ids = [p["id"] for p in pool[earlier]]
        missing = [i for i in ids if i not in present]
        if missing:
            raise SystemExit(
                f"sequence violation: {earlier} has {len(missing)} unpromoted "
                f"patches (e.g. {missing[0]}). Promote {earlier} first."
            )
    to_add = [p for p in pool[tid] if p["id"] not in present]
    if not to_add:
        print(f"{tid}: nothing to promote (already present / no patches)")
        return
    with out.open("a", encoding="utf-8") as fh:
        for p in to_add:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    total = validate(out)
    print(f"promoted {len(to_add)} patches for {tid}; human_patch total: {total}")


if __name__ == "__main__":
    main()
