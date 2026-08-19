"""Memory & conversation-recall baseline — TASKS T009.

The generic Harness Memory and ConversationSearch capabilities are wired and
kept strictly separate from ZUAEF Case and evidence-backed Knowledge:

- Memory can persist/retrieve a non-evidentiary note (its own store under the
  runtime state root, never under ``knowledge/**``).
- ConversationSearch can retrieve prior conversation material from persisted
  step snapshots.
- Knowledge provenance and Case state are untouched: a memory/recall session
  neither creates nor mutates evidence-backed knowledge or case files.

Deterministic FunctionModel scripts; no model request, no network.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel
from pydantic_ai_harness.step_persistence import (
    ContinuableSnapshot,
    FileStepStore,
    RunRecord,
)

from zuaef_agent.config import AgentSettings
from zuaef_agent.core import build_agent

UNIQUE_PHRASE = "golden-ostrich-evidence-77"


def _settings(tmp_path: Path, **cap_flags) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_knowledge=False,
        enable_skills=False,
        **cap_flags,
    )


def _run_script_recording(agent: Agent, sequence: list[tuple[str, dict]]) -> dict[str, str]:
    """Run ``agent`` with a scripted model calling each (tool, args) then
    ``final_result``; return the last tool-return content observed after each
    scripted call (keyed ``after_step_{n}``)."""
    returns_by_step: dict[str, str] = {}
    cursor = {"step": 0}
    seq = list(sequence)

    async def handler(messages, info):
        returns_now = [
            p
            for m in messages
            for p in getattr(m, "parts", [])
            if getattr(p, "part_kind", None) == "tool-return"
        ]
        if seq:
            name, args = seq.pop(0)
            cursor["step"] += 1
            # the return observed for an earlier step is the latest so far
            if returns_now:
                latest = str(getattr(returns_now[-1], "content", "") or "")
                returns_by_step[f"after_step_{cursor['step'] - 1}"] = latest
            return ModelResponse(parts=[ToolCallPart(name, args)])
        if returns_now:
            returns_by_step["after_step_" + str(cursor["step"])] = str(
                getattr(returns_now[-1], "content", "") or ""
            )
        return ModelResponse(
            parts=[TextPart(content="done")]
        )

    with agent.override(model=FunctionModel(handler)):
        asyncio.run(agent.run("proceed"))
    return returns_by_step


def _seed_prior_snapshot(step_store_dir: Path, *, run_id: str, conversation_id: str) -> None:
    store = FileStepStore(step_store_dir)
    asyncio.run(
        store.register_run(
            RunRecord(run_id=run_id, conversation_id=conversation_id, agent_name="zuaef")
        )
    )
    asyncio.run(
        store.save_snapshot(
            ContinuableSnapshot(
                run_id=run_id,
                step_index=0,
                agent_name="zuaef",
                state="complete",
                messages=[
                    ModelRequest(
                        [
                            UserPromptPart(
                                "客户的代号是 golden-ostrich-evidence-77，背景材料在材料包。"
                            )
                        ]
                    )
                ],
            )
        )
    )


def test_memory_persists_and_retrieves_non_evidentiary_note(tmp_path):
    """Memory persist + retrieve a plain note, in its own store under state."""
    agent = build_agent(_settings(tmp_path, enable_memory=True))
    note = "项目代号 aurora9x（非证据性备注，客户偏好随和）"
    returns = _run_script_recording(
        agent,
        sequence=[
            ("write_memory", {"content": note}),
            ("search_memory", {"query": "aurora9x"}),
        ],
    )
    search_return = returns.get("after_step_2", "")
    assert "aurora9x" in search_return, search_return

    # The note persisted into the Memory store (runtime state), not knowledge/**.
    memory_root = tmp_path / ".zuaef-state" / "memory"
    assert memory_root.is_dir()
    assert any(memory_root.rglob("*.md")), list(memory_root.rglob("*.md"))[:5]


def test_conversation_search_retrieves_prior_material(tmp_path):
    """ConversationSearch recovers material from an earlier persisted run."""
    state = tmp_path / ".zuaef-state"
    _seed_prior_snapshot(state / "steps", run_id="prior-run", conversation_id="conv-1")
    agent = build_agent(
        _settings(tmp_path, enable_conversation_search=True, enable_step_persistence=True)
    )
    returns = _run_script_recording(
        agent,
        sequence=[("search_conversation_history", {"query": "golden-ostrich-evidence-77"})],
    )
    content = returns.get("after_step_1", "")
    assert UNIQUE_PHRASE in content, content
    assert "prior-run" in content, content


def test_memory_and_recall_leave_knowledge_and_case_untouched(tmp_path):
    """Memory + conversation recall do not create/mutate Knowledge or Case."""
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    # A pre-existing evidence-backed knowledge node (provenance intact).
    knowledge_dir = workspace / "knowledge" / "concepts"
    knowledge_dir.mkdir(parents=True)
    knowledge_file = knowledge_dir / "client.md"
    knowledge_before = "---\ntype: concept\ntitle: Client\nsources: []\ngenerated:\n  run_id: prior\n---\nbody\n"
    knowledge_file.write_text(knowledge_before, encoding="utf-8")

    # A pre-existing Case control file (bytes must not change).
    case_dir = workspace / "cases" / "c1"
    case_dir.mkdir(parents=True)
    case_file = case_dir / "case.md"
    case_before = "# Case c1\n客户背景简述。\n"
    case_file.write_text(case_before, encoding="utf-8")

    _seed_prior_snapshot(tmp_path / ".zuaef-state" / "steps", run_id="prior-run", conversation_id="conv-1")
    agent = build_agent(
        _settings(
            tmp_path,
            enable_memory=True,
            enable_conversation_search=True,
            enable_step_persistence=True,
        )
    )
    _run_script_recording(
        agent,
        sequence=[
            ("write_memory", {"content": "非证据性备注"}),
            ("search_conversation_history", {"query": UNIQUE_PHRASE}),
        ],
    )

    assert knowledge_file.read_text(encoding="utf-8") == knowledge_before
    assert case_file.read_text(encoding="utf-8") == case_before
