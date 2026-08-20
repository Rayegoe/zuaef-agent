"""Slice integration test (SPEC v0.1 §62): profile -> plugin resolution ->
PluginBundle -> toolset -> policy execution -> draft -> receipt.

Driven with FunctionModel (no network/credentials); plugin resolution is
hermetic via the discover/version_for injection seam in composition.py.
"""

from __future__ import annotations

import shutil
from importlib.metadata import EntryPoint
from pathlib import Path
from uuid import uuid4

from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from zuaef_agent.composition import (
    build_agent_from_snapshot,
    resolve_profile,
)
from zuaef_agent.config import AgentSettings
from zuaef_agent.models import CoreDeps
from zuaef_agent.runtime import (
    TerminalRun,
    execute_run,
)

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_client_service"

PROFILE_TOML = """\
schema = 1
name = "client-service-beauty"

[[plugins]]
id = "client-service"
allow_capabilities = false

[plugins.config]
mode = "shadow"
domain = "beauty-content"
slice_root = "{slice_root}"
"""


def _entry_points() -> dict[str, EntryPoint]:
    return {
        "client-service": EntryPoint(
            name="client-service",
            value="zuaef_client_service.plugin:build_plugin",
            group="zuaef.plugins",
        )
    }


def _version_for(_ep: EntryPoint) -> str:
    return "0.1.0"


def _settings(tmp: Path) -> AgentSettings:
    workspace = tmp / "workspace"
    workspace.mkdir(exist_ok=True)
    return AgentSettings(
        model="test",
        workspace_root=workspace,
        runtime_state_root=tmp / ".zuaef-state",
        enable_planning=False,
        enable_skills=False,
    )


def _make_slice_root(tmp: Path) -> Path:
    root = tmp / "slice"
    shutil.copytree(FIXTURE, root)
    return root


class TestSliceComposition:
    def test_resolve_and_compose_plugin_profile(self, tmp_path: Path) -> None:
        slice_root = _make_slice_root(tmp_path)
        config_root = tmp_path / "config"
        (config_root / "profiles").mkdir(parents=True)
        (config_root / "profiles" / "client-service-beauty.toml").write_text(
            PROFILE_TOML.format(slice_root=slice_root), encoding="utf-8"
        )
        settings = _settings(tmp_path)

        snapshot = resolve_profile(
            "client-service-beauty",
            settings,
            config_root=config_root,
            discover=_entry_points,
            version_for=_version_for,
        )
        assert snapshot.profile == "client-service-beauty"
        assert [p.id for p in snapshot.plugins] == ["client-service"]
        assert snapshot.plugins[0].version == "0.1.0"
        assert snapshot.plugins[0].entry_point == (
            "zuaef_client_service.plugin:build_plugin"
        )
        assert snapshot.plugins[0].capabilities_allowed is False
        assert snapshot.composition_id

        agent = build_agent_from_snapshot(
            settings,
            run_id=uuid4().hex,
            snapshot=snapshot,
            discover=_entry_points,
            version_for=_version_for,
        )
        assert agent is not None

    def test_run_through_profile_generates_receipt(self, tmp_path: Path) -> None:
        slice_root = _make_slice_root(tmp_path)
        config_root = tmp_path / "config"
        (config_root / "profiles").mkdir(parents=True)
        (config_root / "profiles" / "client-service-beauty.toml").write_text(
            PROFILE_TOML.format(slice_root=slice_root), encoding="utf-8"
        )
        settings = _settings(tmp_path)
        run_id = uuid4().hex
        snapshot = resolve_profile(
            "client-service-beauty",
            settings,
            config_root=config_root,
            discover=_entry_points,
            version_for=_version_for,
        )
        agent = build_agent_from_snapshot(
            settings,
            run_id=run_id,
            snapshot=snapshot,
            discover=_entry_points,
            version_for=_version_for,
        )
        deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)
        calls: list[str] = []

        def fn(messages, info):
            has_return = any(
                getattr(part, "part_kind", None) in ("tool-return", "tool-retry")
                for message in messages
                for part in getattr(message, "parts", [])
            )
            if not has_return:
                calls.append("retrieve")
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "retrieve_client_context",
                            {
                                "customer_id": "CASE-SYN-001",
                                "query": "有没有成功案例可以分享呀？",
                                "limit": 8,
                            },
                        )
                    ]
                )
            return ModelResponse(parts=[TextPart(content="资格审查草稿完成")])

        with agent.override(model=FunctionModel(fn)):
            outcome = execute_run(
                agent,
                deps,
                prompt="客户问：有没有成功案例可以分享？",
                settings=settings,
                run_id=run_id,
                composition=snapshot,
            )

        assert isinstance(outcome, TerminalRun)
        assert outcome.receipt.execution_state == "completed"
        assert calls == ["retrieve"]
        receipt = outcome.receipt
        assert receipt.run_id == run_id
        assert receipt.composition is not None
        assert receipt.composition.profile == "client-service-beauty"
        assert [p.id for p in receipt.composition.plugins] == ["client-service"]

    def test_record_interaction_is_local_write(self, tmp_path: Path) -> None:
        """P3B-2 INV-9: recording internal business history is a local write —
        it executes inline, writes the interaction receipt and updates state,
        with zero approval pauses."""
        slice_root = _make_slice_root(tmp_path)
        settings = _settings(tmp_path)
        run_id = uuid4().hex
        from zuaef_client_service.store import ClientServiceStore

        store = ClientServiceStore(slice_root)
        from zuaef_client_service.toolset import build_client_service_toolset

        from zuaef_agent.core import build_agent

        agent = build_agent(
            settings,
            run_id=run_id,
            extra_toolsets=[
                build_client_service_toolset(
                    store, plugin_id="client-service", plugin_version="0.1.0"
                )
            ],
        )
        deps = CoreDeps(workspace_root=settings.workspace_root.resolve(), run_id=run_id)

        def fn(messages, info):
            has_return = any(
                getattr(part, "part_kind", None) in ("tool-return", "tool-retry")
                for message in messages
                for part in getattr(message, "parts", [])
            )
            if not has_return:
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "record_interaction",
                            {
                                "customer_id": "CASE-SYN-001",
                                "incoming_message": "有没有成功案例可以分享呀？",
                                "assessment": {
                                    "customer_id": "CASE-SYN-001",
                                    "signals": ["case_request"],
                                    "authority": "unknown",
                                    "budget_signal": "unknown",
                                    "uncertainties": ["decision_authority_unknown"],
                                    "evidence_ids": [],
                                    "feature": {"asks_case": True},
                                },
                                "strategy": {},
                                "draft_response": "先确认一下您这边的决策链和预算情况。",
                                "human_action": "APPROVED",
                            },
                        )
                    ]
                )
            return ModelResponse(parts=[TextPart(content="交互已记录")])

        with agent.override(model=FunctionModel(fn)):
            outcome = execute_run(
                agent,
                deps,
                prompt="记录这次交互",
                settings=settings,
                run_id=run_id,
            )

        assert isinstance(outcome, TerminalRun), type(outcome)
        assert outcome.receipt.execution_state == "completed"
        interactions = list((slice_root / "state" / "interactions").glob("INT-*.json"))
        assert len(interactions) == 1
        state_text = (
            slice_root / "state" / "customers" / "CASE-SYN-001.yaml"
        ).read_text(encoding="utf-8")
        assert "CASE-SYN-001" in state_text
