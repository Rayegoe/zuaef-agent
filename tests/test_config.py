import math
from pathlib import Path

import pytest

from zuaef_agent.config import AgentSettings


def test_defaults_are_bounded_and_durable_guards_enabled():
    s = AgentSettings()
    assert s.request_limit > 0
    assert s.tool_calls_limit > 0
    assert s.workspace_root == Path("workspace")
    assert s.enable_tool_output_limits is True
    assert s.enable_step_persistence is True
    assert s.max_snapshots_per_run == 8
    assert s.state_root == Path(".zuaef-state")
    assert s.step_store_dir == Path(".zuaef-state/steps")
    assert s.tool_result_dir == Path(".zuaef-state/tool-results")


def test_compatible_endpoint_requires_model_name():
    with pytest.raises(ValueError):
        AgentSettings(openai_base_url="http://localhost:8000/v1")


def test_snapshot_bound_must_be_valid():
    with pytest.raises(ValueError):
        AgentSettings(max_snapshots_per_run=0)


def test_runtime_state_cannot_live_inside_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    with pytest.raises(ValueError):
        AgentSettings(workspace_root=workspace, runtime_state_root=workspace / ".state")


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_provider_timeout_must_be_finite(value: float):
    with pytest.raises(ValueError, match="finite"):
        AgentSettings(openai_timeout_seconds=value)
