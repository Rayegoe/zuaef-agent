from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "compare_metrics.py"
spec = spec_from_file_location("compare_metrics", SCRIPT)
module = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_compare_reports_runtime_deltas_and_tool_surface():
    before = {
        "case": "WCASE-1",
        "outcome_pass": True,
        "evidence_pass": True,
        "requests": 16,
        "tool_calls": 27,
        "input_tokens": 1000,
        "model_visible_tools": ["write_plan", "read_material", "save_artifact"],
    }
    after = {
        "case": "WCASE-1",
        "outcome_pass": True,
        "evidence_pass": True,
        "requests": 4,
        "tool_calls": 6,
        "input_tokens": 600,
        "model_visible_tools": ["read_material", "save_artifact"],
    }
    result = module.compare(before, after)
    assert result["metrics"]["requests"]["delta"] == -12
    assert result["model_visible_tools"]["removed"] == ["write_plan"]
