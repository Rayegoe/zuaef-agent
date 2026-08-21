#!/usr/bin/env python3
"""Compare two normalized ZUAEF runtime metric JSON files.

This script deliberately does not decide business quality. It only makes
runtime deltas explicit; outcome/evidence gates remain separate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRICS = (
    "requests",
    "tool_calls",
    "input_tokens",
    "output_tokens",
    "reasoning_tokens",
    "cache_read_tokens",
    "cache_miss_tokens",
    "wall_clock_ms",
    "largest_input_tokens",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    deltas: dict[str, Any] = {}
    for key in METRICS:
        b = numeric(before.get(key))
        a = numeric(after.get(key))
        if b is None or a is None:
            deltas[key] = {"before": before.get(key), "after": after.get(key), "delta": None}
            continue
        pct = None if b == 0 else ((a - b) / b) * 100
        deltas[key] = {
            "before": b,
            "after": a,
            "delta": a - b,
            "percent": pct,
        }

    before_tools = set(before.get("model_visible_tools") or [])
    after_tools = set(after.get("model_visible_tools") or [])
    return {
        "case": after.get("case") or before.get("case"),
        "outcome": {
            "before": before.get("outcome_pass"),
            "after": after.get("outcome_pass"),
        },
        "evidence": {
            "before": before.get("evidence_pass"),
            "after": after.get("evidence_pass"),
        },
        "metrics": deltas,
        "model_visible_tools": {
            "added": sorted(after_tools - before_tools),
            "removed": sorted(before_tools - after_tools),
            "before_count": len(before_tools),
            "after_count": len(after_tools),
        },
        "repeated_signatures": {
            "before": before.get("repeated_signatures") or [],
            "after": after.get("repeated_signatures") or [],
        },
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("before", type=Path)
    p.add_argument("after", type=Path)
    p.add_argument("--json", action="store_true", dest="as_json")
    args = p.parse_args()

    result = compare(load(args.before), load(args.after))
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"case: {result['case']}")
    print(f"outcome: {result['outcome']}")
    print(f"evidence: {result['evidence']}")
    for name, row in result["metrics"].items():
        pct = row.get("percent")
        pct_text = "" if pct is None else f" ({pct:+.1f}%)"
        print(f"{name}: {row['before']} -> {row['after']} | delta={row['delta']}{pct_text}")
    tools = result["model_visible_tools"]
    print(f"visible tools: {tools['before_count']} -> {tools['after_count']}")
    if tools["added"]:
        print("  added:", ", ".join(tools["added"]))
    if tools["removed"]:
        print("  removed:", ", ".join(tools["removed"]))


if __name__ == "__main__":
    main()
