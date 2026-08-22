"""Editorial control capability tests — SPEC ``zuaef-editorial-control-v0.1``.

Since v1.2 T014B the capability is BENCHMARK/LEGACY code living in
``benchmarks/editorial-learning/legacy/editorial_capability.py``; the
production plugin rejects ``editorial_*`` config (Gate A below). The remaining
tests pin the legacy module's machine-checkable behavior for the benchmark
experiments that still exercise it:

- Gate A (no regression): production surface unchanged, editorial config
  rejected loudly.
- Gate B (bounded control): intervention cap, save-veto cap, identical-draft
  never rejected twice.
- Gate C (provenance): every semantic intervention cites EditorialEvidence ids.
- Gate D (human ownership): no tool for approving/persisting evidence; the
  evidence file is read-only at runtime.

Gates E/F (blind human A/B evaluation; learning proof from ≥30 human patches)
are operational gates, not code — see the WO receipt and registered debt.
"""

from __future__ import annotations

import asyncio
import json
from importlib.metadata import EntryPoint
from pathlib import Path

import pytest
from editorial_capability import (
    COGNITIVE_ACTIONS,
    EditorialControlCapability,
    EditorialEvidenceStore,
    EditorialSettings,
)
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.exceptions import ModelRetry
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models import ModelRequestContext
from pydantic_ai.tools import ToolDefinition
from zuaef_ace_writing import create_plugin

from zuaef_agent.composition import build_agent_from_snapshot
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import (
    CompositionError,
    PluginBundle,
    PluginEnv,
    PluginRef,
)

# Two calibrated long-form drafts (see sensor constants in editorial.py):
# templated trips several sensors (drift 4.771 > 1.50); grounded carries one
# weak signal only (drift 0.731 < 1.50).
TEMPLATED_DRAFT = """\
首先，我们必须认识到，这个问题的意义在于它揭示了当今社会的一种普遍现象。值得注意的是，这种现象的背后隐藏着深层次的价值取向问题。与此同时，它也反映了整个社会体系在发展过程中所面临的结构性挑战。

其次，从更宏观的角度来看，这个问题的影响已经超出了它本身的范围。不仅如此，它还与当下的文化模式之间存在着复杂的互动关系。本质上，这说明我们的社会机制正在经历一场深刻的转型。由此可见，这一趋势值得我们认真对待。

再次，这一现象的意义还体现在它与个体价值的关系上。与此同时，我们也可以看到，这种发展趋势对社会结构产生了重要的影响。换句话说，这一问题的本质是一个关于体系与模式之间关系的问题。可以说，它揭示了当代社会的一个核心现象。

然后，从历史的维度来看，这个问题的发展脉络也体现了类似的现象。值得注意的是，历史的经验告诉我们，任何一种社会现象的出现都有其深层的背景因素。与此同时，我们也应当看到，这种历史趋势与现实问题之间存在着紧密的内在关系。

此外，这一问题的另一个重要层面在于它与文化价值之间的关联。不仅如此，这种关联本身也构成了一种值得研究的现象。换句话说，从这个角度出发，我们可以更清楚地认识这一问题的意义与价值。

最后，综上所述，这个问题的价值在于它促使我们重新思考发展的意义。值得注意的是，这种思考本身也是一种重要的社会现象。归根结底，这表明我们对这一问题的理解还需要进一步深化。总之，这一趋势的影响将会持续显现。"""

