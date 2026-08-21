"""Normalize an existing WCASE run record into the coach metric schema.

T001 (docs/runtime-refoundation/TASKS.md): one command emits comparable JSON
for an existing WCASE record, per SPEC §7 ("Runtime acceptance record") and
BENCHMARKS §2 ("Required metrics").

The mapping is purely mechanical. It never evaluates quality and never
fabricates metrics: anything the record does not carry is ``null`` with a
note. Raw provider fields are preserved verbatim under ``raw.usage``.

Source record format (written by tools/run_writing_eval.py as
``draft-record.json`` / ``revision-record.json``)::

    {
      "run_id", "task_id", "status", "outcome",
      "model_requests": int,
      "usage": {
        "input_tokens", "output_tokens", "cache_read_tokens", ...
        "details": {"prompt_cache_hit_tokens", "prompt_cache_miss_tokens",
                     "reasoning_tokens"},
        "cost", "requests", "tool_calls"
      },
      "tool_effect_facts": [["<tool_name>", "<status>"], ...],
      "wall_clock_ms": number | null,
      "request_latencies_ms": [number | null, ...] | null,
      "tool_latencies_ms": {"<tool_name>": [number | null, ...]} | null,
      "largest_input_tokens": number | null,
      "artifact_path", "artifact_exists", "artifact_chars", "artifact_sha256",
      "prep": {...}
    }

Usage:

    uv run python tools/normalize_wcase_metrics.py \
        workspace/artifacts/writing-v0.2/eval/WCASE-1/learned/draft-record.json

``case`` / ``variant`` / ``pass`` labels are derived from the record path
(``eval/<CASE>/<VARIANT>/<PASS>-record.json``); each can be overridden.
``--outcome-pass`` / ``--evidence-pass`` exist because those gates are human
judgments — they stay ``null`` until supplied.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _num(value: Any) -> int | float | None:
    """Pass through numbers only — strings/bools/None never become metrics."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _latency_list(value: Any) -> list[int | float | None] | None:
    if not isinstance(value, list):
        return None
    return [_num(item) for item in value]


def _tool_latency_map(value: Any) -> dict[str, list[int | float | None] | None] | None:
    if not isinstance(value, dict):
        return None
    normalized: dict[str, list[int | float | None] | None] = {}
    for tool_name, values in sorted(value.items(), key=lambda item: str(item[0])):
        normalized[str(tool_name)] = _latency_list(values)
    return normalized


def derive_labels(record_path: Path) -> tuple[str | None, str | None, str | None]:
    """Derive (case, variant, pass) from ``.../eval/<CASE>[/<VARIANT>/]<PASS>-record.json``."""
    parts = record_path.parts
    pass_name: str | None = None
    if record_path.stem.endswith("-record"):
        pass_name = record_path.stem[: -len("-record")]
    dirs = list(parts[:-1])
    if "eval" in dirs:
        dirs = dirs[dirs.index("eval") + 1 :]
    case = dirs[0] if dirs else None
    variant = dirs[-1] if len(dirs) > 1 else None
    return case, variant, pass_name


