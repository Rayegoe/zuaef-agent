"""Research artifacts — durable research packets and customer evidence
(quant research service v0.2, T011/T012).

A Research Packet is a BUSINESS research result, not execution state: no
tool traces, no token usage, no prompts, no model reasoning. Customer-
reported claims are stored as CUSTOMER_REPORTED / UNVERIFIED evidence with
provenance; they may influence research attention and hypotheses but can
never mutate the candidate pool, READY/NEAR state, strategy or fills.

Layout (file-native, per analysis scope — the same opaque binding the
watchlist uses, so a bound Case's research stays isolated):

    workspace/artifacts/quant/research/<scope>/<symbol>/<as_of>.json
    workspace/artifacts/quant/research/<scope>/<symbol>/customer-evidence.jsonl

Written only by this module (host tool); never committed to Git.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from .watchlist import normalize_symbol, scope_slug

RESEARCH_DIRNAME = Path("artifacts") / "quant" / "research"
CUSTOMER_EVIDENCE_FILENAME = "customer-evidence.jsonl"
RESEARCH_STATUSES = ("COMPLETE", "PARTIAL", "INSUFFICIENT_EVIDENCE")
PACKET_MAX_ITEMS = 12
ITEM_MAX_CHARS = 400
THESIS_MAX_CHARS = 2000
EVIDENCE_MAX_CHARS = 600
EVIDENCE_TAIL_LIMIT = 10


class ResearchError(ValueError):
    """Raised for invalid packet/evidence input — user-facing message."""


def symbol_dir(directory: Path, scope: str, symbol: str) -> Path:
    return Path(directory) / scope_slug(scope) / symbol


def _cap_text(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _capped_list(values, limit: int = ITEM_MAX_CHARS) -> list[str]:
    items = [_cap_text(v, limit) for v in (values or []) if str(v or "").strip()]
    return items[:PACKET_MAX_ITEMS]


def save_packet(
    directory: Path,
    scope: str,
    symbol: str,
    *,
    research_status: str,
    thesis: str,
    coverage: list[str] | None = None,
    supporting_facts: list[str] | None = None,
    counter_evidence: list[str] | None = None,
    risks: list[str] | None = None,
    invalidation: str = "",
    scenarios: list[str] | None = None,
    unknowns: list[str] | None = None,
    source_references: list[str] | None = None,
    run_id: str | None = None,
) -> dict:
    """Persist one bounded research packet; returns write + read-back facts."""
    symbol = normalize_symbol(symbol)
    if research_status not in RESEARCH_STATUSES:
        raise ResearchError(f"research_status must be one of {RESEARCH_STATUSES}")
    as_of = _dt.datetime.now(_dt.UTC)
    packet = {
        "symbol": symbol,
        "as_of": as_of.isoformat(timespec="seconds"),
        "scope": scope,
        "research_status": research_status,
        "thesis": _cap_text(thesis, THESIS_MAX_CHARS),
        "invalidation": _cap_text(invalidation, ITEM_MAX_CHARS),
        "unknowns": _capped_list(unknowns),
        "recorded_by_run": run_id,
        "note": "prior hypothesis, never current market truth; re-verify before reuse",
    }
    for field in (
        "coverage",
        "supporting_facts",
        "counter_evidence",
        "risks",
        "scenarios",
        "source_references",
    ):
        packet[field] = _capped_list(locals()[field])

    target_dir = symbol_dir(directory, scope, symbol)
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = as_of.strftime("%Y%m%dT%H%M%SZ")
    path = target_dir / f"{stamp}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(packet, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)
    # read-back: a packet may only be claimed saved when the file proves it
    read_back = latest_packet(directory, scope, symbol)
    if not read_back or read_back.get("as_of") != packet["as_of"]:
        return {"saved": False, "error": "research packet write did not persist; do not claim success"}
    rel = Path(RESEARCH_DIRNAME) / scope_slug(scope) / symbol / path.name
    return {
        "saved": True,
        "file": rel.as_posix(),
        "as_of": packet["as_of"],
        "research_status": research_status,
        "note": packet["note"],
    }


def latest_packet(directory: Path, scope: str, symbol: str) -> dict | None:
    """Latest persisted packet for one symbol in one scope; None if absent."""
    target = symbol_dir(directory, scope, symbol)
    if not target.is_dir():
        return None
    packets = sorted(
        p for p in target.glob("*.json") if p.name != CUSTOMER_EVIDENCE_FILENAME
    )
    if not packets:
        return None
    try:
        return json.loads(packets[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def record_customer_evidence(
    directory: Path,
    scope: str,
    symbol: str,
    *,
    claim: str,
    source_hint: str = "",
    run_id: str | None = None,
) -> dict:
    """Append one customer-reported claim as UNVERIFIED evidence.

    Customer claims influence research attention and hypotheses; they never
    touch the candidate pool, READY/NEAR, strategy or fills."""
    symbol = normalize_symbol(symbol)
    claim = _cap_text(claim, EVIDENCE_MAX_CHARS)
    if not claim:
        raise ResearchError("customer evidence claim is empty")
    entry = {
        "recorded_at": _dt.datetime.now(_dt.UTC).isoformat(timespec="seconds"),
        "symbol": symbol,
        "kind": "CUSTOMER_REPORTED",
        "verification": "UNVERIFIED",
        "claim": claim,
        "source_hint": _cap_text(source_hint, ITEM_MAX_CHARS) or None,
        "recorded_by_run": run_id,
        "note": "may shape research attention/hypotheses; never strategy state",
    }
    target = symbol_dir(directory, scope, symbol)
    target.mkdir(parents=True, exist_ok=True)
    path = target / CUSTOMER_EVIDENCE_FILENAME
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    tail = read_customer_evidence(directory, scope, symbol)
    if not any(e.get("claim") == claim for e in tail):
        return {"recorded": False, "error": "evidence write did not persist"}
    rel = Path(RESEARCH_DIRNAME) / scope_slug(scope) / symbol / path.name
    return {
        "recorded": True,
        "verification": "UNVERIFIED",
        "file": rel.as_posix(),
        "note": entry["note"],
    }


def read_customer_evidence(directory: Path, scope: str, symbol: str) -> list[dict]:
    """Bounded recent tail of customer evidence (newest last)."""
    symbol = normalize_symbol(symbol)
    path = symbol_dir(directory, scope, symbol) / CUSTOMER_EVIDENCE_FILENAME
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines[-EVIDENCE_TAIL_LIMIT:]:
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows
