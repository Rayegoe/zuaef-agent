"""Static architecture guards — SPEC v0.3 §80, §95–§97, GW-12.

Behavioral tests prove the seams; these guards pin the layering: the Gateway
owns no agent/approval-engine/workflow class, composes through
``build_profile_agent`` and executes through the shared seams, and never
imports a business toolset directly.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


GATEWAY_SOURCES = {
    "src/zuaef_agent/gateway/models.py",
    "src/zuaef_agent/gateway/store.py",
    "src/zuaef_agent/gateway/surface.py",
    "src/zuaef_agent/gateway/telegram.py",
    "src/zuaef_agent/gateway/feishu.py",
    "src/zuaef_agent/gateway/routing.py",
    "src/zuaef_agent/gateway/bridge.py",
    "src/zuaef_agent/gateway/renderer.py",
    "src/zuaef_agent/gateway/service.py",
    "src/zuaef_agent/gateway/runner.py",
}


def test_gateway_defines_no_second_runtime_classes():
    banned = (
        "class GatewayAgent",
        "class TelegramAgent",
        "class ApprovalEngine",
        "class GatewayWorkflow",
        "class WorkflowRuntime",
        "class GatewayReceipt",
        "class EventBus",
        "class AgentRegistry",
        "class TaskGraph",
    )
    for path in GATEWAY_SOURCES:
        source = _read(path)
        for symbol in banned:
            assert symbol not in source, f"{path} must not define {symbol}"


def test_gateway_uses_shared_runtime_seams():
    bridge = _read("src/zuaef_agent/gateway/bridge.py")
    assert "execute_run" in bridge
    assert "resume_paused_run" in bridge
    assert "build_profile_agent" in bridge
    service = _read("src/zuaef_agent/gateway/service.py")
    assert "bridge.start_profile_run" in service
    assert "bridge.resume_for_surface" in service
    assert "execute_run" not in service, "service must run through the bridge"


def test_gateway_never_imports_business_toolsets():
    for path in GATEWAY_SOURCES:
        source = _read(path)
        assert "zuaef_wordpress" not in source, f"{path} imports a business plugin"
        assert "zuaef_ace_writing" not in source
    core = _read("src/zuaef_agent/core.py")
    assert "zuaef_wordpress" not in core


def test_feishu_surface_has_no_business_coupling():
    """Spec pack 07 A2: the Feishu adapter carries no business vocabulary —
    it is a generic surface, profiles (including quant-decision) are data."""
    source = _read("src/zuaef_agent/gateway/feishu.py")
    forbidden = (
        "BUY",
        "WATCH",
        "HOLD",
        "PIT",
        "T+1",
        "T+3",
        "T+5",
        "ticker",
        "position",
        "market_data",
        "quant",
    )
    for token in forbidden:
        assert token not in source, f"feishu adapter must not contain {token!r}"


def test_gateway_routing_policy_is_data_not_code():
    """Aliases and access policy are runtime configuration: the gateway
    source never names a business profile id."""
    for path in (
        "src/zuaef_agent/gateway/service.py",
        "src/zuaef_agent/gateway/routing.py",
        "src/zuaef_agent/gateway/runner.py",
    ):
        source = _read(path)
        assert "quant-decision" not in source, f"{path} names a business profile"


def test_wordpress_uses_entry_point_not_direct_import():
    pyproject = _read("plugins/zuaef-wordpress/pyproject.toml")
    assert '[project.entry-points."zuaef.plugins"]' in pyproject
    assert 'wordpress = "zuaef_wordpress:create_plugin"' in pyproject


def test_continuation_owned_once():
    """StepPersistence resume reconstruction (the ``continue_run`` import) is
    owned by exactly one module; the CLI and the Gateway both call it."""
    import ast

    owners: list[str] = []
    for path in sorted((REPO_ROOT / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "pydantic_ai_harness.step_persistence"
                and any(alias.name == "continue_run" for alias in node.names)
            ):
                owners.append(path.relative_to(REPO_ROOT).as_posix())
    assert owners == [
        "src/zuaef_agent/continuation.py"
    ], f"resume history reconstruction must live only in continuation.py, found {owners}"
