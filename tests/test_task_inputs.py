"""Benchmark BEFORE-material projection contract tests.

SPEC: benchmark-before-material-projection. Derived task records carry the
ASSIGNMENT in `material` and the real document in `before`. This test suite:

  1. reproduces the exact T01 failure shape (144-char assignment vs 4498-char
     BEFORE body) and proves the adapter returns BEFORE as the body;
  2. rejects missing/empty BEFORE before any model call;
  3. proves the execution-path wiring (run_benchmark / compare_paths material
     files) writes the BEFORE body — an artifact can never be "success"
     while the ingested material is the assignment prompt;
  4. keeps the adapter usable from all three runner locations.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]
BENCH = REPO / "benchmarks" / "editorial-learning"
SCRIPTS = BENCH / "scripts"
sys.path[:0] = [
    str(SCRIPTS),
    str(REPO),
    str(REPO / "examples"),
    str(REPO / "src"),
    str(REPO / "plugins" / "zuaef-ace-writing"),
]

from task_inputs import resolve_task_inputs

# Exact T01 shape: assignment is metadiscourse about the task, body is real.
T01_ASSIGNMENT = (
    "IteraTeR document revision task (domain: unknown, revision depth 1). "
    "Revise the BEFORE document. The human revision prim"
    "itive is clarity — apply it to the supplied text."
)
T01_BEFORE = (
    "240px| Several companies just looked the vision of WiMAX but ignore its "
    "threats. In the picture is MTube, innovated by S..."
) + (" More concrete body sentences with numbers and names. " * 20)


def _t01_shaped() -> dict:
    return {"task_id": "T01", "material": T01_ASSIGNMENT, "before": T01_BEFORE}


def test_happy_path_splits_assignment_and_before():
    inputs = resolve_task_inputs(_t01_shaped(), "T01")
    assert inputs["assignment"] == T01_ASSIGNMENT
    assert inputs["before_text"] == T01_BEFORE


def test_t01_shape_is_reproduced_from_real_data():
    """The committed derived task must still have the regression shape:
    assignment in material (short), real body in before (long)."""
    full = json_load(REPO / "data" / "derived" / "tasks_full" / "T01.json")
    if full is None:
        pytest.skip("data/derived absent (CI without datasets)")
    inputs = resolve_task_inputs(full, "T01")
    assert len(full["material"]) < 300  # the 144-char assignment, not a body
    assert len(inputs["before_text"]) > 1000  # the real BEFORE document
    assert inputs["before_text"] != full["material"]


def test_missing_before_fails_before_model_call():
    record = _t01_shaped()
    record.pop("before")
    with pytest.raises(ValueError, match="T01: 'before'"):
        resolve_task_inputs(record, "T01")


@pytest.mark.parametrize("bad", ["", "   ", "\n\t"])
def test_empty_before_fails(bad):
    record = _t01_shaped()
    record["before"] = bad
    with pytest.raises(ValueError, match="T01: 'before'"):
        resolve_task_inputs(record, "T01")


def test_missing_assignment_fails():
    record = _t01_shaped()
    record.pop("material")
    with pytest.raises(ValueError, match="T01: 'material'"):
        resolve_task_inputs(record, "T01")


def test_run_benchmark_material_file_writes_before_body(tmp_path):
    """The Gate E runner's ingested material must be the BEFORE body, never
    the assignment prompt (an artifact is only a revision if the model saw
    the document)."""
    from run_benchmark import _material_file

    path = _material_file("T01", T01_BEFORE)
    assert path.read_text(encoding="utf-8") == T01_BEFORE
    assert path.read_text(encoding="utf-8") != T01_ASSIGNMENT


def test_compare_paths_material_file_writes_before_body(tmp_path):
    """OLD/NEW/Writer-Editor share the same material seam."""
    from compare_paths import material_file

    path = material_file("T01", T01_BEFORE)
    assert path.read_text(encoding="utf-8") == T01_BEFORE
    assert path.read_text(encoding="utf-8") != T01_ASSIGNMENT


def test_prompt_only_input_cannot_be_projected_as_body():
    """PROMPT_ONLY matrix row: even a runner that historically passed
    material as the body gets BEFORE from the adapter — the adapter is the
    only way in."""
    record = _t01_shaped()
    inputs = resolve_task_inputs(record, "T01")
    prompt_text = inputs["assignment"] + "\n\n### BEFORE document\n\n" + inputs["before_text"]
    assert T01_BEFORE in prompt_text
    assert T01_ASSIGNMENT in prompt_text
    # the projected body section contains the real document, not assignment
    body = prompt_text.split("### BEFORE document\n\n", 1)[1]
    assert body.startswith(T01_BEFORE)


def json_load(path: Path):
    import json

    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
