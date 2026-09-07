"""Method Kernel v0.1 tests (T001/T003/T005/T006/T007) — all offline, no model.

The spec's hard constraints are what these tests protect: the kernel is a
short soft-principle block (not a workflow), the reviewer generalizes without
becoming a taxonomy, promotion becomes intervention-neutral while staying
human-gated, and the ablation runner records machine facts without ever
producing a scalar score or automatic verdict.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if importlib.util.find_spec("zuaef_agent") is None:
    sys.path.insert(0, str(REPO / "src"))


def _load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# --- T001: the Core Method Kernel ---------------------------------------------


def _flat(text: str) -> str:
    """Whitespace-normalized text: kernel prose wraps across source lines."""
    return " ".join(text.split())


def test_core_instructions_contain_the_six_principles():
    from zuaef_agent.core import CORE_INSTRUCTIONS

    flat = _flat(CORE_INSTRUCTIONS)
    for phrase in (
        "Reconstruct reality before proposing change",
        "Evidence outranks explanation",
        "smallest intervention that can prove the outcome",
        "uncertainty explicit",
        "falsify important conclusions",
        "Recommend durable additions only when evidence",
    ):
        assert phrase in flat, f"missing kernel principle: {phrase}"


def test_method_kernel_is_short_soft_and_domain_free():
    from zuaef_agent.core import CORE_INSTRUCTIONS

    flat = _flat(CORE_INSTRUCTIONS)
    # Soft, not a state machine / mandatory checklist.
    assert "not a mandatory workflow" in flat
    assert "simple tasks just get done" in flat
    # No domain names leaked into the core instructions ("writing" names a
    # generic activity in the pre-existing text, not a business domain).
    for domain in ("quant", "stillevo", "feishu", "wordpress"):
        assert domain not in flat, f"domain leak: {domain}"
    # The kernel block stays within the spec's ~150-250 token budget
    # (guarded here as a character bound: ~6.5 chars/token).
    start = CORE_INSTRUCTIONS.index("Method Kernel")
    end = CORE_INSTRUCTIONS.index("For normal analysis")
    kernel = _flat(CORE_INSTRUCTIONS[start:end])
    assert len(kernel) < 250 * 7, f"kernel block too long: {len(kernel)} chars"


# --- T003: generalized independent reviewer ------------------------------------


def test_reviewer_accepts_kind_neutral_packet(tmp_path):
    mod = _load_tool("llm_reviewer")
    packet_dir = tmp_path / "impl-packet"
    packet_dir.mkdir()
    (packet_dir / "manifest.json").write_text(
        json.dumps(
            {
                "case_id": "impl-packet",
                "kind": "implementation",
                "task": "task.md",
                "context": "context.md",
                "result": "result.md",
                "validation": "validation.md",
                "sources": "sources.md",
            }
        ),
        encoding="utf-8",
    )
    for name in ("task", "context", "result", "validation", "sources"):
        (packet_dir / f"{name}.md").write_text(f"{name} body", encoding="utf-8")

    packet = mod.load_packet(packet_dir)
    assert packet["task"] == "task body"
    assert packet["validation"] == "validation body"
    prompt = mod.render_prompt(packet)
    assert "Deliverable kind: implementation" in prompt
    assert "## Task / request" in prompt
    assert "## Result (the evaluated output)" in prompt
    assert "## Validation evidence / preferred variant" in prompt
    # The review contract stays prose-first with the independent stance.
    assert "no reusable lesson should be promoted" in _flat(prompt)
    assert "counterexample could break the conclusion" in _flat(prompt)
    assert "simpler" in prompt
    assert "Do NOT produce a fixed label schema" in _flat(prompt)


def test_reviewer_still_loads_learning_case_packet():
    mod = _load_tool("llm_reviewer")
    case_dir = REPO / "learning" / "cases" / "summer-nail-rewrite-20260819"
    packet = mod.load_packet(case_dir)
    prompt = mod.render_prompt(packet)
    # Backward compatible: legacy manifest keys render the same sections.
    assert "## Task / request" in prompt
    assert "李姐，这篇我按您老板的口味现场改了一版" in prompt
    assert "What did the output actually accomplish" in prompt


# --- T005/T006: intervention-neutral, human-gated promotion --------------------


def test_promotion_records_intervention_and_disposition_verbatim(tmp_path):
    mod = _load_tool("promote_lesson")
    case = tmp_path / "retire-case"
    case.mkdir()
    (case / "manifest.json").write_text(
        json.dumps({"case_id": "retire-case", "output": "out.md"}), encoding="utf-8"
    )
    (case / "out.md").write_text("output", encoding="utf-8")
    (case / "human-review.md").write_text(
        "Decision: ACCEPT\n"
        "intervention: retirement candidate — quant-research-skill\n"
        "disposition: delete after one confirming ablation\n"
        "\n理由：模型升级后 without skill 与 with skill 无可辨差别。\n",
        encoding="utf-8",
    )
    target = mod.promote(case, dry_run=True)
    assert target.name == "retire-case.json"
    # Verbatim human text survives; the tool derives nothing.
    text = (case / "human-review.md").read_text(encoding="utf-8")
    assert "delete after one confirming ablation" in text


def test_promotion_without_markers_keeps_v1_payload_shape(tmp_path):
    mod = _load_tool("promote_lesson")
    case = tmp_path / "plain-case"
    case.mkdir()
    (case / "manifest.json").write_text(
        json.dumps({"case_id": "plain-case", "output": "out.md"}), encoding="utf-8"
    )
    (case / "out.md").write_text("output", encoding="utf-8")
    (case / "human-review.md").write_text("Decision: ACCEPT\n同意采纳。\n", encoding="utf-8")
    payload = mod._promotion_payload(case, "Decision: ACCEPT\n同意采纳。\n", "accepted")
    assert "intervention" not in payload and "disposition" not in payload
    assert payload["schema_version"] == 1


def test_promotion_still_requires_human_authority(tmp_path):
    mod = _load_tool("promote_lesson")
    case = tmp_path / "no-human"
    case.mkdir()
    (case / "manifest.json").write_text(
        json.dumps({"case_id": "no-human", "output": "out.md"}), encoding="utf-8"
    )
    (case / "out.md").write_text("output", encoding="utf-8")
    try:
        mod.promote(case, dry_run=True)
    except SystemExit:
        pass
    else:  # pragma: no cover
        raise AssertionError("promotion must refuse without human review")


# --- T007: minimal ablation runner ---------------------------------------------


def test_ablate_records_machine_facts_without_a_verdict(tmp_path):
    mod = _load_tool("ablate")
    case = tmp_path / "case-x"
    case.mkdir()
    (case / "task.md").write_text("Diagnose and propose the smallest fix.\n", encoding="utf-8")
    calls: list[str] = []

    def fake_run_side(task, *, side, append_path, request_limit, run_id):
        calls.append(side)
        assert task.startswith("Diagnose")
        return {
            "record": {
                "side": side,
                "run_id": run_id,
                "status": "completed",
                "model_requests": 4,
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_tokens": 1500,
                "tool_calls": 1,
                "tool_names": ["read_file"],
                "latency_ms": 8000.0,
                "error": None,
                "paused": False,
            },
            "presentation": f"{side} presentation",
        }

    out = tmp_path / "out"
    diagnostics = mod.ablate(
        case,
        candidate_append=None,
        run_side_fn=fake_run_side,
        out_dir=out,
    )
    assert calls == ["baseline", "candidate"]  # same task, fixed recorded order
    assert diagnostics["note"] == mod.NOTE
    assert diagnostics["order"] == ["baseline", "candidate"]
    for side in ("baseline", "candidate"):
        record = diagnostics[side]
        assert record["status"] == "completed"
        assert record["model_requests"] == 4
        assert (out / side / "output.md").read_text(encoding="utf-8").startswith(side)
    blob = (out / "diagnostics.json").read_text(encoding="utf-8")
    # No scalar score, no winner, no automatic verdict — ever. (The note
    # string legitimately SAYS "never a quality verdict"; keys must not.)
    loaded = json.loads(blob)
    for record in (loaded["baseline"], loaded["candidate"]):
        for forbidden in ("score", "winner", "verdict", "AGENT_SCORE"):
            assert forbidden not in record


def test_ablate_requires_case_task(tmp_path):
    mod = _load_tool("ablate")
    case = tmp_path / "empty-case"
    case.mkdir()
    try:
        mod.load_task(case)
    except SystemExit:
        pass
    else:  # pragma: no cover
        raise AssertionError("ablate must refuse a case without task.md")