GROUNDED_DRAFT = """\
老陈把最后一箱车架搬进仓库的时候，天已经黑了。这是 2024 年 3 月的第 14 个工作日，他的手上还留着上午装配时划开的口子。仓库的卷帘门坏了一半，只能开到两米高，进出都得弯腰。

车间里堆着 327 个待检的车架，其中 61 个要赶在周五之前发往杭州。质检员小刘拿着卡尺挨个量头管口径，量到第 40 个的时候她停了下来。「这批的内径偏了 0.2 毫米，」她在记录本上写下数字，「得返工。」她把这行字圈了两遍。

老陈蹲在货架边上抽了半根烟。厂里给他的交期是 4 月 10 日，罚款条款写在合同第 8 条：每延误一天，扣合同金额的百分之三。他算过，这批货值 46 万，拖一周就是将近一万块，够付两个学徒一个月的工资。

晚上九点，返工的名单发到了群里，一共 17 个人。小刘在名单末尾加了一句话：「明天早到半小时，先量后装。」没有人回复，但第二天早上七点二十，车间里的灯是亮的，砂轮机响起来的时候，门口的水泥地上还结着霜。

返工到第三天，供应商的王经理来了一趟车间。他看了小刘的记录本，翻到画圈的那页，拍了拍老陈的肩膀：「模具是我们的事，这批的费用我们来担。」老陈没说话，把烟掐了，回身去搬下一箱车架。那天晚上发货单打印出来的时候，离交期还有六天。"""

WRITING_TOOLS = {
    "pull_context",
    "save_article",
}


def _env(tmp_path: Path) -> PluginEnv:
    return PluginEnv(
        plugin_id="ace-writing",
        plugin_version="0.2.0",
        workspace_root=tmp_path / "workspace",
        state_root=tmp_path / "state",
    )


def _fake_ace_root(tmp_path: Path) -> Path:
    ace = tmp_path / "ace"
    (ace / "tools").mkdir(parents=True, exist_ok=True)
    (ace / "tools" / "ctx.py").write_text("", encoding="utf-8")
    return ace


def _bundle(tmp_path: Path, config: dict | None = None) -> PluginBundle:
    cfg = {"ace_root": str(_fake_ace_root(tmp_path))}
    if config:
        cfg.update(config)
    return create_plugin(_env(tmp_path), cfg)


def _capability(settings: EditorialSettings | None = None, store: EditorialEvidenceStore | None = None) -> EditorialControlCapability:
    return EditorialControlCapability(
        settings=settings or EditorialSettings(),
        store=store if store is not None else EditorialEvidenceStore(),
    )


def _ctx(tmp_path: Path) -> RunContext[CoreDeps]:
    deps = CoreDeps(workspace_root=tmp_path, run_id="r1")
    return RunContext(deps=deps, usage=RunUsage(), prompt="", model=None)


def _request_context() -> ModelRequestContext:
    return ModelRequestContext(
        model=None, messages=[], model_settings=None, model_request_parameters=None
    )


def _response(text: str) -> ModelResponse:
    return ModelResponse(parts=[TextPart(content=text)])


def _call_and_def(tool_name: str, args: dict) -> tuple[ToolCallPart, ToolDefinition]:
    return (
        ToolCallPart(tool_name=tool_name, args=args),
        ToolDefinition(name=tool_name, description=tool_name, parameters_json_schema={}),
    )


def _save_args(text: str) -> dict:
    return {
        "article_id": "a1",
        "final_markdown": text,
        "claims": [{"id": "C1", "text": "x", "type": "FACT", "source_ids": ["S1"], "status": "resolved"}],
        "sources": [{"id": "S1", "kind": "material", "label": "m", "material_ids": ["M001"]}],
    }


# --- Gate A: no regression -----------------------------------------------------


