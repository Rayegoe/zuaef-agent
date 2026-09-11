"""Deterministic trading-state projection helpers shared by Quant surfaces.

The canonical trading ledger stays in ``workspace/artifacts/quant/trading/``
and is written only by the monitor host. This module owns the small derived
projection arithmetic that multiple monitor paths need from a position row —
today's mark-to-market P&L — so the formula cannot drift between the live
projection, exit alerts and closed-position settlement.

It is stdlib-only and performs no I/O and no state mutation.
"""

from __future__ import annotations

from typing import Any

__all__ = ["mark_to_market", "position_pnl"]


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
