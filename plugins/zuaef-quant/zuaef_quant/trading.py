"""Deterministic trading-state projection helpers shared by Quant surfaces.

The canonical trading ledger stays in ``workspace/artifacts/quant/trading/``
and is written only by the monitor host. This module owns the small derived
projection arithmetic that multiple monitor paths need from a position row —
today's mark-to-market P&L — so the formula cannot drift between the live
projection, exit alerts and closed-position settlement. It also owns the one
bounded read of that ledger, ``read_trading_snapshot``, so the model-facing
toolset and the operator CLI project the same artifacts through a single
deterministic read path instead of two drifting implementations.

The arithmetic helpers perform no I/O and no state mutation;
``read_trading_snapshot`` is the only reader here. The module stays
stdlib-only (no pandas/pydantic-ai) so every surface can import it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .freshness import derive_freshness, now_market
from .validation import compute_validation_accounting

__all__ = ["mark_to_market", "position_pnl", "read_trading_snapshot"]


def position_pnl(
    position: dict[str, Any],
    price: float,
    *,
    shares: int | None = None,
) -> float:
    """Realized/unrealized P&L for one position, rounded like the ledger.

    ``position`` is a canonical position row; ``shares`` lets the SELL path
    price the actual closing quantity while the live mark uses the position's
    own quantity. Missing/non-numeric fields fail loudly instead of becoming
    a fabricated zero.
    """
    quantity = int(position["shares"] if shares is None else shares)
    return round((float(price) - float(position["entry_price"])) * quantity, 2)


def mark_to_market(position: dict[str, Any], price: float) -> dict[str, Any]:
    """The monitor's live-position mark: current price and unrealized P&L.

    ``get_positions`` and the broad compatibility projection read this mark
    from ``state.json`` after the monitor writes it; they never recompute it.
    """
    return {"price": round(float(price), 3), "pnl": position_pnl(position, price)}


def _read_json(path: Path, default):
    """Tolerant canonical-artifact read: absent/corrupt -> the default, never
    a fabricated business state."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _read_jsonl_tail(path: Path, limit: int) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines[-limit:]:
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _read_jsonl(path: Path) -> list[dict]:
    """Full append-only stream read for ledger accounting (soak/alerts are
    bounded by market days, ~hundreds of bytes per row)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _resolve_last_scan_at(business_last_scan: Path, soak: list[dict]) -> str | None:
    """Timestamp of the last completed scan, from canonical artifacts.

    ``business/last_scan.json`` is the retired one-key daily script's metadata
    record (pre-M1); soak records that actually scanned symbols are the
    monitor's session-side evidence. Both writers use ``+08:00`` ISO stamps,
    so the newer one is the lexicographic max. ``None`` means no scan
    evidence is visible — freshness treats that honestly (STALE does not
    depend on it), never as "no scan ever happened".
    """
    candidates = []
    business = _read_json(business_last_scan, {})
    if isinstance(business.get("as_of"), str):
        candidates.append(business["as_of"])
    for record in reversed(soak):
        if (record.get("symbols") or 0) > 0 and isinstance(record.get("ts"), str):
            candidates.append(record["ts"])
            break
    return max(candidates) if candidates else None


def read_trading_snapshot(workspace_root: Path) -> dict[str, Any]:
    """Single deterministic read of the canonical trading artifacts.

    The one projection authority shared by the model-facing toolset and the
    operator CLI; neither re-implements it. Observe tools select a bounded
    block from this snapshot; the snapshot itself never writes, never
    recomputes market state, and never invents a value that the artifacts do
    not contain. Keeping one read path prevents narrow tools from drifting
    away from the broad compatibility projection.
    """
    trading = workspace_root / "artifacts" / "quant" / "trading"
    state = _read_json(trading / "state.json", {})
    positions = _read_json(trading / "positions.json", {"open": [], "closed": []})
    forward = _read_json(trading / "forward.json", {"observations": []})
    soak = _read_jsonl_tail(trading / "soak.jsonl", 50)
    alerts = _read_jsonl_tail(trading / "alerts.jsonl", 20)
    events = [
        {k: a.get(k) for k in ("ts", "type", "symbol", "what", "why", "price", "venue")}
        for a in alerts
    ]
    now = now_market()
    validation_accounting = compute_validation_accounting(
        positions=positions,
        forward=forward,
        soak_rows=_read_jsonl(trading / "soak.jsonl"),
        alerts=_read_jsonl(trading / "alerts.jsonl"),
        as_of=now.date(),
    )
    last_scan_at = _resolve_last_scan_at(
        workspace_root / "artifacts" / "quant" / "business" / "last_scan.json",
        soak,
    )
    freshness = derive_freshness(
        now=now,
        latest_market_data_date=state.get("day"),
        last_scan_at=last_scan_at,
    )
    return {
        "trading_dir": trading,
        "state": state,
        "positions": positions,
        "forward": forward,
        "soak": soak,
        "alerts": alerts,
        "events": events,
        "validation_accounting": validation_accounting,
        "last_scan_at": last_scan_at,
        "freshness": freshness,
        "now": now,
    }
