"""LLM reviewer for a document-first learning case packet (v1.2 T010).

Reads one case directory under ``learning/cases/<case-id>/`` and writes
``llm-review.md``: a prose review answering the QUALITY_LOOP.md §4 review
contract, with an explicit option for "no reusable lesson".

Usage (real model credentials required):

    uv run python tools/llm_reviewer.py --case learning/cases/summer-nail-rewrite-20260819

The reviewer produces PROSE, not a fixed classification. It never writes a
mandatory label/taxonomy (no trigger_signal/action/weight/approved_by).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

# The review contract from QUALITY_LOOP.md §4 — fixed prose questions, no
# fixed answer schema.
REVIEW_PROMPT = """\
You are an independent LLM reviewer for one learning case from this project's
document-first quality loop. You have been given: the original request, the
relevant context/material, the model output, and the source/resource pointers.

Write a prose review in Chinese (the working language of this case) as
`llm-review.md`, answering these questions directly. Do NOT produce a fixed
label schema, a score table, or an enum. Quote the passages you mean.

1. What did the output actually accomplish?
2. What important requirement did it miss?
3. Which factual claims (if any) need source checking?
4. For each important cited claim, does the cited source appear to support
   it? (State clearly when the material is private customer material with no
   public URL — that is a legitimate different case from research.)
5. What is weak in reasoning, writing, structure, tone, or business judgment?
6. Which passages should change, and why? (Be specific; quote before/after.)
7. What should be preserved?
8. What generalizable lesson, if any, can be proposed?

End with one of these two explicit lines:

- LESSON: <the proposed lesson in one natural-language sentence>
- LESSON: no reusable lesson should be promoted from this case.

You will not receive the human's opinion; produce your own independent
review. Do not invent facts or sources that are not in the packet.
"""


def load_packet(case_dir: Path) -> dict:
    manifest_path = case_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"no manifest.json in {case_dir}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"manifest.json unreadable in {case_dir}: {exc}") from exc
    packet = {"manifest": manifest, "case_dir": case_dir}
    for key in ("request", "context", "output", "sources", "revised"):
        rel = manifest.get(key)
        if rel:
            f = case_dir / rel
            packet[key] = f.read_text(encoding="utf-8") if f.is_file() else "<missing>"
    return packet


def render_prompt(packet: dict) -> str:
    m = packet["manifest"]
    return f"""# Learning case: {m['case_id']}

## Request
{packet.get('request', '<missing>')}

## Context / material
{packet.get('context', '<missing>')}

## Model output (the evaluated version)
{packet.get('output', '<missing>')}

## Sources / resource pointers
{packet.get('sources', '<missing>')}

## Revised / preferred text (may be absent for the reviewed output)
{packet.get('revised', '<missing>')}

---
{REVIEW_PROMPT}"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True, type=Path, help="case directory under learning/cases/")
    ap.add_argument("--prompt-only", action="store_true", help="print the prompt and exit (no model call)")
    args = ap.parse_args()

    case_dir = args.case.resolve()
    if not case_dir.is_dir():
        raise SystemExit(f"case directory not found: {case_dir}")
    packet = load_packet(case_dir)
    prompt = render_prompt(packet)

    if args.prompt_only:
        print(prompt)
        return 0

    from zuaef_agent.config import AgentSettings
    from zuaef_agent.providers import resolve_model

    settings = AgentSettings.from_env()
    has_credentials = bool(settings.openai_base_url and settings.openai_api_key) or bool(
        __import__("os").getenv("OPENAI_API_KEY")
    )
    if not has_credentials:
        print(
            "REVIEWER: no real model credentials — use --prompt-only to inspect "
            "the review prompt, or run with LLM_API_BASE/LLM_API_KEY/LLM_MODEL."
        )
        return 2

    import asyncio

    from pydantic_ai import Agent

    agent = Agent(model=resolve_model(settings), system_prompt=prompt)
    result = asyncio.run(agent.run("请按上述契约撰写 llm-review.md 的正文。"))
    review_path = case_dir / "llm-review.md"
    review_path.write_text(str(result.output) + "\n", encoding="utf-8")
    print(f"wrote {review_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())