class TestGateANoRegression:
    def test_default_bundle_keeps_0_1_0_shape(self, tmp_path: Path) -> None:
        bundle = _bundle(tmp_path)
        assert len(bundle.toolsets) == 1
        assert bundle.capabilities == ()
        assert bundle.skill_dirs == ()

    def test_editorial_control_is_rejected_by_production_factory(self, tmp_path: Path) -> None:
        """v1.2 T014B: the production plugin no longer composes the editorial
        capability; a stale profile with editorial_control = true fails
        composition loudly instead of silently re-enabling a machine gate on
        taste. The capability survives only as benchmark/legacy code."""
        with pytest.raises(CompositionError, match="v1.2 T014B"):
            _bundle(tmp_path, {"editorial_control": True})
        # production remains the small writing environment
        bundle = _bundle(tmp_path)
        ctx = _ctx(tmp_path)
        names = set(asyncio.run(bundle.toolsets[0].get_tools(ctx)))
        assert names == WRITING_TOOLS

    def test_exactly_five_cognitive_actions_frozen(self) -> None:
        assert COGNITIVE_ACTIONS == (
            "return_to_observation",
            "delay_interpretation",
            "shift_perspective",
            "retrieve_concrete_memory",
            "break_trajectory",
        )


# --- sensors --------------------------------------------------------------------


class TestSensors:
    def test_templated_draft_crosses_threshold(self) -> None:
        from editorial_capability import combined_drift, run_trajectory_sensors

        signals = run_trajectory_sensors(TEMPLATED_DRAFT)
        assert set(signals) == {
            "template_connectors",
            "summary_pressure",
            "uniform_paragraphs",
            "low_concrete_anchor_density",
            "abstract_noun_density",
        }
        assert combined_drift(signals) >= 1.50

    def test_grounded_draft_stays_below_threshold(self) -> None:
        from editorial_capability import combined_drift, run_trajectory_sensors

        signals = run_trajectory_sensors(GROUNDED_DRAFT)
        assert combined_drift(signals) < 1.50

    def test_short_text_not_sensorable(self) -> None:
        from editorial_capability import run_trajectory_sensors

        assert run_trajectory_sensors("总之，这说明了问题的意义。") == {}


# --- dynamic instructions and the render→consume handshake -----------------------


