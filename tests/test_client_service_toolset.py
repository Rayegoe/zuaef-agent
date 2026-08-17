"""ClientServiceToolset tests over the synthetic fixture (SPEC §24-27)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from pydantic_ai import RunContext, RunUsage
from pydantic_ai.models.test import TestModel
from zuaef_client_service.store import ClientServiceStore
from zuaef_client_service.toolset import build_client_service_toolset

from zuaef_agent.models import CoreDeps

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_client_service"

EXPECTED_TOOLS = {
    "retrieve_client_context",
    "assess_customer",
    "select_response_strategy",
    "record_interaction",
}


def _invoke_tool(tool: object, args: dict[str, Any], ctx: Any) -> Any:
    return cast(Any, tool).function(ctx, **args)


@pytest.fixture()
def env(tmp_path: Path):
    root = tmp_path / "slice"
    shutil.copytree(FIXTURE, root)
    store = ClientServiceStore(root)
    toolset = build_client_service_toolset(
        store, plugin_id="client-service", plugin_version="0.1.0"
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    run_id = uuid4().hex

    def ctx() -> RunContext[CoreDeps]:
        deps = CoreDeps(workspace_root=workspace, run_id=run_id)
        return RunContext[CoreDeps](deps=deps, model=TestModel(), usage=RunUsage())

    return {
        "root": root,
        "store": store,
        "toolset": toolset,
        "by_name": toolset.tools,
        "run_id": run_id,
        "ctx": ctx,
    }


class TestToolset:
    def test_four_domain_tools_exposed(self, env) -> None:
        assert set(env["by_name"]) == EXPECTED_TOOLS

    def test_retrieve_client_context_shape(self, env) -> None:
        out = _invoke_tool(
            env["by_name"]["retrieve_client_context"],
            {"customer_id": "CASE-SYN-001", "query": "有没有成功案例", "limit": 8},
            env["ctx"](),
        )
        assert out["customer_id"] == "CASE-SYN-001"
        assert out["customer_state"]["authority"] == "unknown"
        assert any(k["knowledge_id"] == "KNO-SYN-001" for k in out["knowledge"])
        assert any(s["preference_id"] == "SEM-SYN-001" for s in out["semantic_refs"])
        assert any(e["evidence_id"] == "EVD-SYN-001" for e in out["evidence_refs"])

    def test_assess_case_request(self, env) -> None:
        out = _invoke_tool(
            env["by_name"]["assess_customer"],
            {"customer_id": "CASE-SYN-001", "message": "有没有成功案例可以分享呀？"},
            env["ctx"](),
        )
        assert out["authority"] == "unknown"
        assert out["feature"]["asks_case"] is True
        assert "case_request" in out["signals"]
        assert "decision_authority_unknown" in out["uncertainties"]

    def test_strategy_for_case_request_qualifies_before_disclose(self, env) -> None:
        assessment = _invoke_tool(
            env["by_name"]["assess_customer"],
            {"customer_id": "CASE-SYN-001", "message": "有没有成功案例可以分享呀？"},
            env["ctx"](),
        )
        strategy = _invoke_tool(
            env["by_name"]["select_response_strategy"],
            {"customer_id": "CASE-SYN-001", "assessment": assessment},
            env["ctx"](),
        )
        assert strategy["strategy"] == "QUALIFY_BEFORE_DISCLOSE"
        assert "POL-C-006" in strategy["matched_policy_ids"]
        assert strategy["approval_level"] == "R2"
        assert "clarify_decision_authority" in strategy["allowed_actions"]
        assert "send_detailed_case" in strategy["restricted_actions"]

    def test_strategy_for_price_request(self, env) -> None:
        assessment = _invoke_tool(
            env["by_name"]["assess_customer"],
            {"customer_id": "CASE-SYN-001", "message": "现在做内容要花多少钱？"},
            env["ctx"](),
        )
        strategy = _invoke_tool(
            env["by_name"]["select_response_strategy"],
            {"customer_id": "CASE-SYN-001", "assessment": assessment},
            env["ctx"](),
        )
        assert "POL-C-021" in strategy["matched_policy_ids"]
        assert strategy["approval_level"] == "R2"

    def test_record_interaction_writes_receipt_and_state(self, env) -> None:
        assessment = _invoke_tool(
            env["by_name"]["assess_customer"],
            {"customer_id": "CASE-SYN-001", "message": "有没有成功案例可以分享呀？"},
            env["ctx"](),
        )
        strategy = _invoke_tool(
            env["by_name"]["select_response_strategy"],
            {"customer_id": "CASE-SYN-001", "assessment": assessment},
            env["ctx"](),
        )
        result = _invoke_tool(
            env["by_name"]["record_interaction"],
            {
                "customer_id": "CASE-SYN-001",
                "incoming_message": "有没有成功案例可以分享呀？",
                "assessment": assessment,
                "strategy": strategy,
                "draft_response": "先确认一下您这边的决策链和预算情况……",
                "human_action": "APPROVED",
            },
            env["ctx"](),
        )
        assert result["written"] is True
        assert result["run_id"] == env["run_id"]
        receipt_path = (
            env["root"]
            / "state"
            / "interactions"
            / f"{result['interaction_id']}.json"
        )
        assert receipt_path.is_file()
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        assert receipt["run_id"] == env["run_id"]
        assert receipt["strategy"] == "QUALIFY_BEFORE_DISCLOSE"
        state_path = env["root"] / "state" / "customers" / "CASE-SYN-001.yaml"
        assert "继续资格审查" in state_path.read_text(encoding="utf-8")

    def test_record_interaction_is_approval_gated(self, env) -> None:
        tool = env["by_name"]["record_interaction"]
        assert cast(Any, tool).tool_def.defer is True
