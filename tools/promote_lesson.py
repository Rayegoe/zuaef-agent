"""Human-gated, intervention-neutral promotion (v1.2 T011, MK v0.1 T005/T006).

Promotion is NOT automatic. This tool reads one case packet's
``human-review.md``; only when the human explicitly ACCEPTS a lesson does it
produce a promotion candidate under ``learning/promotions/``.

Intervention-neutral (Method Kernel v0.1): a promoted result may be nothing
at all, a prompt line, an example, a test, a tool/plugin/data fix, a skill,
an architecture fix — or a RETIREMENT candidate (simplify/replace/delete an
existing asset). Deleting scaffolding that proved no marginal value is a
successful learning outcome, not a failure. The human review may declare the
intervention with an optional ``intervention:`` line and the disposition
(``disposition: keep|simplify|replace|delete|retirement-candidate``); both
are recorded verbatim — the tool never classifies on its own and never
auto-deletes anything.

Usage:

    uv run python tools/promote_lesson.py --case learning/cases/<case-id> [--dry-run]

Contract (QUALITY_LOOP §5/§8, MK v0.1 §Learning & Promotion):

- human review is authoritative; the human may ACCEPT / REJECT / EDIT / PARTIAL;
- no auto-promotion from an LLM "high confidence";
- the promoted unit is intervention-neutral (see above);
- promotion lands as a versionable asset (Skill change / example pack item /
  tool/plugin change / deletion proposal), independently reversible by
  normal version control.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROMOTIONS = REPO / "learning" / "promotions"

ACCEPT_MARKERS = ("ACCEPT", "PROMOTE", "已采纳", "采纳", "接受")


def _human_review(case_dir: Path) -> str:
    review = case_dir / "human-review.md"
    if not review.is_file():
        raise SystemExit(
            f"no human-review.md in {case_dir} — promotion requires explicit "
            "human review (ACCEPT/EDIT/PARTIAL) before anything is promoted"
        )
    text = review.read_text(encoding="utf-8")
    # Anti-impersonation (T012): an ACCEPT string is not human authority by
    # itself. No tool may write human-review.md (static guard in
    # test_learning_cases.py), and a human review that is a copy of the LLM
    # review is refused here — the two must be independently authored.
    llm_review = case_dir / "llm-review.md"
    if llm_review.is_file():
        llm_text = llm_review.read_text(encoding="utf-8")
        normalized_human = "".join(text.split())
        normalized_llm = "".join(llm_text.split())
        if normalized_human == normalized_llm or (
            len(normalized_llm) > 200 and normalized_llm in normalized_human
        ):
            raise SystemExit(
                "human-review.md is a copy of llm-review.md — an LLM-written "
                "ACCEPT cannot impersonate human authority. Edit the human "
                "review by hand (it may quote the LLM review, but must carry "
                "the human's own decision and comments)."
            )
    return text


def _decide(text: str) -> tuple[bool, str]:
    """Explicit human decision only: a line containing an accept marker
    wins; any explicit reject (REJECT) or a missing decision refuses."""
    for line in text.splitlines():
        if line.strip().startswith(("REJECT", "拒绝")):
            return False, "human explicitly rejected the lesson"
    for line in text.splitlines():
        upper = line.strip().upper()
        if any(marker.upper() in upper for marker in ACCEPT_MARKERS):
            return True, "human explicitly accepted the lesson"
    return False, "no explicit ACCEPT decision found; nothing is promoted"


def _human_marker(text: str, name: str) -> str | None:
    """Verbatim value of an optional ``<name>:`` line in the human review.

    Markers are read ONLY from human-review.md (whose anti-impersonation
    guard runs first), so they carry human authority by construction. The
    value is never validated against a vocabulary and never derived by the
    tool — the human decides, the tool records.
    """
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith(f"{name}:"):
            value = stripped.split(":", 1)[1].strip()
            return value or None
    return None


def _promotion_payload(case_dir: Path, review_text: str, decision: str) -> dict:
    try:
        manifest = json.loads((case_dir / "manifest.json").read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"manifest.json unreadable in {case_dir}: {exc}") from exc
    revised_rel = manifest.get("revised")
    revised = (
        (case_dir / revised_rel).read_text(encoding="utf-8")
        if revised_rel and (case_dir / revised_rel).is_file()
        else None
    )
    payload = {
        "schema_version": 1,
        "case_id": manifest["case_id"],
        "promoted_at": "see-version-control",  # promotion is a committed asset
        "decision": decision,
        "decision_source": (
            "human-review.md — hand-authored file; no tool may write it "
            "(T012 anti-impersonation rule)"
        ),
        # The promoted unit: preserve the raw human text + the accepted
        # output. Derived labels are NOT promoted.
        "lesson": review_text,
        "exemplar": revised,
    }
    # Optional intervention-neutral fields (MK v0.1 T005/T006): verbatim
    # human declarations. Absent markers keep the v1 payload shape unchanged.
    for field in ("intervention", "disposition"):
        value = _human_marker(review_text, field)
        if value:
            payload[field] = value
    return payload


def promote(case_dir: Path, *, dry_run: bool = False) -> Path:
    review_text = _human_review(case_dir)
    accepted, decision = _decide(review_text)
    if not accepted:
        raise SystemExit(
            f"promotion refused for {case_dir.name}: {decision}. "
            "No automatic promotion — fix human-review.md with an explicit "
            "ACCEPT first."
        )
    payload = _promotion_payload(case_dir, review_text, decision)
    target = PROMOTIONS / f"{case_dir.name}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        print(f"[dry-run] would promote {case_dir.name} -> {target}")
        print(json.dumps(payload, ensure_ascii=False, indent=2)[:800])
        return target
    tmp = target.with_name(f"{target.name}.{__import__('uuid').uuid4().hex}.tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        shutil.move(str(tmp), str(target))
    except OSError as exc:
        raise SystemExit(f"could not write promotion {target}: {exc}") from exc
    print(f"promoted {case_dir.name} -> {target}")
    print(
        "NEXT: turn the accepted intervention into a versionable change — a "
        "new asset, or keep/simplify/replace/delete of an existing one "
        "(retirement candidate included; nothing is auto-deleted) — then "
        "compare later output (T012)."
    )
    return target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True, type=Path)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    promote(args.case.resolve(), dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
