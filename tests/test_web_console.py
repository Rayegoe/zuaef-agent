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
from zuaef_agent.web.api import api_routes
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


def test_api_list_detail_consistency(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _seed_sync(tmp_path, settings, "r-consistent", COMPLETED_RUN)
    with _client(settings) as client:
        summary = client.get("/api/runs").json()["runs"][0]
        detail = client.get("/api/runs/r-consistent").json()
    for key in ("status", "request_count", "tool_call_count", "started_at"):
        assert summary[key] == detail["run"][key], key
