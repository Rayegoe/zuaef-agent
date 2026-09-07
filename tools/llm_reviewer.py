"""Independent LLM reviewer for one deliverable packet (v1.2 T010, MK v0.1 T003).

Reads one packet directory (``learning/cases/<case-id>/`` for learning cases;
any packet dir following the same manifest-addressing shape for other kinds)
and writes ``llm-review.md``: a prose review, with an explicit option for
"no reusable lesson".

Generalized (Method Kernel v0.1 T003) to review any deliverable kind —
documents, implementation, research, architecture, business artifacts — by
accepting either the original learning-case manifest keys
(``request/context/output/sources/revised``) or the kind-neutral keys
(``task/context/result/validation/sources``). ``manifest["kind"]`` optionally
narrows the reviewer's role sentence. The review output stays PROSE, never a
fixed classification; no score enum or label taxonomy is introduced.

Usage (real model credentials required):

    uv run python tools/llm_reviewer.py --case learning/cases/summer-nail-rewrite-20260819
    uv run python tools/llm_reviewer.py --case learning/comparisons/MK-ABLATION-1

The reviewer is INDEPENDENT: it never receives the human's opinion or the
main agent's self-explanation as authority.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

# The review contract (QUALITY_LOOP.md §4, generalized by MK v0.1 §Review):
# fixed prose questions, no fixed answer schema. Questions cover what was
# accomplished, what is proven vs merely claimed, missed requirements, source
# checking, weak reasoning/design, counterexamples and simpler alternatives,
# what to change, what to preserve, and what generalizes.
REVIEW_PROMPT = """\
You are an independent LLM reviewer for one deliverable packet from this
project — a learning case, an implementation, a research result, an
architecture proposal, or a business deliverable. You have been given: the
original task/request, the relevant context/evidence, the produced result,
any validation evidence, and the source/resource pointers.

Write a prose review in the packet's working language (default Chinese) as
`llm-review.md`, answering these questions directly. Do NOT produce a fixed
label schema, a score table, or an enum. Quote the passages you mean.

1. What did the output actually accomplish?
2. What is actually proven by the evidence, and what is merely claimed?
3. What important requirement did it miss?
4. Which factual claims (if any) need source checking?
5. For each important cited claim, does the cited source appear to support
   it? (State clearly when the material is private material with no public
   URL — that is a legitimate different case from research.)
6. What is weak in reasoning, writing, structure, design, tone, or business
   judgment?
7. What counterexample could break the conclusion? Is there a simpler
   explanation or a smaller implementation that would do?
8. Which passages or elements should change, and why? (Be specific; quote
   before/after where applicable.)
9. What should be preserved?
10. What generalizable lesson, if any, can be proposed?

End with one of these two explicit lines:

- LESSON: <the proposed lesson in one natural-language sentence>
- LESSON: no reusable lesson should be promoted from this case.

You will not receive the human's opinion; produce your own independent
review. Do not invent facts or sources that are not in the packet.
"""

# Manifest section keys, in render order: the original learning-case names
# and the kind-neutral aliases they map to. A manifest may use either set.
SECTIONS: list[tuple[str, str, tuple[str, ...]]] = [
    # (canonical key, section header, accepted manifest aliases)
    ("task", "Task / request", ("request", "task")),
    ("context", "Context / material / evidence", ("context", "evidence")),
    ("result", "Result (the evaluated output)", ("output", "result")),
    ("validation", "Validation evidence / preferred variant", ("revised", "validation")),
    ("sources", "Sources / resource pointers", ("sources",)),
]


def load_packet(case_dir: Path) -> dict:
    manifest_path = case_dir / "manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"no manifest.json in {case_dir}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"manifest.json unreadable in {case_dir}: {exc}") from exc
    packet: dict = {"manifest": manifest, "case_dir": case_dir}
    for _canonical, _header, aliases in SECTIONS:
        for key in aliases:
            rel = manifest.get(key)
            if rel:
                f = case_dir / rel
                packet[key] = f.read_text(encoding="utf-8") if f.is_file() else "<missing>"
                break
    return packet


def render_prompt(packet: dict) -> str:
    m = packet["manifest"]
    kind = m.get("kind")
    role = (
        f"Deliverable kind: {kind}"
        if kind
        else "Deliverable kind: not declared — judge it from the material."
    )
    sections = []
    for _canonical, header, aliases in SECTIONS:
        body = "<missing>"
        for key in aliases:
            if key in packet:
                body = packet[key]
                break
        sections.append(f"## {header}\n{body}")
    return f"""# Review packet: {m["case_id"]}

{role}

""" + "\n\n".join(sections) + f"""

---
{REVIEW_PROMPT}"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--case", required=True, type=Path, help="packet directory (e.g. learning/cases/<id>)"
    )
    ap.add_argument(
        "--prompt-only",
        action="store_true",
        help="print the prompt and exit (no model call)",
    )
    args = ap.parse_args()

    case_dir = args.case.resolve()
    if not case_dir.is_dir():
        raise SystemExit(f"packet directory not found: {case_dir}")
    packet = load_packet(case_dir)
    prompt = render_prompt(packet)

    if args.prompt_only:
        print(prompt)
        return 0

    from zuaef_agent.config import AgentSettings
    from zuaef_agent.providers import resolve_model

    settings = AgentSettings.from_env()
    has_credentials = bool(
        settings.openai_base_url and settings.openai_api_key
    ) or bool(__import__("os").getenv("OPENAI_API_KEY"))
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