def normalize_record(
    record: dict[str, Any],
    *,
    case: str | None = None,
    variant: str | None = None,
    pass_name: str | None = None,
) -> dict[str, Any]:
    usage = record.get("usage") or {}
    details = usage.get("details") or {}

    requests = _num(usage.get("requests"))
    if requests is None:
        requests = _num(record.get("model_requests"))

    tool_calls = _num(usage.get("tool_calls"))

    # T002 timing fields are mechanical pass-throughs; absent data stays null.
    wall_clock_ms = _num(record.get("wall_clock_ms"))
    request_latencies_ms = _latency_list(record.get("request_latencies_ms"))
    tool_latencies_ms = _tool_latency_map(record.get("tool_latencies_ms"))
    largest_input_tokens = _num(record.get("largest_input_tokens"))
    model_visible_tools = record.get("model_visible_tools")
    if isinstance(model_visible_tools, list):
        model_visible_tools = sorted(str(t) for t in model_visible_tools)
    else:
        model_visible_tools = None

    effects = record.get("tool_effect_facts") or []
    tool_counts = dict(sorted(Counter(str(e[0]) for e in effects if e).items()))

    notes: list[str] = []
    if requests is not None and tool_calls is not None and len(effects) != tool_calls:
        notes.append(
            f"tool_effect_facts count ({len(effects)}) != usage.tool_calls ({tool_calls})"
        )
    if wall_clock_ms is None:
        notes.append("wall_clock_ms not recorded (T002 run timestamps unavailable)")
    if request_latencies_ms is None:
        notes.append("request_latencies_ms not recorded (Harness event timestamps unavailable)")
    if tool_latencies_ms is None:
        notes.append("tool_latencies_ms not recorded (Harness event timestamps unavailable)")
    if largest_input_tokens is None:
        notes.append("largest_input_tokens not recorded (per-request provider usage unavailable)")
    if model_visible_tools is None:
        notes.append("model_visible_tools not recorded (captured from T003 baseline)")
    notes.append("repeated_signatures not computable (tool arguments not persisted)")

    status = record.get("status")
    if status is not None and status != "completed":
        notes.append(f"record status: {status}")

    return {
        "case": case,
        "variant": variant,
        "pass": pass_name,
        "outcome_pass": None,
        "evidence_pass": None,
        "requests": requests,
        "tool_calls": tool_calls,
        "input_tokens": _num(usage.get("input_tokens")),
        "output_tokens": _num(usage.get("output_tokens")),
        "reasoning_tokens": _num(details.get("reasoning_tokens")),
        "cache_read_tokens": _num(
            usage.get("cache_read_tokens", details.get("prompt_cache_hit_tokens"))
        ),
        "cache_miss_tokens": _num(details.get("prompt_cache_miss_tokens")),
        "wall_clock_ms": wall_clock_ms,
        "request_latencies_ms": request_latencies_ms,
        "tool_latencies_ms": tool_latencies_ms,
        "largest_input_tokens": largest_input_tokens,
        "model_visible_tools": model_visible_tools,
        "tool_counts": tool_counts,
        "repeated_signatures": [],
        "notes": notes,
        "raw": {
            "run_id": record.get("run_id"),
            "task_id": record.get("task_id"),
            "status": status,
            "outcome": record.get("outcome"),
            "artifact_chars": record.get("artifact_chars"),
            "artifact_sha256": record.get("artifact_sha256"),
            "model_requests": record.get("model_requests"),
            "tool_effect_facts": record.get("tool_effect_facts"),
            "wall_clock_ms": record.get("wall_clock_ms"),
            "request_latencies_ms": record.get("request_latencies_ms"),
            "tool_latencies_ms": record.get("tool_latencies_ms"),
            "largest_input_tokens": record.get("largest_input_tokens"),
            "runtime_timestamps": record.get("runtime_timestamps"),
            "usage": usage,
        },
    }


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("record", type=Path, help="draft-record.json / revision-record.json path")
    ap.add_argument("--case", default=None, help="override case label (default: derive from path)")
    ap.add_argument("--variant", default=None, help="override variant label (default: derive from path)")
    ap.add_argument("--pass-name", default=None, help="override pass label (default: derive from filename)")
    ap.add_argument(
        "--outcome-pass",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="record the human outcome verdict (default: null — never machine-inferred)",
    )
    ap.add_argument(
        "--evidence-pass",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="record the human evidence verdict (default: null — never machine-inferred)",
    )
    ap.add_argument("--out", type=Path, default=None, help="also write the normalized JSON here")
    args = ap.parse_args(argv)

    derived_case, derived_variant, derived_pass = derive_labels(args.record.resolve())
    normalized = normalize_record(
        json.loads(args.record.read_text(encoding="utf-8")),
        case=args.case or derived_case,
        variant=args.variant or derived_variant,
        pass_name=args.pass_name or derived_pass,
    )
    normalized["outcome_pass"] = args.outcome_pass
    normalized["evidence_pass"] = args.evidence_pass

    text = json.dumps(normalized, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
