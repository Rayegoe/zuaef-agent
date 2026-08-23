"""Console projection tests (T003, read-only scope).

Seeds real ``FileStepStore``/receipt data into a temp state root — no
network, no model calls. The load-bearing regression is
``test_legacy_receipt_events_survive``: an unparsable receipt must only lose
receipt-derived facts, never the StepPersistence facts.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.usage import RunUsage
from pydantic_ai_harness.step_persistence import (
    ContinuableSnapshot,
    FileStepStore,
    RunRecord,
    StepEvent,
)
from starlette.testclient import TestClient

from zuaef_agent.config import AgentSettings
from zuaef_agent.web import analysis, analysis_store, readers, sse
from zuaef_agent.web.api import api_routes
from zuaef_agent.web.inspection import (
    inspect_run,
    inspect_run_segment,
    render_run_json,
    render_run_markdown,
    render_run_segment_markdown,
)
from zuaef_agent.web.projector import RunFacts, project_run
from zuaef_agent.web.readers import load_run_facts

T0 = datetime(2026, 8, 21, 11, 0, 0, tzinfo=UTC)


def _settings(tmp_path: Path) -> AgentSettings:
    return AgentSettings(
        model="test",
        workspace_root=tmp_path / "ws",
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )


def _stamp(seconds: int, *, tz: timezone | None = UTC) -> datetime:
    value = T0 + timedelta(seconds=seconds)
    return value if tz is not None else value.replace(tzinfo=None)


async def _seed_events(
    settings: AgentSettings,
    run_id: str,
    specs: list[tuple[str, int, str | None, str | None]],
    *,
    start: datetime = T0,
    naive: bool = False,
) -> None:
    store = FileStepStore(settings.step_store_dir)
    await store.register_run(RunRecord(run_id=run_id, started_at=start))
    for offset, (kind, step, tool_call_id, tool_name) in enumerate(specs):
        stamp = start + timedelta(seconds=offset)
        if naive:
            stamp = stamp.replace(tzinfo=None)
        await store.append_event(
            StepEvent(
                run_id=run_id,
                kind=kind,
                step_index=step,
                timestamp=stamp,
                tool_call_id=tool_call_id,
                tool_name=tool_name,
            )
        )


def _seed_sync(tmp_path: Path, settings: AgentSettings, run_id: str, specs, **kwargs) -> None:
    asyncio.run(_seed_events(settings, run_id, specs, **kwargs))


def _write_receipt(settings: AgentSettings, run_id: str, payload: dict) -> None:
    path = settings.state_root / "receipts" / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _terminal_receipt(run_id: str, **overrides) -> dict:
    payload = {
        "schema_version": "2.0",
        "state": "terminal",
        "run_id": run_id,
        "model": "test-model",
        "started_at": T0.isoformat(),
        "finished_at": (T0 + timedelta(seconds=60)).isoformat(),
        "execution_state": "completed",
        "outcome": "ok",
        "usage": {"input_tokens": 500, "output_tokens": 50},
    }
    payload.update(overrides)
    return payload


COMPLETED_RUN = [
    ("run_started", 0, None, None),
    ("model_request_started", 1, None, None),
    ("model_request_completed", 1, None, None),
    ("tool_call_started", 2, "tc-1", "save_article"),
    ("tool_call_completed", 2, "tc-1", "save_article"),
    ("run_completed", 3, None, None),
]


async def _save_snapshot(settings: AgentSettings, snapshot: ContinuableSnapshot) -> None:
    store = FileStepStore(settings.step_store_dir)
    await store.save_snapshot(snapshot)


def _snapshot(run_id: str, responses: int, requests: int) -> ContinuableSnapshot:
    messages: list[ModelRequest | ModelResponse] = []
    for index in range(requests):
        messages.append(ModelRequest(parts=[UserPromptPart(content=f"q{index}")]))
        if index < responses:
            messages.append(
                ModelResponse(
                    parts=[TextPart(f"a{index}")],
                    usage=RunUsage(input_tokens=100 * (index + 1), output_tokens=10),
                    timestamp=_stamp(30 + index),
                )
            )
    return ContinuableSnapshot(run_id=run_id, step_index=0, messages=messages)


def _snapshot_with_usage(
    run_id: str, usage: list[tuple[int, int]]
) -> ContinuableSnapshot:
    messages: list[ModelRequest | ModelResponse] = []
    for index, (input_tokens, output_tokens) in enumerate(usage):
        messages.append(ModelRequest(parts=[UserPromptPart(content=f"q{index}")]))
        messages.append(
            ModelResponse(
                parts=[TextPart(f"a{index}")],
                usage=RunUsage(
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                ),
                timestamp=_stamp(30 + index),
            )
        )
    return ContinuableSnapshot(run_id=run_id, step_index=0, messages=messages)


def _load(settings: AgentSettings, run_id: str) -> RunFacts:
    facts = asyncio.run(load_run_facts(settings, run_id))
    assert facts is not None
    return facts


# --- status derivation -----------------------------------------------------


def test_completed_with_valid_receipt(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-complete", COMPLETED_RUN)
    _write_receipt(settings, "r-complete", _terminal_receipt("r-complete"))
    projection = project_run(_load(settings, "r-complete"))
    assert projection["run"]["status"] == "completed"
    assert projection["run"]["model"] == "test-model"
    assert projection["usage"]["source"] == "receipt_aggregate"
    assert projection["artifacts"] == []


def test_legacy_receipt_events_survive(tmp_path: Path) -> None:
    """THE regression: unparsable receipt must not erase execution facts."""
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-legacy", COMPLETED_RUN)
    _write_receipt(
        settings,
        "r-legacy",
        {"schema_version": "1.1", "state": "terminal", "run_id": "r-legacy"},
    )
    projection = project_run(_load(settings, "r-legacy"))
    assert projection["run"]["status"] == "completed"
    assert projection["run"]["request_count"] == 1
    assert projection["run"]["tool_call_count"] == 1
    assert projection["run"]["started_at"] is not None
    assert projection["run"]["finished_at"] is not None
    assert projection["artifacts"] == []
    assert projection["composition"] is None
    assert any(
        "receipt_unavailable" in diagnostic
        for diagnostic in projection["diagnostics"]
    )


def test_no_receipt_facts_from_events_only(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-bare", COMPLETED_RUN)
    projection = project_run(_load(settings, "r-bare"))
    assert projection["run"]["status"] == "completed"
    assert projection["run"]["request_count"] == 1
    assert projection["run"]["tool_call_count"] == 1
    assert projection["run"]["display_label"] == "r-bare"
    assert projection["diagnostics"] == []


def test_failed_without_receipt(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "r-failed",
        [
            ("run_started", 0, None, None),
            ("model_request_started", 1, None, None),
            ("model_request_failed", 1, None, None),
            ("run_failed", 2, None, None),
        ],
    )
    projection = project_run(_load(settings, "r-failed"))
    assert projection["run"]["status"] == "failed"
    requests = [row for row in projection["timeline"] if row["kind"] == "model_request"]
    assert requests[0]["status"] == "failed"


def test_incomplete_started_only(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "r-open",
        [("run_started", 0, None, None)],
    )
    projection = project_run(_load(settings, "r-open"))
    assert projection["run"]["status"] == "incomplete"


def test_unresolved_tool_when_settled_started_when_live(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    open_call = [
        ("run_started", 0, None, None),
        ("tool_call_started", 1, "tc-x", "external_write"),
    ]
    _seed_sync(tmp_path, settings, "r-live", open_call)
    live = project_run(_load(settings, "r-live"))
    tools = [r for r in live["timeline"] if r["kind"] == "tool_call"]
    assert tools[0]["status"] == "started"

    _seed_sync(tmp_path, settings, "r-paused", open_call)
    _write_receipt(
        settings,
        "r-paused",
        {
            "schema_version": "2.0",
            "state": "paused",
            "run_id": "r-paused",
            "conversation_id": "c1",
            "model": "test-model",
            "started_at": T0.isoformat(),
            "finished_at": (T0 + timedelta(seconds=5)).isoformat(),
            "pending_approvals": [{"tool_name": "external_write", "tool_call_id": "tc-x", "args": {}}],
            "pending_calls": [],
        },
    )
    paused = project_run(_load(settings, "r-paused"))
    assert paused["run"]["status"] == "paused"
    tools = [r for r in paused["timeline"] if r["kind"] == "tool_call"]
    assert tools[0]["status"] == "unresolved"
    assert paused["pause"]["pending_approvals"][0]["tool_call_id"] == "tc-x"


# --- timestamp semantics ----------------------------------------------------


def test_duration_refuses_mixed_clocks() -> None:
    """One aware start + one naive completion: same row, incomparable clocks —
    the duration stays unknown instead of inventing a timezone."""
    facts = RunFacts(
        run_id="r-mixed-pure",
        record=None,
        events=(
            StepEvent(
                run_id="r-mixed-pure",
                kind="model_request_started",
                step_index=1,
                timestamp=_stamp(0),
            ),
            StepEvent(
                run_id="r-mixed-pure",
                kind="model_request_completed",
                step_index=1,
                timestamp=_stamp(2, tz=None),
            ),
        ),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )
    rows = [r for r in project_run(facts)["timeline"] if r["kind"] == "model_request"]
    assert rows[0]["status"] == "completed"
    assert rows[0]["duration_ms"] is None


def test_naive_events_with_aware_receipt_still_project(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "r-naive",
        COMPLETED_RUN,
        naive=True,
    )
    _write_receipt(settings, "r-naive", _terminal_receipt("r-naive"))
    projection = project_run(_load(settings, "r-naive"))
    assert projection["run"]["status"] == "completed"
    request_row = next(r for r in projection["timeline"] if r["kind"] == "model_request")
    # Same-clock event pair: duration is computable without inventing offsets.
    assert request_row["duration_ms"] == 1000


# --- usage attachment --------------------------------------------------------


def test_per_response_usage_attached_one_to_one(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "r-usage",
        [
            ("run_started", 0, None, None),
            ("model_request_started", 1, None, None),
            ("model_request_completed", 1, None, None),
            ("model_request_started", 2, None, None),
            ("model_request_completed", 2, None, None),
            ("run_completed", 3, None, None),
        ],
    )
    asyncio.run(_save_snapshot(settings, _snapshot("r-usage", responses=2, requests=2)))
    projection = project_run(_load(settings, "r-usage"))
    rows = [r for r in projection["timeline"] if r["kind"] == "model_request"]
    assert [r["usage"]["input_tokens"] for r in rows] == [100, 200]
    assert projection["usage"] == {
        "input_tokens": 300,
        "output_tokens": 20,
        "requests": 2,
        "source": "per_response",
    }


def test_aggregate_usage_never_distributed_to_requests(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "r-partial",
        [
            ("run_started", 0, None, None),
            ("model_request_started", 1, None, None),
            ("model_request_completed", 1, None, None),
            ("model_request_started", 2, None, None),
            ("model_request_completed", 2, None, None),
            ("run_completed", 3, None, None),
        ],
    )
    # Snapshot pruned to one response: correlation is NOT clear for two requests.
    asyncio.run(_save_snapshot(settings, _snapshot("r-partial", responses=1, requests=2)))
    _write_receipt(
        settings,
        "r-partial",
        _terminal_receipt("r-partial", usage={"input_tokens": 900, "output_tokens": 90}),
    )
    projection = project_run(_load(settings, "r-partial"))
    for row in projection["timeline"]:
        if row["kind"] == "model_request":
            assert row["usage"] is None
    assert projection["usage"]["source"] == "receipt_aggregate"
    assert projection["usage"]["input_tokens"] == 900
    assert projection["usage"]["requests"] == 2


# --- deterministic run inspection ------------------------------------------


def test_inspection_completed_summary_and_artifact_facts(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-inspection", COMPLETED_RUN)
    _write_receipt(
        settings,
        "r-inspection",
        _terminal_receipt(
            "r-inspection",
            artifact_facts=[
                {
                    "path": "artifacts/final.md",
                    "size": 42,
                    "sha256": "a" * 64,
                    "change": "created",
                }
            ],
        ),
    )
    markdown = render_run_markdown("r-inspection", settings=settings)
    data = render_run_json("r-inspection", settings=settings)

    assert "# Run r-inspection" in markdown
    assert "Status: completed" in markdown
    assert "Requests: 1" in markdown
    assert "Tool calls: 1" in markdown
    assert "Input tokens: 500" in markdown
    assert data["summary"]["wall_clock_ms"] == 60_000
    assert data["artifacts"][0]["path"] == "artifacts/final.md"
    assert data["artifacts"][0]["size"] == 42


def test_inspection_rankings_and_contiguous_tools_are_mechanical(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    specs = [
        ("run_started", 0, None, None),
        ("model_request_started", 1, None, None),
        ("tool_call_started", 2, "read-1", "read_material"),
        ("tool_call_completed", 2, "read-1", "read_material"),
        ("tool_call_started", 3, "read-2", "read_material"),
        ("tool_call_completed", 3, "read-2", "read_material"),
        ("model_request_completed", 1, None, None),
        ("model_request_started", 4, None, None),
        ("tool_call_started", 5, "claim-1", "check_claim"),
        ("tool_call_completed", 5, "claim-1", "check_claim"),
        ("model_request_completed", 4, None, None),
        ("model_request_started", 6, None, None),
        ("model_request_completed", 6, None, None),
        ("run_completed", 7, None, None),
    ]
    _seed_sync(tmp_path, settings, "r-ranking", specs)
    asyncio.run(
        _save_snapshot(
            settings,
            _snapshot_with_usage(
                "r-ranking", [(100, 10), (200, 30), (300, 20)]
            ),
        )
    )
    _write_receipt(settings, "r-ranking", _terminal_receipt("r-ranking"))

    data = render_run_json("r-ranking", settings=settings)
    rankings = data["rankings"]
    assert [row["request"] for row in rankings["slowest_requests"][:3]] == [
        "model-request-0",
        "model-request-1",
        "model-request-2",
    ]
    assert [row["request"] for row in rankings["largest_input_requests"][:3]] == [
        "model-request-2",
        "model-request-1",
        "model-request-0",
    ]
    assert [row["request"] for row in rankings["largest_output_requests"][:3]] == [
        "model-request-1",
        "model-request-2",
        "model-request-0",
    ]
    tools = {item["tool"]: item for item in data["tool_activity"]}
    assert tools["read_material"] == {
        "tool": "read_material",
        "total": 2,
        "contiguous_groups": [2],
    }
    assert tools["check_claim"]["total"] == 1


def test_inspection_unknown_usage_is_not_distributed(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "r-partial-inspection",
        [
            ("run_started", 0, None, None),
            ("model_request_started", 1, None, None),
            ("model_request_completed", 1, None, None),
            ("model_request_started", 2, None, None),
            ("model_request_completed", 2, None, None),
            ("run_completed", 3, None, None),
        ],
    )
    asyncio.run(
        _save_snapshot(
            settings,
            _snapshot("r-partial-inspection", responses=1, requests=2),
        )
    )
    _write_receipt(
        settings,
        "r-partial-inspection",
        _terminal_receipt(
            "r-partial-inspection", usage={"input_tokens": 900, "output_tokens": 90}
        ),
    )
    data = render_run_json("r-partial-inspection", settings=settings)
    assert data["summary"]["input_tokens"] == 900
    assert data["summary"]["output_tokens"] == 90
    assert data["summary"]["usage_source"] == "receipt_aggregate"
    assert data["rankings"]["largest_input_requests"] == []
    assert data["rankings"]["largest_output_requests"] == []
    assert "per-request input tokens" in data["unknown_facts"]["unavailable_usage"]
    assert "per-request output tokens" in data["unknown_facts"]["unavailable_usage"]
    markdown = render_run_markdown("r-partial-inspection", settings=settings)
    assert markdown.count("Unavailable: no authoritative per-request input usage.") == 1
    assert markdown.count("Unavailable: no authoritative per-request output usage.") == 1
    assert "| model-request-0 | 1.000s | Unknown | Unknown | completed |" in markdown


def test_inspection_incomplete_request_is_not_running(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "r-incomplete-inspection",
        [
            ("run_started", 0, None, None),
            ("model_request_started", 1, None, None),
        ],
    )
    data = render_run_json("r-incomplete-inspection", settings=settings)
    assert data["summary"]["status"] == "incomplete"
    assert data["unknown_facts"]["incomplete_requests"] == [
        {"request": "model-request-0", "step": 1}
    ]
    assert "running" not in render_run_markdown(
        "r-incomplete-inspection", settings=settings
    ).lower()


def test_inspection_unresolved_tool_is_preserved(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "r-unresolved-inspection",
        [
            ("run_started", 0, None, None),
            ("tool_call_started", 1, "tc-x", "external_write"),
        ],
    )
    _write_receipt(
        settings,
        "r-unresolved-inspection",
        {
            "schema_version": "2.0",
            "state": "paused",
            "run_id": "r-unresolved-inspection",
            "conversation_id": "c1",
            "model": "test-model",
            "started_at": T0.isoformat(),
            "finished_at": (T0 + timedelta(seconds=5)).isoformat(),
            "pending_approvals": [],
            "pending_calls": [],
        },
    )
    data = render_run_json("r-unresolved-inspection", settings=settings)
    assert data["summary"]["status"] == "paused"
    assert data["unknown_facts"]["unresolved_tool_calls"] == [
        {
            "tool_call": "tool-call-0",
            "tool": "external_write",
            "step": 1,
        }
    ]


def test_inspection_large_run_has_bounded_chronology_and_markdown(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    specs: list[tuple[str, int, str | None, str | None]] = [("run_started", 0, None, None)]
    for index in range(100):
        step = index + 1
        specs.extend(
            [
                ("model_request_started", step, None, None),
                ("model_request_completed", step, None, None),
            ]
        )
    specs.append(("run_completed", 101, None, None))
    _seed_sync(tmp_path, settings, "r-large-inspection", specs)
    _write_receipt(settings, "r-large-inspection", _terminal_receipt("r-large-inspection"))

    data = render_run_json(
        "r-large-inspection", settings=settings, chronology_limit=5
    )
    markdown = render_run_markdown(
        "r-large-inspection", settings=settings, chronology_limit=5
    )
    assert len(data["timeline"]) == 5
    assert data["bounds"]["chronology_omitted"] > 0
    assert len(markdown) <= 12_000
    assert "chronology rows omitted" in markdown


def test_inspection_json_and_markdown_share_projection_facts_without_content(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-interoperable", COMPLETED_RUN)
    asyncio.run(
        _save_snapshot(
            settings,
            _snapshot("r-interoperable", responses=1, requests=1),
        )
    )
    _write_receipt(settings, "r-interoperable", _terminal_receipt("r-interoperable"))
    projection = project_run(_load(settings, "r-interoperable"))
    direct = inspect_run(projection)
    json_data = render_run_json("r-interoperable", settings=settings)
    markdown = render_run_markdown("r-interoperable", settings=settings)

    assert json_data == direct
    assert f"Requests: {json_data['summary']['requests']}" in markdown
    assert f"Tool calls: {json_data['summary']['tool_calls']}" in markdown
    assert [
        row["request"] for row in json_data["rankings"]["slowest_requests"]
    ] == [row["request"] for row in direct["rankings"]["slowest_requests"]]
    serialized = json.dumps(json_data)
    assert "q0" not in serialized
    assert "a0" not in serialized
    assert "q0" not in markdown
    assert "a0" not in markdown


def test_inspection_segment_is_step_bounded_and_content_free(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-segment", COMPLETED_RUN)
    projection = project_run(_load(settings, "r-segment"))
    segment = inspect_run_segment(projection, 1, 2)

    assert segment["scope"] == {"start_step": 1, "end_step": 2}
    assert segment["timeline"]
    assert all(
        row["step"] is not None and 1 <= row["step"] <= 2
        for row in segment["timeline"]
    )
    assert all("payload" not in row for row in segment["timeline"])


def test_inspection_segment_markdown_keeps_scope_and_content_gap(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-segment-md", COMPLETED_RUN)
    markdown = render_run_segment_markdown(
        "r-segment-md", 1, 2, settings=settings
    )
    assert "## Scope" in markdown
    assert "Steps: 1–2" in markdown
    assert "Content: unavailable" in markdown
    assert "q0" not in markdown


def test_inspection_legacy_receipt_keeps_events_and_diagnostics(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-legacy-inspection", COMPLETED_RUN)
    _write_receipt(
        settings,
        "r-legacy-inspection",
        {"schema_version": "1.1", "state": "terminal", "run_id": "r-legacy-inspection"},
    )
    data = render_run_json("r-legacy-inspection", settings=settings)
    markdown = render_run_markdown("r-legacy-inspection", settings=settings)
    assert data["summary"]["status"] == "completed"
    assert data["summary"]["requests"] == 1
    assert data["summary"]["tool_calls"] == 1
    assert any(
        "receipt_unavailable" in diagnostic
        for diagnostic in data["unknown_facts"]["diagnostics"]
    )
    assert "receipt_unavailable" in markdown


# --- API surface (read-only) --------------------------------------------------


def _client(settings: AgentSettings) -> TestClient:
    from starlette.applications import Starlette

    app = Starlette(routes=list(api_routes()))
    app.state.settings = settings
    return TestClient(app)


def test_api_list_newest_first_with_cursor(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    for index, run_id in enumerate(("old-run", "mid-run", "new-run")):
        _seed_sync(
            tmp_path,
            settings,
            run_id,
            [("run_started", 0, None, None), ("run_completed", 1, None, None)],
            start=T0 + timedelta(minutes=index),
        )
    with _client(settings) as client:
        first = client.get("/api/runs", params={"limit": 2})
        assert first.status_code == 200
        body = first.json()
        assert [run["run_id"] for run in body["runs"]] == ["new-run", "mid-run"]
        assert body["next_cursor"] == "2"
        second = client.get("/api/runs", params={"limit": 2, "cursor": body["next_cursor"]})
        assert [run["run_id"] for run in second.json()["runs"]] == ["old-run"]
        assert second.json()["next_cursor"] is None

        health = client.get("/api/health")
        assert health.status_code == 200 and health.json()["ok"] is True

        missing = client.get("/api/runs/does-not-exist")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "RUN_NOT_FOUND"

        invalid = client.get("/api/runs/bad%20id")
        assert invalid.status_code == 400
        assert invalid.json()["error"]["code"] == "INVALID_RUN_ID"


def test_api_list_unknown_start_sorts_last(tmp_path: Path) -> None:
    """Regression (real-UI finding): a receipt-only run whose receipt cannot
    be parsed has no start stamp — it must not displace the newest known run
    from the top of the default console selection."""
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "known-run",
        [("run_started", 0, None, None)],
        start=T0,
    )
    _write_receipt(
        settings,
        "legacy-run",
        {"schema_version": "1.1", "state": "terminal", "run_id": "legacy-run"},
    )
    with _client(settings) as client:
        body = client.get("/api/runs").json()
        assert [run["run_id"] for run in body["runs"]] == ["known-run", "legacy-run"]
        assert body["runs"][0]["status"] == "incomplete"
        assert body["runs"][1]["status"] == "unknown"


def test_api_list_detail_consistency(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-consistent", COMPLETED_RUN)
    with _client(settings) as client:
        summary = client.get("/api/runs").json()["runs"][0]
        detail = client.get("/api/runs/r-consistent").json()
    for key in ("status", "request_count", "tool_call_count", "started_at"):
        assert summary[key] == detail["run"][key], key


def test_api_inspection_is_derived_and_content_free(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-api-inspection", COMPLETED_RUN)
    asyncio.run(
        _save_snapshot(
            settings,
            _snapshot("r-api-inspection", responses=1, requests=1),
        )
    )
    _write_receipt(settings, "r-api-inspection", _terminal_receipt("r-api-inspection"))

    with _client(settings) as client:
        response = client.get("/api/runs/r-api-inspection/inspection")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["status"] == "completed"
    assert body["summary"]["requests"] == 1
    assert body["summary"]["tool_calls"] == 1
    assert body["timeline"]
    serialized = json.dumps(body)
    assert "q0" not in serialized
    assert "a0" not in serialized


def test_api_inspection_reuses_run_errors(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with _client(settings) as client:
        missing = client.get("/api/runs/does-not-exist/inspection")
        invalid = client.get("/api/runs/bad%20id/inspection")

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RUN_NOT_FOUND"
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "INVALID_RUN_ID"


def test_api_analysis_is_explicit_async_action_and_readback(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-api-analysis", COMPLETED_RUN)
    monkeypatch.setattr(
        analysis,
        "start_analysis",
        lambda settings, run_id, **kwargs: "analysis-test",
    )
    monkeypatch.setattr(
        analysis,
        "analysis_state",
        lambda settings, run_id: {
            "state": "running",
            "subject_run_id": run_id,
            "analysis_run_id": "analysis-test",
            "artifact_path": "analysis/r-api-analysis/analysis.md",
        },
    )
    with _client(settings) as client:
        started = client.post(
            "/api/runs/r-api-analysis/analysis",
            json={"scope": "full", "agent": True},
        )
        state = client.get("/api/runs/r-api-analysis/analysis")

    assert started.status_code == 202
    assert started.json() == {
        "accepted": True,
        "subject_run_id": "r-api-analysis",
        "analysis_run_id": "analysis-test",
        "artifact_path": "analysis/r-api-analysis/analysis.md",
    }
    assert state.status_code == 200
    assert state.json()["state"] == "running"


def _complete_analysis_presentation(*, observed_facts: str = "") -> str:
    section_2 = (
        f"\n\n## 2. Observed Facts\n{observed_facts}" if observed_facts else ""
    )
    return (
        "## 1. Outcome\nBusiness quality is unknown."
        f"{section_2}\n\n"
        "## 3. Interpretation\nThe observed completion may not establish quality.\n\n"
        "## 4. Causal Hypothesis\nThe primary hypothesis remains unproved.\n\n"
        "## 5. Smallest Next Experiment\nKeep the baseline and vary one input "
        "to distinguish the primary hypothesis from a competing explanation."
    )


def test_analysis_host_facts_replace_model_section_2(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(
        tmp_path,
        settings,
        "abc123",
        [
            ("run_started", 0, None, None),
            ("model_request_started", 1, None, None),
            ("tool_call_started", 2, "inspect-1", "inspect_run_segment"),
            ("tool_call_completed", 2, "inspect-1", "inspect_run_segment"),
            ("model_request_completed", 1, None, None),
            ("run_completed", 3, None, None),
        ],
    )
    _write_receipt(
        settings,
        "abc123",
        _terminal_receipt(
            "abc123",
            usage={"input_tokens": 900, "output_tokens": 1436},
            artifact_facts=[
                {
                    "path": "artifacts/exact-report.md",
                    "size": 81,
                    "sha256": "b" * 64,
                    "change": "created",
                }
            ],
        ),
    )

    rendered = analysis._format_analysis_artifact(
        "abc123",
        "analysis-A",
        _complete_analysis_presentation(
            observed_facts=(
                "Run abc132 used read_run_projection with a ~1500 token limit."
            )
        ),
        _load(settings, "abc123"),
    )

    assert rendered.count("## 2. Observed Facts") == 1
    assert "- Run ID: `abc123`" in rendered
    assert "- Execution state: completed" in rendered
    assert "- Model: test-model" in rendered
    assert "  - output_tokens: 1436" in rendered
    assert "- Tools (1 total, 1 shown, 0 omitted):" in rendered
    assert "`inspect_run_segment`" in rendered
    assert "- Artifacts (1 total, 1 shown, 0 omitted):" in rendered
    assert "`artifacts/exact-report.md`" in rendered
    assert "Configured output limit: unknown" in rendered
    assert "abc132" not in rendered
    assert "read_run_projection" not in rendered
    assert "~1500 token limit" not in rendered
    expected_bodies = {
        "## 1. Outcome": "Business quality is unknown.",
        "## 3. Interpretation": "The observed completion may not establish quality.",
        "## 4. Causal Hypothesis": "The primary hypothesis remains unproved.",
        "## 5. Smallest Next Experiment": "Keep the baseline and vary one input",
    }
    positions = []
    for heading, body in expected_bodies.items():
        position = rendered.index(heading)
        positions.append(position)
        assert rendered.index(body, position) > position
    assert positions == sorted(positions)


def test_analysis_prompt_preserves_unknown_and_hypothesis_discipline() -> None:
    prompt = analysis._analysis_prompt(
        "subject-run",
        intent=None,
        scope="full",
        selected_row_id=None,
    )

    assert "Sections 1, 3, 4, and 5" in prompt
    assert "Host supplies Section 2" in prompt
    instructions = " ".join(analysis.ANALYSIS_INSTRUCTIONS.split())
    assert "Never infer a configured token or output limit" in instructions
    assert "never upgrade a hypothesis to fact" in instructions
    assert "distinguish the primary hypothesis" in instructions


@pytest.mark.parametrize(
    ("prompt", "expected_nested"),
    [
        ("Analyze subject run `nested-C`.\nOperator intent: diagnose", "`nested-C`"),
        ("Analyze another run without the fixed sentence.", "unknown"),
    ],
)
def test_analysis_metadata_distinguishes_nested_subject_roles(
    prompt: str, expected_nested: str
) -> None:
    facts = RunFacts(
        run_id="analysis-B",
        record=None,
        events=(),
        receipt=None,
        snapshot=ContinuableSnapshot(
            run_id="analysis-B",
            step_index=0,
            messages=[ModelRequest(parts=[UserPromptPart(content=prompt)])],
        ),
        tool_effects=(),
    )

    rendered = analysis._format_analysis_artifact(
        "analysis-B",
        "analysis-A",
        _complete_analysis_presentation(),
        facts,
    )

    assert "> Analysis run: `analysis-A`" in rendered
    assert "> Subject run: `analysis-B`" in rendered
    assert "> Subject kind: analysis" in rendered
    assert f"> Nested subject: {expected_nested}" in rendered


def test_analysis_nested_subject_comes_only_from_first_task_prompt() -> None:
    prompts = [
        "Analyze subject run `nested-C`.\nOperator intent: diagnose",
        "Analyze subject run `nested-D`.\nOperator intent: diagnose",
    ]
    facts = RunFacts(
        run_id="analysis-B",
        record=None,
        events=(),
        receipt=None,
        snapshot=ContinuableSnapshot(
            run_id="analysis-B",
            step_index=0,
            messages=[
                ModelRequest(parts=[UserPromptPart(content=prompt)])
                for prompt in prompts
            ],
        ),
        tool_effects=(),
    )

    rendered = analysis._format_analysis_artifact(
        "analysis-B",
        "analysis-A",
        _complete_analysis_presentation(),
        facts,
    )

    assert "> Nested subject: `nested-C`" in rendered


def test_analysis_rejects_required_headings_only_inside_code_fence() -> None:
    facts = RunFacts(
        run_id="subject-run",
        record=None,
        events=(),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )
    fenced = "```markdown\n" + _complete_analysis_presentation() + "\n```"

    with pytest.raises(analysis.AnalysisError) as exc_info:
        analysis._format_analysis_artifact(
            "subject-run", "analysis-A", fenced, facts
        )

    assert exc_info.value.code == "INCOMPLETE_ANALYSIS"


def test_analysis_discards_indented_model_section_2() -> None:
    facts = RunFacts(
        run_id="subject-run",
        record=None,
        events=(),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )
    presentation = _complete_analysis_presentation(
        observed_facts="model-owned false fact"
    ).replace("## 2. Observed Facts", "   ## 2. Observed Facts")

    rendered = analysis._format_analysis_artifact(
        "subject-run", "analysis-A", presentation, facts
    )

    assert rendered.count("## 2. Observed Facts") == 1
    assert "model-owned false fact" not in rendered


def test_analysis_long_fence_is_not_closed_by_shorter_fence() -> None:
    facts = RunFacts(
        run_id="subject-run",
        record=None,
        events=(),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )
    fenced = (
        "````markdown\n"
        "quoted output\n"
        "```\n"
        + _complete_analysis_presentation()
        + "\n````"
    )

    with pytest.raises(analysis.AnalysisError) as exc_info:
        analysis._format_analysis_artifact(
            "subject-run", "analysis-A", fenced, facts
        )

    assert exc_info.value.code == "INCOMPLETE_ANALYSIS"


def test_analysis_observed_facts_render_known_empty_collections() -> None:
    facts = RunFacts(
        run_id="subject-empty",
        record=None,
        events=(),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )

    rendered = analysis_store.render_observed_facts(facts)

    assert "- Execution state: unknown" in rendered
    assert "- Model: unknown" in rendered
    assert "- Tools (0 total, 0 shown, 0 omitted):\n  - none" in rendered
    assert "- Artifacts (0 total, 0 shown, 0 omitted):\n  - none" in rendered
    assert analysis_store._observed_value("") == "unknown"


def test_analysis_observed_facts_bound_details_and_report_omissions(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    tool_specs = [("run_started", 0, None, None)]
    for index in range(125):
        call_id = f"call-{index}"
        tool_name = f"canonical-tool-{index}"
        tool_specs.extend(
            [
                ("tool_call_started", index + 1, call_id, tool_name),
                ("tool_call_completed", index + 1, call_id, tool_name),
            ]
        )
    tool_specs.append(("run_completed", 126, None, None))
    _seed_sync(tmp_path, settings, "subject-large", tool_specs)
    _write_receipt(
        settings,
        "subject-large",
        _terminal_receipt(
            "subject-large",
            artifact_facts=[
                {
                    "path": f"artifacts/item-{index}.md",
                    "size": index,
                    "sha256": f"{index:064x}",
                    "change": "created",
                }
                for index in range(45)
            ],
        ),
    )

    rendered = analysis_store.render_observed_facts(
        _load(settings, "subject-large")
    )

    assert "- Tool calls: 125" in rendered
    assert "- Tools (125 total, 120 shown, 5 omitted):" in rendered
    assert "`canonical-tool-0`" in rendered
    assert "`canonical-tool-124`" not in rendered
    assert "- Artifacts (45 total, 40 shown, 5 omitted):" in rendered
    assert "`artifacts/item-39.md`" in rendered
    assert "`artifacts/item-40.md`" not in rendered


def test_analysis_observed_facts_render_paused_execution_state(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "subject-paused", [("run_started", 0, None, None)])
    _write_receipt(
        settings,
        "subject-paused",
        {
            "schema_version": "2.0",
            "state": "paused",
            "run_id": "subject-paused",
            "conversation_id": "conversation-1",
            "model": "paused-model",
            "started_at": T0.isoformat(),
            "finished_at": (T0 + timedelta(seconds=5)).isoformat(),
            "pending_approvals": [],
            "pending_calls": [],
        },
    )

    rendered = analysis_store.render_observed_facts(
        _load(settings, "subject-paused")
    )

    assert "- Status: paused" in rendered
    assert "- Execution state: paused" in rendered


@pytest.mark.parametrize("heading", analysis._MODEL_SECTION_HEADINGS)
@pytest.mark.parametrize("mode", ["missing", "empty"])
def test_analysis_rejects_each_missing_or_empty_model_section(
    heading: str, mode: str
) -> None:
    presentation = _complete_analysis_presentation()
    body_by_heading = {
        "## 1. Outcome": "Business quality is unknown.",
        "## 3. Interpretation": "The observed completion may not establish quality.",
        "## 4. Causal Hypothesis": "The primary hypothesis remains unproved.",
        "## 5. Smallest Next Experiment": (
            "Keep the baseline and vary one input to distinguish the primary "
            "hypothesis from a competing explanation."
        ),
    }
    if mode == "missing":
        presentation = presentation.replace(f"{heading}\n{body_by_heading[heading]}", "")
    else:
        presentation = presentation.replace(body_by_heading[heading], "")
    facts = RunFacts(
        run_id="subject-run",
        record=None,
        events=(),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )

    with pytest.raises(analysis.AnalysisError) as exc_info:
        analysis._format_analysis_artifact(
            "subject-run", "analysis-A", presentation, facts
        )

    assert exc_info.value.code == "INCOMPLETE_ANALYSIS"


def test_incomplete_analysis_settles_worker_state_as_failed(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    subject_run_id = "subject-incomplete"
    analysis_run_id = "analysis-incomplete"
    facts = RunFacts(
        run_id=subject_run_id,
        record=None,
        events=(),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )

    async def fake_load_run_facts(settings, run_id):
        return facts

    monkeypatch.setattr(analysis.readers, "load_run_facts", fake_load_run_facts)
    monkeypatch.setattr(analysis, "export_projection", lambda settings, facts: {})
    monkeypatch.setattr(analysis, "build_agent", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        analysis,
        "execute_run",
        lambda *args, **kwargs: SimpleNamespace(
            receipt=SimpleNamespace(execution_state="completed", error=None),
            presentation=(
                "## 1. Outcome\nunknown\n\n"
                "## 3. Interpretation\nunknown\n\n"
                "## 4. Causal Hypothesis\nunproved"
            ),
        ),
    )
    with analysis._lock:
        analysis._in_flight[subject_run_id] = analysis_run_id
        analysis._results.pop(subject_run_id, None)

    analysis._run_analysis(
        settings,
        subject_run_id,
        analysis_run_id,
        None,
        "full",
        None,
    )
    state = analysis.analysis_state(settings, subject_run_id)

    assert state["state"] == "failed"
    assert "Smallest Next Experiment" in state["error"]
    assert not analysis.analysis_path(settings, subject_run_id).exists()
    with analysis._lock:
        analysis._results.pop(subject_run_id, None)


def test_complete_analysis_settles_worker_and_reads_back_artifact(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    subject_run_id = "subject-complete"
    analysis_run_id = "analysis-complete"
    _seed_sync(tmp_path, settings, subject_run_id, COMPLETED_RUN)
    _write_receipt(settings, subject_run_id, _terminal_receipt(subject_run_id))
    monkeypatch.setattr(analysis, "build_agent", lambda *args, **kwargs: object())
    monkeypatch.setattr(
        analysis,
        "execute_run",
        lambda *args, **kwargs: SimpleNamespace(
            receipt=SimpleNamespace(execution_state="completed", error=None),
            presentation=_complete_analysis_presentation(),
        ),
    )
    with analysis._lock:
        analysis._in_flight[subject_run_id] = analysis_run_id
        analysis._results.pop(subject_run_id, None)

    analysis._run_analysis(
        settings,
        subject_run_id,
        analysis_run_id,
        None,
        "full",
        None,
    )
    state = analysis.analysis_state(settings, subject_run_id)
    artifact = analysis.analysis_path(settings, subject_run_id)

    assert state["state"] == "completed"
    assert state["analysis_run_id"] == analysis_run_id
    assert state["content"] == artifact.read_text(encoding="utf-8")
    assert "# Run Analysis — subject-complete" in state["content"]
    assert "## 5. Smallest Next Experiment" in state["content"]
    with analysis._lock:
        analysis._results.pop(subject_run_id, None)


def test_analysis_artifact_never_overwrites_existing_file(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    path = analysis.analysis_path(settings, "r-existing-analysis")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("human note", encoding="utf-8")

    with pytest.raises(analysis.AnalysisError) as exc_info:
        analysis.start_analysis(settings, "r-existing-analysis")

    assert exc_info.value.code == "ANALYSIS_EXISTS"
    assert path.read_text(encoding="utf-8") == "human note"


def test_analysis_toolset_exposes_only_bound_read_tools(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    toolset = analysis.make_inspection_toolset(settings, "subject-run")
    assert list(toolset.tools) == ["inspect_run", "read_run_projection"]


def test_analysis_toolset_reuses_bound_facts_without_reloading(
    tmp_path: Path, monkeypatch
) -> None:
    settings = _settings(tmp_path)
    facts = RunFacts(
        run_id="subject-bound",
        record=None,
        events=(),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )

    async def fail_reload(settings, run_id):
        raise AssertionError("bound inspection unexpectedly reloaded facts")

    monkeypatch.setattr(analysis.readers, "load_run_facts", fail_reload)
    toolset = analysis.make_inspection_toolset(
        settings,
        "subject-bound",
        bound_facts=facts,
    )

    summary = asyncio.run(toolset.tools["inspect_run"].function(None))
    chunk = asyncio.run(
        toolset.tools["read_run_projection"].function(
            None,
            section="run_id",
        )
    )

    assert "# Run subject-bound" in summary
    assert json.loads(chunk)["content"] == "subject-bound"


def test_analysis_projection_export_preserves_human_owned_files(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    facts = RunFacts(
        run_id="r-export",
        record=None,
        events=(),
        receipt=None,
        snapshot=None,
        tool_effects=(),
    )

    paths = analysis_store.export_projection(settings, facts)
    notes = paths["projection_md"].parent / "operator-notes.md"
    analysis_md = paths["projection_md"].parent / "analysis.md"
    notes.write_text("human decision", encoding="utf-8")
    analysis_md.write_text("human analysis", encoding="utf-8")

    analysis_store.export_projection(settings, facts)

    assert paths["projection_md"].exists()
    assert paths["projection_json"].exists()
    assert notes.read_text(encoding="utf-8") == "human decision"
    assert analysis_md.read_text(encoding="utf-8") == "human analysis"


# --- T008C: SSE run_changed invalidation --------------------------------------


async def _pull(gen, count: int, timeout: float = 2.0) -> list[str]:
    """Pull ``count`` frames inside the caller's loop (per-frame timeout)."""
    frames: list[str] = []
    for _ in range(count):
        frames.append(await asyncio.wait_for(gen.__anext__(), timeout))
    return frames