class TestDynamicInstructions:
    def test_first_request_has_only_minimal_invariants(self, tmp_path: Path) -> None:
        cap = _capability()
        text = cap.get_instructions()(_ctx(tmp_path))
        assert "Do not optimize for one-pass completion" in text
        assert "editorial move" not in text

    def test_after_model_response_arms_and_renders_one_move(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        response = asyncio.run(
            cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
        )
        assert response.parts  # unchanged, observe-only
        assert cap.state.pending is not None
        rendered = cap.get_instructions()(ctx)
        assert rendered.count("[editorial move |") == 1
        assert "seed." in rendered  # Gate C: provenance refs present

    def test_before_model_request_consumes_pending(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        asyncio.run(
            cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
        )
        cap.get_instructions()(ctx)  # rendered into this request
        asyncio.run(cap.before_model_request(ctx, _request_context()))
        assert cap.state.interventions == 1
        assert cap.state.pending is None
        assert "editorial move" not in cap.get_instructions()(ctx)

    def test_interventions_bounded_by_max_injections(self, tmp_path: Path) -> None:
        cap = _capability(EditorialSettings(max_injections=2))
        ctx = _ctx(tmp_path)
        for _ in range(5):
            asyncio.run(
                cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
            )
            cap.get_instructions()(ctx)
            asyncio.run(cap.before_model_request(ctx, _request_context()))
        assert cap.state.interventions == 2

    def test_for_run_isolates_state(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        asyncio.run(
            cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
        )
        fresh = asyncio.run(cap.for_run(ctx))
        assert fresh is not cap
        assert fresh.state.pending is None
        assert fresh.state.interventions == 0
        assert cap.state.pending is not None  # original untouched

    def test_temperature_nudge_only_when_configured(self, tmp_path: Path) -> None:
        assert _capability().get_model_settings() is None  # default: no sampling change
        cap = _capability(EditorialSettings(temperature_nudge=0.15, base_temperature=0.7))
        ctx = _ctx(tmp_path)
        settings_fn = cap.get_model_settings()
        assert settings_fn(ctx) == {}  # nothing armed
        asyncio.run(
            cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
        )
        cap.get_instructions()(ctx)  # rendered → nudge applies to this request
        assert settings_fn(ctx) == {"temperature": pytest.approx(0.85)}


# --- after_tool_execute: context tags + low-pressure intervention ----------------


class TestAfterToolExecute:
    def test_observation_tools_recorded_as_tags(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        call, tool_def = _call_and_def("read_material", {"article_id": "a1", "material_id": "M001"})
        asyncio.run(cap.after_tool_execute(ctx, call=call, tool_def=tool_def, args={"article_id": "a1", "material_id": "M001"}, result="ok"))
        call, tool_def = _call_and_def("retrieve_exemplars", {"article_id": "a1", "query": "scene"})
        asyncio.run(cap.after_tool_execute(ctx, call=call, tool_def=tool_def, args={"article_id": "a1", "query": "scene"}, result="ok"))
        assert cap.state.context_tags == ["material_observed", "exemplar_observed"]

    def test_exemplar_observation_arms_low_pressure_move(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        call, tool_def = _call_and_def("retrieve_exemplars", {"article_id": "a1", "query": "scene"})
        asyncio.run(cap.after_tool_execute(ctx, call=call, tool_def=tool_def, args={"article_id": "a1", "query": "scene"}, result="ok"))
        assert cap.state.pending is not None
        assert cap.state.pending.origin == "after_tool_execute"
        assert cap.state.pending.evidence_ids[0] == "seed.after-exemplar.001"
        assert cap.state.pending.action == "return_to_observation"


# --- Gate B: bounded save veto ----------------------------------------------------


class TestSaveVeto:
    def test_high_drift_draft_vetoed_before_side_effect(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        call, tool_def = _call_and_def("save_artifact", _save_args(TEMPLATED_DRAFT))
        with pytest.raises(ModelRetry) as excinfo:
            asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args=_save_args(TEMPLATED_DRAFT)))
        message = str(excinfo.value)
        assert "EDITORIAL SAVE VETO" in message
        assert "seed." in message  # Gate C: evidence provenance cited
        assert "SMALLEST useful patch" in message
        assert "claims ledger and source ledger exactly" in message
        assert "identical draft will not be vetoed again" in message
        assert cap.state.save_vetoes == 1
        assert cap.state.last_veto_hash is not None

    def test_grounded_draft_passes_without_veto(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        call, tool_def = _call_and_def("save_artifact", _save_args(GROUNDED_DRAFT))
        args = asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args=_save_args(GROUNDED_DRAFT)))
        assert args["final_markdown"] == GROUNDED_DRAFT
        assert cap.state.save_vetoes == 0

    def test_identical_draft_never_rejected_twice(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        call, tool_def = _call_and_def("save_artifact", _save_args(TEMPLATED_DRAFT))
        with pytest.raises(ModelRetry):
            asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args=_save_args(TEMPLATED_DRAFT)))
        # Same draft again: passes even though the veto budget is not spent.
        args = asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args=_save_args(TEMPLATED_DRAFT)))
        assert args["final_markdown"] == TEMPLATED_DRAFT
        assert cap.state.save_vetoes == 1

    def test_veto_budget_exhausted_passes_different_draft(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        call, tool_def = _call_and_def("save_artifact", _save_args(TEMPLATED_DRAFT))
        with pytest.raises(ModelRetry):
            asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args=_save_args(TEMPLATED_DRAFT)))
        other = _save_args(TEMPLATED_DRAFT + "\n\n此外，值得注意的是，这一问题的意义与价值还需要进一步探讨。")
        args = asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args=other))
        assert args == other
        assert cap.state.save_vetoes == 1  # capped at max_save_vetoes = 1

    def test_non_save_tool_and_short_text_pass_through(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        call, tool_def = _call_and_def("read_material", {"article_id": "a1", "material_id": "M001"})
        args = asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args={"article_id": "a1", "material_id": "M001"}))
        assert args == {"article_id": "a1", "material_id": "M001"}
        short = _save_args("短文本，不足以判断。")
        call, tool_def = _call_and_def("save_artifact", short)
        assert asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args=short)) == short


