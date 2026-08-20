"""Human-gated lesson promotion (v1.2 T011).

Promotion is NOT automatic. This tool reads one case packet's
``human-review.md``; only when the human explicitly ACCEPTS a lesson does it
produce a promotion candidate (a Skill change, an example-pack item, or a
plugin-fix recommendation) under ``learning/promotions/``.

Usage:

    uv run python tools/promote_lesson.py --case learning/cases/<case-id> [--dry-run]

Contract (QUALITY_LOOP §5/§8):

- human review is authoritative; the human may ACCEPT / REJECT / EDIT / PARTIAL;
- no auto-promotion from an LLM "high confidence";
- the promoted unit is one of: natural-language guideline, before/after pair,
  full accepted exemplar, or tool/plugin behavior correction;
- promotion lands as a versionable asset (Skill change / example pack item /
  plugin change), independently removable by normal version control.
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
    return review.read_text(encoding="utf-8")


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
    return {
        "schema_version": 1,
        "case_id": manifest["case_id"],
        "promoted_at": "see-version-control",  # promotion is a committed asset
        "decision": decision,
        # The promoted unit: preserve the raw human text + the accepted
        # output. Derived labels are NOT promoted.
        "lesson": review_text,
        "exemplar": revised,
    }


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
    print("NEXT: turn the accepted lesson into a versionable Skill / example "
          "pack item / plugin change, then compare later output (T012).")
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