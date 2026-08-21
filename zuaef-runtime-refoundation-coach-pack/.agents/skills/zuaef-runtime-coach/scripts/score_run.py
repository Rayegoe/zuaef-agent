#!/usr/bin/env python3
"""Compute a diagnostic runtime-complexity score from a normalized record.

The score is not an acceptance criterion. Business outcome and evidence gates
must be evaluated independently.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def n(record: dict[str, Any], key: str) -> float:
    value = record.get(key)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def score(record: dict[str, Any]) -> dict[str, float]:
    requests = n(record, "requests")
    tool_calls = n(record, "tool_calls")
    input_tokens = n(record, "input_tokens")
    reasoning = n(record, "reasoning_tokens")
    wall_seconds = n(record, "wall_clock_ms") / 1000.0

    components = {
        "requests": requests * 20.0,
        "tool_calls": tool_calls * 2.0,
        "input_tokens": input_tokens / 10_000.0,
        "reasoning_tokens": reasoning / 5_000.0,
        "wall_clock": wall_seconds * 0.1,
    }
    components["total"] = sum(components.values())
    return components


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("record", type=Path)
    args = p.parse_args()
    record = json.loads(args.record.read_text(encoding="utf-8"))
    print(json.dumps(score(record), indent=2))


if __name__ == "__main__":
    main()
