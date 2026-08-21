"""T001 — WCASE record → coach metric schema normalization.

The normalizer (tools/normalize_wcase_metrics.py) is mechanical only: fields
map or become null, raw provider fields survive verbatim, and nothing is
inferred.
"""

from __future__ import annotations

import json

from tools.normalize_wcase_metrics import derive_labels, main, normalize_record


def _record(**overrides) -> dict:
    record = {
        "run_id": "wcase-1-single-source",
        "task_id": "wcase-1-single-source",
        "status": "completed",
        "outcome": "Returned the result to the current user.",
        "model_requests": 12,
        "usage": {
            "input_tokens": 243596,
            "cache_read_tokens": 172032,
            "output_tokens": 25456,
            "details": {
                "prompt_cache_hit_tokens": 172032,
                "prompt_cache_miss_tokens": 71564,
                "reasoning_tokens": 21166,
            },
            "cost": 0.0176,
            "requests": 12,
            "tool_calls": 3,
        },
        "tool_effect_facts": [
            ["list_materials", "completed"],
            ["read_material", "completed"],
            ["read_material", "completed"],
        ],
        "artifact_chars": 1035,
        "artifact_sha256": "a7f5b3e37d939cce8a7d42e1410773f738e7cfa5c94f03eb8c6dd5cca1a5afe6",
    }
    record.update(overrides)
    return record


def test_maps_provider_fields_to_coach_schema():
    normalized = normalize_record(_record(), case="WCASE-1", variant="learned", pass_name="draft")
    assert normalized["case"] == "WCASE-1"
    assert normalized["variant"] == "learned"
    assert normalized["pass"] == "draft"
    assert normalized["requests"] == 12
    assert normalized["tool_calls"] == 3
    assert normalized["input_tokens"] == 243596
    assert normalized["output_tokens"] == 25456
    assert normalized["reasoning_tokens"] == 21166
    assert normalized["cache_read_tokens"] == 172032
    assert normalized["cache_miss_tokens"] == 71564
    assert normalized["tool_counts"] == {"list_materials": 1, "read_material": 2}
    # raw provider fields survive verbatim
    assert normalized["raw"]["usage"] == _record()["usage"]
    assert normalized["raw"]["artifact_sha256"] == _record()["artifact_sha256"]


def test_maps_available_timing_fields_and_preserves_runtime_facts():
    record = _record(
        wall_clock_ms=321.5,
        request_latencies_ms=[100.25, None],
        tool_latencies_ms={"read_material": [4.5, 6.0]},
        largest_input_tokens=9876,
        runtime_timestamps={
            "started_at": "2026-08-21T00:00:00+00:00",
            "finished_at": "2026-08-21T00:00:00.321500+00:00",
        },
    )

    normalized = normalize_record(record)

    assert normalized["wall_clock_ms"] == 321.5
    assert normalized["request_latencies_ms"] == [100.25, None]
    assert normalized["tool_latencies_ms"] == {"read_material": [4.5, 6.0]}
    assert normalized["largest_input_tokens"] == 9876
    assert normalized["raw"]["runtime_timestamps"] == record["runtime_timestamps"]
    assert normalized["raw"]["request_latencies_ms"] == record["request_latencies_ms"]


def test_missing_metrics_are_null_not_fabricated():
    normalized = normalize_record({}, case="WCASE-1", variant=None, pass_name="draft")
    for key in (
        "requests",
        "tool_calls",
        "input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "cache_read_tokens",
        "cache_miss_tokens",
        "wall_clock_ms",
        "request_latencies_ms",
        "tool_latencies_ms",
        "largest_input_tokens",
        "model_visible_tools",
        "outcome_pass",
        "evidence_pass",
    ):
        assert normalized[key] is None, key
    assert normalized["tool_counts"] == {}
    assert normalized["repeated_signatures"] == []
    assert any("T002" in note for note in normalized["notes"])


def test_requests_falls_back_to_model_requests():
    record = _record()
    record["usage"] = {k: v for k, v in record["usage"].items() if k != "requests"}
    normalized = normalize_record(record)
    assert normalized["requests"] == 12


def test_effect_count_mismatch_is_noted():
    record = _record()
    record["usage"] = {**record["usage"], "tool_calls": 24}
    notes = normalize_record(record)["notes"]
    assert any("tool_effect_facts count (3) != usage.tool_calls (24)" in n for n in notes)


def test_non_completed_status_is_noted():
    notes = normalize_record(_record(status="partial"))["notes"]
    assert any("status: partial" in n for n in notes)


def test_path_label_derivation(tmp_path):
    nested = tmp_path / "eval" / "WCASE-2" / "baseline" / "draft-record.json"
    nested.parent.mkdir(parents=True)
    nested.write_text("{}", encoding="utf-8")
    assert derive_labels(nested.resolve()) == ("WCASE-2", "baseline", "draft")

    flat = tmp_path / "eval" / "WCASE-1" / "revision-record.json"
    flat.parent.mkdir(parents=True)
    flat.write_text("{}", encoding="utf-8")
    assert derive_labels(flat.resolve()) == ("WCASE-1", None, "revision")


def test_cli_emits_comparable_json(tmp_path, capsys):
    record_path = tmp_path / "eval" / "WCASE-1" / "learned" / "draft-record.json"
    record_path.parent.mkdir(parents=True)
    record_path.write_text(json.dumps(_record()), encoding="utf-8")

    main([str(record_path)])
    emitted = json.loads(capsys.readouterr().out)

    assert emitted["case"] == "WCASE-1"
    assert emitted["variant"] == "learned"
    assert emitted["pass"] == "draft"
    assert emitted["requests"] == 12
    assert emitted["outcome_pass"] is None
    assert emitted["evidence_pass"] is None

    # human gates are flags, never machine-inferred
    main([str(record_path), "--outcome-pass"])
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["outcome_pass"] is True
    assert emitted["evidence_pass"] is None