# --- Gate C: provenance ------------------------------------------------------------


class TestGateCProvenance:
    def test_no_intervention_without_evidence_match(self, tmp_path: Path) -> None:
        store = EditorialEvidenceStore()
        store._entries.clear()  # no approved evidence at all
        cap = _capability(store=store)
        ctx = _ctx(tmp_path)
        asyncio.run(
            cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
        )
        assert cap.state.pending is None  # never a semantic intervention without provenance

    def test_every_intervention_carries_evidence_ids(self, tmp_path: Path) -> None:
        cap = _capability()
        ctx = _ctx(tmp_path)
        asyncio.run(
            cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
        )
        assert cap.state.pending is not None
        assert all(eid.startswith(("seed.", "human.")) for eid in cap.state.pending.evidence_ids)

    def test_human_patch_outranks_seed_on_signal_match(self, tmp_path: Path) -> None:
        evidence_path = tmp_path / "evidence.jsonl"
        human_patch = {
            "id": "human.patch.delay-explanation.001",
            "source_type": "human_patch",
            "source_ref": "patch:2026-08-16",
            "situation_tags": ["drafting", "nonfiction"],
            "trigger_signals": ["summary_pressure"],
            "action": "delay_interpretation",
            "directive": "Hold the explanation until after the second scene.",
            "rationale": "Editoror flagged premature explanation in review.",
            "weight": 4.0,
            "approved_by": "human-editor",
            "before_excerpt": "这说明……",
            "after_excerpt": "（第二个场景之后才出现解释）",
        }
        evidence_path.write_text(json.dumps(human_patch, ensure_ascii=False) + "\n", encoding="utf-8")
        store = EditorialEvidenceStore(evidence_path)
        assert len(store) == 7  # 6 seeds + 1 human patch
        ctx = _ctx(tmp_path)
        cap = _capability(store=store)
        asyncio.run(
            cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
        )
        assert cap.state.pending is not None
        assert cap.state.pending.evidence_ids[0] == "human.patch.delay-explanation.001"

    def test_malformed_evidence_line_fails_loud(self, tmp_path: Path) -> None:
        bad = tmp_path / "evidence.jsonl"
        bad.write_text("{not json}\n", encoding="utf-8")
        with pytest.raises(CompositionError, match="not a valid EditorialEvidence"):
            EditorialEvidenceStore(bad)

    def test_unknown_action_fails_loud(self, tmp_path: Path) -> None:
        bad = tmp_path / "evidence.jsonl"
        entry = {
            "id": "x.001",
            "source_type": "human_patch",
            "trigger_signals": ["summary_pressure"],
            "action": "rewrite_everything",  # not in the frozen v0.1 set
            "directive": "…",
        }
        bad.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        with pytest.raises(CompositionError, match="not one of"):
            EditorialEvidenceStore(bad)


# --- Gate D: human ownership --------------------------------------------------------


class TestGateDHumanOwnership:
    def test_capability_exposes_no_tools(self, tmp_path: Path) -> None:
        cap = _capability()
        assert cap.get_toolset() is None
        assert list(cap.get_native_tools()) == []

    def test_evidence_file_never_written_by_capability(self, tmp_path: Path) -> None:
        evidence_path = tmp_path / "evidence.jsonl"
        entry = {
            "id": "human.patch.break-trajectory.001",
            "source_type": "human_patch",
            "situation_tags": ["drafting", "nonfiction"],
            "trigger_signals": ["template_connectors"],
            "action": "break_trajectory",
            "directive": "Vary the structural move.",
            "rationale": "Templated openings flagged in review.",
            "weight": 4.0,
            "approved_by": "human-editor",
        }
        evidence_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        before = evidence_path.read_bytes()
        cap = _capability(EditorialSettings(evidence_path=evidence_path), EditorialEvidenceStore(evidence_path))
        ctx = _ctx(tmp_path)
        asyncio.run(
            cap.after_model_request(ctx, request_context=_request_context(), response=_response(TEMPLATED_DRAFT))
        )
        cap.get_instructions()(ctx)
        asyncio.run(cap.before_model_request(ctx, _request_context()))
        call, tool_def = _call_and_def("save_artifact", _save_args(TEMPLATED_DRAFT))
        with pytest.raises(ModelRetry):
            asyncio.run(cap.before_tool_execute(ctx, call=call, tool_def=tool_def, args=_save_args(TEMPLATED_DRAFT)))
        assert evidence_path.read_bytes() == before  # read-only at runtime


