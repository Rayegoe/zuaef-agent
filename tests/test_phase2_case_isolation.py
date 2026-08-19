"""Bound-Case isolation — SPEC v1.0 §5.6 (P2-3).

When a run's CoreDeps is bound to a Case, every real zuaef-case tool must
reject any operation targeting a different Case — a business authorization
boundary, not prompt guidance. Cross-case access fails the run loudly
(host-enforced, never a model-choice); unbound CLI/test runs keep the legacy
behavior (any case the caller names).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / "src"), str(REPO / "plugins" / "zuaef-case")]

from zuaef_case.models import CaseDoc, CaseError
from zuaef_case.store import CaseStore
from zuaef_case.toolset import build_case_toolset

from zuaef_agent.models import CoreDeps


@pytest.fixture
def cases(tmp_path: Path) -> tuple[CaseStore, str, str]:
    store = CaseStore(tmp_path / "cases")
    for case_id, goal in (
        ("stillevo-beauty", "给云朵美妆现场写一篇 demo 文章"),
        ("other-case", "其他客户的无关任务"),
    ):
        store.create_case(
            CaseDoc(case_id=case_id, goal=goal, stakeholders={"customer": "c"})
        )
    return store, "stillevo-beauty", "other-case"


def _agent(store: CaseStore) -> Agent:
    return Agent(
        "test",
        deps_type=CoreDeps,
        output_type=[str],
        toolsets=[build_case_toolset(store)],
    )


def _run(agent: Agent, sequence: list[tuple[str, dict]], case_id: str | None):
    """Run a scripted model through one tool call then final; a cross-case
    access surfaces as a raised CaseError, which the runtime would settle as
    a blocked receipt."""
    seq = list(sequence)
    raised: list[CaseError] = []

    async def handler(messages, info):
        if seq:
            name, args = seq.pop(0)
            return ModelResponse(parts=[ToolCallPart(name, args)])
        return ModelResponse(
            parts=[
                TextPart(content="done")
            ]
        )

    deps = CoreDeps(
        workspace_root=Path("/tmp/unused-workspace"),
        run_id="r-isolation",
        case_id=case_id,
    )
    with agent.override(model=FunctionModel(handler)):
        try:
            asyncio.run(agent.run("proceed", deps=deps))
        except CaseError as exc:
            raised.append(exc)
    return raised


def _bound_run(store: CaseStore, bound: str, other: str, tool: str, args: dict):
    errors = _run(_agent(store), [(tool, args)], bound)
    assert len(errors) == 1
    assert "not the bound case" in str(errors[0])
    return errors[0]


def test_bound_run_rejects_reading_another_case(cases):
    store, bound, other = cases
    _bound_run(
        store, bound, other,
        "load_case_context",
        {"case_id": other, "limit": 5},
    )


def test_bound_run_reads_own_case(cases):
    store, bound, _ = cases
    errors = _run(
        _agent(store),
        [("load_case_context", {"case_id": bound, "limit": 5})],
        bound,
    )
    assert errors == []


def test_bound_run_rejects_all_cross_case_operations(cases):
    store, bound, other = cases
    cases_to_fail = (
        ("save_draft", {"case_id": other, "text": "leak"}),
        ("update_situation", {"case_id": other, "delta": {"customer": {"company": "x"}}}),
        ("record_case_step", {"case_id": other, "kind": "action", "summary": "x"}),
        ("load_case_context", {"case_id": other, "limit": 5}),
    )
    for tool, args in cases_to_fail:
        _bound_run(store, bound, other, tool, args)


def test_bound_run_cross_case_send_is_blocked_not_paused(cases, tmp_path):
    """``send_to_customer`` is approval-gated, so the framework pauses BEFORE
    the tool body runs; the RUNTIME's pause frontier re-checks Case isolation
    and turns a cross-case send into a blocked receipt instead of an operator
    queue entry (SPEC v1.0 §5.6)."""
    from uuid import uuid4

    from zuaef_agent.config import AgentSettings
    from zuaef_agent.core import build_agent
    from zuaef_agent.runtime import PausedRun, execute_run

    store, bound, other = cases
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    settings = AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    # ensure a draft exists on the OTHER case so only the guard can stop the send
    store.write_draft(other, "draft text")

    run_id = uuid4().hex

    async def handler(messages, info):
        return ModelResponse(
            parts=[ToolCallPart("send_to_customer", {"case_id": other, "draft_ref": "msg-001.md"})]
        )

    agent = build_agent(
        settings,
        run_id=run_id,
        extra_toolsets=[build_case_toolset(store)],
    )
    deps = CoreDeps(
        workspace_root=workspace.resolve(),
        run_id=run_id,
        case_id=bound,
    )
    with agent.override(model=FunctionModel(handler)):
        outcome = execute_run(
            agent, deps, prompt="send it", settings=settings, run_id=run_id
        )
    assert not isinstance(outcome, PausedRun)
    assert outcome.receipt.status == "blocked"
    assert "isolated to the bound Case" in (outcome.receipt.error or "")
    assert outcome.receipt.case_id == bound


def test_bound_run_own_case_send_pauses_for_approval(cases, tmp_path):
    from uuid import uuid4

    from zuaef_agent.config import AgentSettings
    from zuaef_agent.core import build_agent
    from zuaef_agent.runtime import PausedRun, execute_run

    store, bound, _ = cases
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    settings = AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )
    store.write_draft(bound, "draft text")
    run_id = uuid4().hex

    async def handler(messages, info):
        return ModelResponse(
            parts=[ToolCallPart("send_to_customer", {"case_id": bound, "draft_ref": "msg-001.md"})]
        )

    agent = build_agent(
        settings,
        run_id=run_id,
        extra_toolsets=[build_case_toolset(store)],
    )
    deps = CoreDeps(
        workspace_root=workspace.resolve(),
        run_id=run_id,
        case_id=bound,
    )
    with agent.override(model=FunctionModel(handler)):
        outcome = execute_run(
            agent, deps, prompt="send it", settings=settings, run_id=run_id
        )
    assert isinstance(outcome, PausedRun)
    assert outcome.pause_receipt.case_id == bound
    assert [c["tool_name"] for c in outcome.pause_receipt.pending_approvals] == [
        "send_to_customer"
    ]


def test_unbound_run_keeps_legacy_behavior(cases):
    """No bound case (CLI direct runs) keeps the historical contract: the
    caller names the Case explicitly."""
    store, bound, _ = cases
    errors = _run(
        _agent(store),
        [("load_case_context", {"case_id": bound, "limit": 5})],
        None,
    )
    assert errors == []