def test_run_revision_tracks_events_and_receipt(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    assert asyncio.run(readers.run_revision(settings, "r-rev")) is None

    _seed_sync(tmp_path, settings, "r-rev", [("run_started", 0, None, None)])
    with_events = asyncio.run(readers.run_revision(settings, "r-rev"))
    assert with_events is not None and with_events.startswith("events=1;")

    _write_receipt(settings, "r-rev", {"schema_version": "2.0"})
    with_receipt = asyncio.run(readers.run_revision(settings, "r-rev"))
    assert with_receipt != with_events


def test_sse_stream_emits_on_subscribe_and_change(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-live", [("run_started", 0, None, None)])

    async def scenario() -> tuple[str, str]:
        gen = sse.run_changed_stream(settings, "r-live", poll_interval=0.02)
        try:
            first = (await _pull(gen, 1))[0]
            store = FileStepStore(settings.step_store_dir)
            await store.append_event(
                StepEvent(
                    run_id="r-live",
                    kind="run_completed",
                    step_index=1,
                    timestamp=T0 + timedelta(seconds=5),
                )
            )
            second = (await _pull(gen, 1))[0]
            return first, second
        finally:
            await gen.aclose()

    first, second = asyncio.run(scenario())
    assert first.startswith("event: run_changed\n")
    assert '"run_id": "r-live"' in first
    assert second.startswith("event: run_changed\n")
    assert second != first


def test_sse_stream_heartbeat_when_quiet(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-quiet", [("run_started", 0, None, None)])

    async def scenario() -> list[str]:
        gen = sse.run_changed_stream(
            settings, "r-quiet", poll_interval=0.02, heartbeat_seconds=0.05
        )
        try:
            return await _pull(gen, 2)
        finally:
            await gen.aclose()

    frames = asyncio.run(scenario())
    assert frames[0].startswith("event: run_changed\n")
    assert frames[1] == ": ping\n\n"


def test_sse_stream_ends_when_facts_vanish(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_receipt(settings, "r-gone", {"schema_version": "2.0"})

    async def scenario() -> tuple[str, str, bool]:
        gen = sse.run_changed_stream(settings, "r-gone", poll_interval=0.02)
        try:
            first = (await _pull(gen, 1))[0]
            (settings.state_root / "receipts" / "r-gone.json").unlink()
            final = (await _pull(gen, 1))[0]
            stopped = False
            try:
                await asyncio.wait_for(gen.__anext__(), 1.0)
            except StopAsyncIteration:
                stopped = True
            return first, final, stopped
        finally:
            await gen.aclose()

    first, final, stopped = asyncio.run(scenario())
    assert first.startswith("event: run_changed\n")
    assert '"revision": null' in final
    assert stopped, "stream must end after the run's facts disappear"


def test_api_events_route_rejects_unknown_and_invalid(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    with _client(settings) as client:
        missing = client.get("/api/runs/does-not-exist/events")
        assert missing.status_code == 404
        assert missing.json()["error"]["code"] == "RUN_NOT_FOUND"

        invalid = client.get("/api/runs/bad%20id/events")
        assert invalid.status_code == 400
        assert invalid.json()["error"]["code"] == "INVALID_RUN_ID"