# --- config wiring: production surface rejects every editorial_* key (T014B) -----------


class TestEditorialConfigIsRejected:
    def test_every_editorial_key_fails_loud(self, tmp_path: Path) -> None:
        stale_keys = (
            {"editorial_control": True},
            {"editorial_control": False},  # even explicit OFF is now stale
            {"editorial_max_injections": 4},
            {"editorial_veto_threshold": 1.5},
            {"editorial_evidence_path": str(tmp_path / "e.jsonl")},
        )
        for cfg in stale_keys:
            with pytest.raises(CompositionError, match="v1.2 T014B"):
                _bundle(tmp_path, cfg)

    def test_rejection_message_points_to_legacy_location(self, tmp_path: Path) -> None:
        with pytest.raises(CompositionError, match="benchmarks/editorial-learning/legacy"):
            _bundle(tmp_path, {"editorial_control": True})


# --- composition: version bump + capability policy (SPEC §9/§10) -----------------------


ACE_EP = EntryPoint(
    name="ace-writing",
    value="zuaef_ace_writing:create_plugin",
    group="zuaef.plugins",
)


def _agent_settings(tmp_path: Path) -> AgentSettings:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp_path / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )


def _snapshot(version: str, capabilities_allowed: bool, config: dict | None = None) -> object:
    from zuaef_agent.plugin_api import CompositionSnapshot, compute_composition_id

    ref = PluginRef(
        id="ace-writing",
        version=version,
        entry_point="zuaef_ace_writing:create_plugin",
        config=config or {},
        capabilities_allowed=capabilities_allowed,
    )
    return CompositionSnapshot(
        profile="ace-writing",
        plugins=[ref],
        composition_id=compute_composition_id(profile="ace-writing", plugins=[ref]),
    )


class TestComposition:
    def test_version_bump_changes_composition_id(self) -> None:
        from zuaef_agent.plugin_api import compute_composition_id

        def ref(version: str) -> PluginRef:
            return PluginRef(id="ace-writing", version=version, entry_point="e", config={})

        old = compute_composition_id(profile=None, plugins=[ref("0.1.0")])
        new = compute_composition_id(profile=None, plugins=[ref("0.2.0")])
        assert old != new

    def test_old_snapshot_version_rejected(self, tmp_path: Path) -> None:
        snapshot = _snapshot("0.1.0", capabilities_allowed=True)
        with pytest.raises(CompositionError, match="version"):
            build_agent_from_snapshot(
                _agent_settings(tmp_path),
                snapshot=snapshot,
                discover=lambda: {"ace-writing": ACE_EP},
                version_for=lambda ep: "0.2.0",
            )

    def test_capability_without_allow_capabilities_rejected(self, tmp_path: Path) -> None:
        snapshot = _snapshot(
            "0.2.0",
            capabilities_allowed=False,
            config={
                "ace_root": str(_fake_ace_root(tmp_path)),
                "code_mode": True,
            },
        )
        with pytest.raises(CompositionError, match="allow_capabilities"):
            build_agent_from_snapshot(
                _agent_settings(tmp_path),
                snapshot=snapshot,
                discover=lambda: {"ace-writing": ACE_EP},
                version_for=lambda ep: "0.2.0",
            )

    def test_codemode_capability_composes_into_agent(self, tmp_path: Path) -> None:
        snapshot = _snapshot(
            "0.2.0",
            capabilities_allowed=True,
            config={
                "ace_root": str(_fake_ace_root(tmp_path)),
                "code_mode": True,
            },
        )
        agent = build_agent_from_snapshot(
            _agent_settings(tmp_path),
            snapshot=snapshot,
            discover=lambda: {"ace-writing": ACE_EP},
            version_for=lambda ep: "0.2.0",
        )
        from pydantic_ai.capabilities.abstract import leaf_capabilities

        caps = [type(c).__name__ for c in leaf_capabilities(agent.root_capability)]
        assert "CodeMode" in caps


# --- real agent loop: veto → retry → pass (the loop pydantic-ai actually runs) ----


class TestAgentLoopIntegration:
    def test_veto_retry_pass_in_real_loop(self, tmp_path: Path) -> None:
        """Drive the REAL pydantic-ai loop with a scripted FunctionModel:
        1. model submits the templated draft → vetoed before any side effect;
        2. model sees the veto retry prompt and submits the patched draft → saved;
        3. run completes. The templated draft must never reach the tool."""
        from pydantic_ai import Agent, FunctionToolset
        from pydantic_ai.models.function import FunctionModel

        saved: list[dict] = []
        toolset = FunctionToolset[CoreDeps]()

        @toolset.tool(retries=3)
        def save_artifact(
            ctx: RunContext[CoreDeps],
            article_id: str,
            final_markdown: str,
            claims: list[dict],
            sources: list[dict],
        ) -> dict:
            saved.append({"article_id": article_id, "final_markdown": final_markdown})
            return {"ok": True}

        # for_run() isolates state on a run-bound copy (SPEC §9), so the test
        # observes that copy through a tracking subclass.
        run_bound: list[EditorialControlCapability] = []

        class TrackingCapability(EditorialControlCapability):
            async def for_run(self, ctx: RunContext[CoreDeps]) -> EditorialControlCapability:
                fresh = await super().for_run(ctx)
                run_bound.append(fresh)
                return fresh

        cap = TrackingCapability(settings=EditorialSettings(), store=EditorialEvidenceStore())
        steps: list[object] = [
            ModelResponse(
                parts=[ToolCallPart(tool_name="save_artifact", args=_save_args(TEMPLATED_DRAFT))]
            ),
            ModelResponse(
                parts=[ToolCallPart(tool_name="save_artifact", args=_save_args(GROUNDED_DRAFT))]
            ),
            ModelResponse(parts=[TextPart(content="done")]),
        ]
        seen_history: list[str] = []

        async def scripted(messages: list, agent_info: object) -> ModelResponse:
            seen_history.append(str(messages))
            return steps[len(seen_history) - 1]

        agent: Agent[CoreDeps, str] = Agent(
            FunctionModel(scripted),
            deps_type=CoreDeps,
            output_type=str,
            capabilities=[cap],
            toolsets=[toolset],
        )

        deps = CoreDeps(workspace_root=tmp_path, run_id="r1")
        result = agent.run_sync("write", deps=deps)

        assert result.output == "done"
        # Only the patched draft was saved; the templated one was vetoed first.
        assert [s["final_markdown"] for s in saved] == [GROUNDED_DRAFT]
        # The veto reached the model as a retry prompt citing evidence.
        assert "EDITORIAL SAVE VETO" in seen_history[1]
        assert "seed." in seen_history[1]
        # Dynamic instructions are present in the real request history.
        assert "Editorial control is active" in seen_history[0]
        # Per-run isolation: the veto was counted on the run-bound copy,
        # and the original instance's state stayed untouched.
        assert len(run_bound) == 1
        assert run_bound[0].state.save_vetoes == 1
        assert cap.state.save_vetoes == 0
