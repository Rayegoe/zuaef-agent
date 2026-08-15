from pathlib import Path


def test_v11_core_uses_harness_guards_without_custom_runtime():
    root = Path(__file__).parents[1]
    core = (root / "src/zuaef_agent/core.py").read_text(encoding="utf-8")
    assert "ToolOutputLimits" in core
    assert "StepPersistence" in core
    assert "LocalFileStore" in core
    assert "FileStepStore" in core
    assert "AgentRegistry" not in core
    assert "StateMachine" not in core


def test_approval_example_uses_native_pydanticai_flag():
    root = Path(__file__).parents[1]
    example = (root / "examples/approval_toolset.py").read_text(encoding="utf-8")
    assert "requires_approval=" in example
    assert "HumanGate" not in example
