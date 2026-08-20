"""Case toolset tests — SPEC v0.3 FDE Platform Stage 2 gate, P3B-3 T008.

Unit coverage of the two toolsets (Case state / customer delivery) over a
real CaseStore, plus the native approval proof: send_to_customer must pause
before any execution.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic_ai import RunContext, RunUsage, models
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from zuaef_case.models import CaseDoc, TrajectoryEntry
from zuaef_case.store import CaseStore
from zuaef_case.toolset import (
    _CaseTools,
    build_case_state_toolset,
    build_customer_delivery_toolset,
)

from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import PausedRun, TerminalRun, execute_run

models.ALLOW_MODEL_REQUESTS = False


@pytest.fixture
def store(tmp_path: Path) -> CaseStore:
    root = tmp_path / "workspace" / "cases"
    store = CaseStore(root)
    store.create_case(
        CaseDoc(
            case_id="beauty-003",
            goal="证明能改善客户内容同质化问题并推进至付费 Pilot。",
            supervisor_chat_id="111",
            customer_chat_id="222",
        )
    )
    return store


def _tool_names(toolset) -> set[str]:
    ctx = RunContext(
        deps=CoreDeps(workspace_root=Path("/tmp"), run_id=""),
        usage=RunUsage(),
        prompt="",
        model=None,
    )
    return set(asyncio.run(toolset.get_tools(ctx)))


def _settings(tmp_path: Path) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )


def test_state_toolset_exposes_exact_tool_names(store: CaseStore):
    assert _tool_names(build_case_state_toolset(store)) == {
        "load_case_context",
        "update_situation",
        "record_case_step",
    }


def test_delivery_toolset_exposes_exact_tool_names(store: CaseStore):
    assert _tool_names(build_customer_delivery_toolset(store)) == {
        "save_draft",
        "send_to_customer",
    }


def test_state_toolset_carries_no_delivery_affordance(store: CaseStore):
    """P3B-3 T008: the state toolset's instructions must not prime outbound
    delivery — save_draft/send_to_customer semantics live in the delivery
    toolset's tool docstrings only, and the delivery toolset itself carries
    no toolset-level instructions (those inject even while deferred)."""
    state = build_case_state_toolset(store)
    state_instructions = asyncio.run(state.get_instructions(None))
    assert "send_to_customer" not in state_instructions
    assert "save_draft" not in state_instructions
    delivery = build_customer_delivery_toolset(store)
    assert not asyncio.run(delivery.get_instructions(None))


# ── tool behavior via the logic holder (no ctx needed) ──────────────────────


def test_load_case_context_bounds_and_assembles(store: CaseStore):
    store.append_trajectory_for_case(
        "beauty-003",
        TrajectoryEntry(
            kind="event", role="customer", summary="客户发来问题稿"
        ),
    )
    tools = _CaseTools(store)
    context = tools.load_case_context("beauty-003", limit=10, include_trajectory=False)
    assert context["case_id"] == "beauty-003"
    assert "Pilot" in context["goal"]
    assert context["policy_overrides"] == ""
    # P3B-3 T005: operational history is NOT mixed into normal Case context —
    # trajectory appears only on the explicit include_trajectory request.
    assert "trajectory_tail" not in context
    explicit = tools.load_case_context("beauty-003", limit=10, include_trajectory=True)
    assert explicit["trajectory_tail"][0]["summary"] == "客户发来问题稿"


def test_update_situation_merges_with_provenance(store: CaseStore):
    tools = _CaseTools(store)
    tools.update_situation(
        "beauty-003", "r1", {"customer": {"authority": "unknown"}}, None, None
    )
    tools.update_situation(
        "beauty-003",
        "r2",
        {"problem": {"template_similarity": "confirmed"}},
        ["EVD-G-1"],
        None,
    )
    situation = store.read_situation("beauty-003")
    assert situation.state["customer"]["authority"] == "unknown"
    assert situation.state["problem"]["template_similarity"] == "confirmed"
    assert situation.evidence_ids == ["EVD-G-1"]
    assert situation.updated_by == "run:r2"


def test_update_situation_refuses_unprovenanced_facts(store: CaseStore):
    tools = _CaseTools(store)
    with pytest.raises(RuntimeError, match="provenance"):
        tools.update_situation(
            "beauty-003",
            "r1",
            {"customer": {"confidence": "medium"}},
            None,
            None,
        )


def test_update_situation_barry_override_writes(store: CaseStore):
    tools = _CaseTools(store)
    tools.update_situation(
        "beauty-003",
        "r1",
        {"commercial": {"stage": "solution_validation"}},
        None,
        "先验证价值再资格审定",
    )
    situation = store.read_situation("beauty-003")
    assert situation.barry_override == "先验证价值再资格审定"
    assert situation.updated_by == "barry"


def test_record_case_step_appends_with_run_id(store: CaseStore):
    tools = _CaseTools(store)
    entry = tools.record_case_step(
        "beauty-003", "r9", "decision", "先做现场 demo 而非换模型", {}
    )
    assert entry["seq"] == 1
    assert entry["run_id"] == "r9"
    assert entry["kind"] == "decision"


def test_save_draft_and_send_roundtrip(store: CaseStore):
    tools = _CaseTools(store)
    saved = tools.save_draft("beauty-003", "您好，这是第一版现场 demo。")
    assert saved["draft_ref"] == "msg-001.md"

    result = tools.send_to_customer("beauty-003", "msg-001.md")
    assert "第一版现场 demo" in result["text"]
    assert result["case_id"] == "beauty-003"


def test_send_to_customer_rejects_unknown_or_traversal_refs(store: CaseStore):
    tools = _CaseTools(store)
    tools.save_draft("beauty-003", "内容")
    with pytest.raises(FileNotFoundError):
        tools.send_to_customer("beauty-003", "msg-999.md")
    with pytest.raises(ValueError):
        tools.send_to_customer("beauty-003", "../case.md")


# ── native approval proof ───────────────────────────────────────────────────


def test_send_to_customer_pauses_for_approval(tmp_path: Path):
    """Native approval proof through the REAL installed `case` entry point:
    profile → build_profile_agent → pause → shared resume → tool settles.
    The draft file persists on disk, so the resumed agent (rebuilt from the
    frozen snapshot) resolves the same draft."""
    from zuaef_agent.composition import build_profile_agent
    from zuaef_agent.continuation import resume_paused_run

    settings = _settings(tmp_path)
    store = CaseStore(settings.workspace_root / "cases")
    store.create_case(
        CaseDoc(
            case_id="beauty-003",
            goal="推进 Pilot",
            supervisor_chat_id="111",
            customer_chat_id="222",
        )
    )
    store.write_draft("beauty-003", "您好，这是要发给客户的草稿。")

    config_root = tmp_path / "config"
    (config_root / "profiles").mkdir(parents=True)
    (config_root / "profiles" / "fde-test.toml").write_text(
        'schema = 1\nname = "fde-test"\n\n[[plugins]]\nid = "case"\n',
        encoding="utf-8",
    )

    run_id = uuid4().hex
    agent, snapshot = build_profile_agent(
        settings,
        run_id=run_id,
        profile="fde-test",
        config_root=config_root,
    )
    deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

    def fn(messages, info):
        has_return = any(
            getattr(part, "part_kind", None) == "tool-return"
            for message in messages
            for part in getattr(message, "parts", [])
        )
        if not has_return:
            return ModelResponse(
                parts=[
                    ToolCallPart(
                        "send_to_customer",
                        {"case_id": "beauty-003", "draft_ref": "msg-001.md"},
                    )
                ]
            )
        return ModelResponse(
            parts=[
                ToolCallPart(
                    "final_result",
                    {"status": "completed", "outcome": "sent", "artifacts": [], "evidence": []},
                )
            ]
        )

    with agent.override(model=FunctionModel(fn)):
        outcome = execute_run(
            agent,
            deps,
            prompt="发给客户",
            settings=settings,
            run_id=run_id,
            composition=snapshot,
        )

    assert isinstance(outcome, PausedRun)
    assert outcome.pause_receipt.pending_approvals[0]["tool_name"] == "send_to_customer"

    terminal = resume_paused_run(settings, run_id, decision="approve")
    assert isinstance(terminal, TerminalRun)
    settled = [
        e for e in terminal.receipt.verified_tool_effects
        if e.tool_name == "send_to_customer"
    ]
    assert settled and settled[0].status == "completed"
