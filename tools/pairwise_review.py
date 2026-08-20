"""T012 comparative review — baseline vs learned, LLM side (QUALITY_LOOP §4/§9).

Mechanical pack builder + LLM reviewer for one writing case:

- reads the two evaluation bundles produced by ``run_writing_eval.py``
  (``--variant baseline`` / ``--variant learned``);
- assembles a document-first comparison packet under
  ``learning/comparisons/<case>/``: request / baseline / learned / sources
  (raw texts preserved, never compressed into scores);
- asks the REAL model for a prose comparative review and writes it as
  ``llm-review.md``.

It NEVER writes ``human-judgment.md`` content: that file is created once as
an explicit ``PENDING-HUMAN`` template and is authoritative only after the
human edits it by hand (an ACCEPT string from a tool is not human authority).

Usage:

    uv run python tools/pairwise_review.py --case WCASE-1 [--prompt-only]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src")]

EVAL_ROOT = REPO / "workspace" / "artifacts" / "writing-v0.2" / "eval"
COMPARISONS = REPO / "learning" / "comparisons"

REVIEW_PROMPT = """\
You are reviewing two versions of ONE writing task: a baseline version and a
"learned" version produced after one promoted editorial lesson became a repo
skill (the lesson: openings should carry a concrete scene anchor — who, when,
where, what object; the author speaks in first person; paragraphs may end in
a restrained judgment but must not all close the same way; do not distill
every piece of material to the same density).

Answer in prose (Chinese is fine), covering at minimum:

1. What did each version actually accomplish against the assignment?
2. For each hard constraint (length, no fabricated scenes/quotes, facts from
   material only, no invented user reviews), does each version comply?
3. Where do the versions differ where it matters (opening, voice, paragraph
   rhythm, use of material)? Quote the specific passages.
4. Which version is closer to what a human editor would send, and why?
5. What edits would still be required on the preferred version?
6. Do any factual claims need source checking, and does the cited material
   appear to support them?
7. Honest verdict on the learned lesson: did it help, hurt, or make no
   difference on this task? You may say "no reusable difference on this task".

You are a reviewer, not the authority: the human editor makes the final
preference judgment. Do not output scores or a fixed label schema."""


def _read_pass_text(eval_variant_dir: Path) -> tuple[str, dict]:
    """(draft text, bundle) for one variant's evaluation directory."""
    bundle_path = eval_variant_dir / "bundle.json"
    if not bundle_path.is_file():
        raise SystemExit(f"missing bundle: {bundle_path} — run run_writing_eval first")
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    draft = eval_variant_dir / "draft.md"
    if not draft.is_file():
        raise SystemExit(f"missing draft.md: {draft}")
    return draft.read_text(encoding="utf-8"), bundle


def build_packet(case: str) -> Path:
    """Assemble the comparison packet; returns its directory."""
    baseline_dir = EVAL_ROOT / case / "baseline"
    learned_dir = EVAL_ROOT / case / "learned"
    baseline_text, baseline_bundle = _read_pass_text(baseline_dir)
    learned_text, learned_bundle = _read_pass_text(learned_dir)
    manifest = baseline_bundle.get("manifest") or {}

    out = COMPARISONS / case
    out.mkdir(parents=True, exist_ok=True)
    (out / "request.md").write_text(
        "\n".join(
            [
                f"# {case} — task contract",
                "",
                f"assignment: {manifest.get('assignment', '<missing>')}",
                f"audience: {manifest.get('audience', '<missing>')}",
                f"constraints: {json.dumps(manifest.get('constraints') or [], ensure_ascii=False)}",
                (
                    f"materials: {len(baseline_bundle.get('materials') or [])} files "
                    "(same set for both versions; host did not select)"
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (out / "baseline.md").write_text(baseline_text, encoding="utf-8")
    (out / "learned.md").write_text(learned_text, encoding="utf-8")
    (out / "sources.md").write_text(
        "\n".join(
            [
                "# Source pointers",
                "",
                (
                    "Writing/style cases: material is private/raw under "
                    f"{'; '.join(baseline_bundle.get('materials') or []) or '<none>'}"
                ),
                f"rights: {baseline_bundle.get('rights', 'unknown')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    diagnostics = {
        "baseline": {
            k: p.get(k)
            for p in baseline_bundle.get("passes", [])
            if p.get("pass") == "draft"
            for k in ("status", "model_requests", "artifact_chars")
        },
        "learned": {
            k: p.get(k)
            for p in learned_bundle.get("passes", [])
            if p.get("pass") == "draft"
            for k in ("status", "model_requests", "artifact_chars")
        },
        "note": "machine diagnostics only — never a quality verdict",
    }
    (out / "diagnostics.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    judgment = out / "human-judgment.md"
    if not judgment.is_file():
        judgment.write_text(
            "\n".join(
                [
                    f"# Human pairwise judgment — {case}",
                    "",
                    "STATUS: PENDING-HUMAN",
                    "",
                    "Which version would you send? (baseline / learned / tie)",
                    "",
                    "Reason (quote the passages that decided it):",
                    "",
                    "Edits still required on the preferred version:",
                    "",
                    (
                        "Does this task support keeping the promoted lesson? "
                        "(support / against / no-signal)"
                    ),
                    "",
                    "-- written by hand by the human editor; no tool fills this",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    return out


def render_prompt(packet: Path) -> str:
    def _read(name: str) -> str:
        p = packet / name
        return p.read_text(encoding="utf-8") if p.is_file() else "<missing>"

    return f"""# Comparative review: {_read('request.md')}

## Baseline version (before the lesson was a skill)
{_read('baseline.md')}

## Learned version (after the promoted lesson became a skill)
{_read('learned.md')}

## Source pointers
{_read('sources.md')}

---
{REVIEW_PROMPT}"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True, help="e.g. WCASE-1")
    ap.add_argument("--prompt-only", action="store_true")
    args = ap.parse_args()

    packet = build_packet(args.case)
    prompt = render_prompt(packet)
    if args.prompt_only:
        print(prompt)
        return 0

    from zuaef_agent.config import AgentSettings
    from zuaef_agent.providers import resolve_model

    settings = AgentSettings.from_env()
    import os

    if not (
        (settings.openai_base_url and settings.openai_api_key)
        or os.getenv("OPENAI_API_KEY")
    ):
        print("REVIEWER: no real model credentials — use --prompt-only")
        return 2

    import asyncio

    from pydantic_ai import Agent

    print(f"reviewing {args.case} with {resolve_model(settings)!r} ...")
    agent = Agent(model=resolve_model(settings), system_prompt=prompt)
    result = asyncio.run(agent.run("请按上述契约撰写对比评审的正文。"))
    (packet / "llm-review.md").write_text(str(result.output) + "\n", encoding="utf-8")
    print(f"wrote {packet / 'llm-review.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
