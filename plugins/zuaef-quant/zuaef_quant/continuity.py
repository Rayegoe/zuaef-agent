"""Shared market-session and continuity projection for Quant operator paths.

Stdlib-only: used by the plugin bridge (daily continuity verdict and recovery
evidence) without importing the root dashboard renderer. The verdict rule
mirrors the dashboard's M1 continuity verdict so the bridge does not define a
second threshold. The full dashboard renderer remains an operator surface until
P6; this module owns the small production projection the bridge needs.
"""

from __future__ import annotations

import json
from datetime import datetime
from datetime import time as dtime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from .validation import forward_evidence_counts

TZ_SH = ZoneInfo("Asia/Shanghai")
SESSION_AM = (dtime(9, 30), dtime(11, 30))
SESSION_PM = (dtime(13, 0), dtime(15, 0))

#: soak statuses that prove an in-session pass actually scanned the universe.
SOAK_IN_SESSION_STATUSES = {"NO_TRADE", "ALERTS", "SCANNED"}
#: heartbeat age bound while the session clock expects a live loop.
NOW_STALE_AFTER_S = 90


def market_phase(now: datetime) -> str:
    """A-share session clock (same rule as the monitor/renderer mirror)."""
    if now.tzinfo is not None:
        now = now.astimezone(TZ_SH)
    if now.weekday() >= 5:
        return "MARKET_CLOSED"
    t = now.time()
    if t < SESSION_AM[0]:
        return "PRE_OPEN"
    if t < SESSION_AM[1]:
        return "OPEN_AM"
    if t < SESSION_PM[0]:
        return "LUNCH_BREAK"
    if t < SESSION_PM[1]:
        return "OPEN_PM"
    return "MARKET_CLOSED"


def in_trading_session(now: datetime) -> bool:
    return market_phase(now) in {"OPEN_AM", "OPEN_PM"}


def _parse_ts(value: Any) -> datetime | None:
    """Tolerant artifact timestamp parse (naive values are market-local)."""
    try:
        parsed = datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=TZ_SH)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def load_latest_semantic_proof(semantic_dir: Path | str) -> dict[str, Any] | None:
    """Latest P0.1 volume-semantic proof, or None (absent/unreadable → UNKNOWN)."""
    proofs = sorted(Path(semantic_dir).glob("semantic_proof_*.json"))
    if not proofs:
        return None
    try:
        return json.loads(proofs[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def continuity_verdict(
    trading_dir: Path | str,
    *,
    semantic_dir: Path | str | None = None,
) -> str:
    """M1 continuity verdict from the canonical trading artifacts.

    Same rule as the business dashboard's ``load_real_trend`` verdict:
    semantic proof PASS + single-scan validity + at least one real in-session
    scan + at least one formal forward observation → PASS; any partial evidence
    → PARTIAL; no real evidence → NO_REAL_EVIDENCE.
    """
    trading_dir = Path(trading_dir)
    if semantic_dir is None:
        semantic_dir = Path("workspace/artifacts/quant/semantic")

    soak = _read_jsonl(trading_dir / "soak.jsonl")
    seen: set[tuple[Any, ...]] = set()
    in_session = 0
    for row in soak:
        ts = str(row.get("ts") or "")
        key = (
            ts,
            str(row.get("status")),
            row.get("events"),
            row.get("symbols"),
        )
        if not ts or key in seen:
            continue
        seen.add(key)
        if (
            row.get("status") in SOAK_IN_SESSION_STATUSES
            and (row.get("symbols") or 0) > 0
        ):
            in_session += 1

    forward = _read_json(trading_dir / "forward.json") or {}
    forward_count = forward_evidence_counts(forward)["count"]

    proof = load_latest_semantic_proof(semantic_dir)
    market_ok = bool(
        proof
        and proof.get("status") == "PASS"
        and str((proof.get("same_date_cross_check") or {}).get("status")) == "PASS"
    )
    sample = (proof.get("sample_size") or 0) if proof else 0

    oks = [market_ok, sample > 0, in_session > 0]
    return (
        "PASS"
        if all(oks) and forward_count > 0
        else "PARTIAL"
        if any(oks) or forward_count
        else "NO_REAL_EVIDENCE"
    )
