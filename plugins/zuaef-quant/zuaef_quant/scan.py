"""Deterministic live-scan semantics shared by every Quant scan surface.

This module is the single production authority for the frozen entry-clause
decision (``entry_trigger``) and the normalized remaining-gap projection
(``entry_clause_gaps``). It is deliberately stdlib-only: the agent-side
plugin environment and the ``.venv-quant`` side environment both import it
without pulling pandas, requests or pydantic_ai.

It performs no fetching, no file I/O and no persistence. Callers own the
reality adapters (quotes / cached history / universe resolution) and pass the
already-computed timing inputs. The model owns interpretation; this module
only answers whether the deterministic frozen entry conditions hold.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "entry_clause_gaps",
    "entry_trigger",
    "evaluate_entry",
]


def entry_trigger(
    pullback: float,
    ratio: float,
    strength: float,
    *,
    entry_pullback_max: float,
    entry_volume_ratio_min: float,
) -> bool:
    """The frozen S3 entry decision: all three clauses must hold.

    ``pullback`` and ``ratio`` come from the date-aligned timing adapter
    (quote day T vs cached sessions strictly before T); ``strength`` is the
    quote's absolute change (price - prev_close). This exact boolean is the
    one production decision shared by ``run_live_scan`` / ``get_live_signals``
    and the monitor's READY layer.
    """
    return bool(
        pullback <= entry_pullback_max
        and ratio >= entry_volume_ratio_min
        and strength >= 0
    )


def entry_clause_gaps(
    pullback: float,
    ratio: float,
    strength: float,
    price: float,
    *,
    entry_pullback_max: float,
    entry_volume_ratio_min: float,
) -> dict[str, float]:
    """Normalized remaining gap to each frozen entry clause (>= 0; 0 = met).

    This is the deterministic projection used by the monitor's NEAR band and
    by ``get_symbol_context`` diagnostics. Missing/unknown inputs are never
    coerced here; callers fail closed before producing timing values.
    """
    return {
        "pullback": max(0.0, (pullback - entry_pullback_max) / abs(entry_pullback_max)),
        "volume": max(0.0, (entry_volume_ratio_min - ratio) / entry_volume_ratio_min),
        "strength": max(0.0, -strength / price) if price > 0 else 1.0,
    }


def evaluate_entry(
    pullback: float,
    ratio: float,
    strength: float,
    price: float,
    *,
    entry_pullback_max: float,
    entry_volume_ratio_min: float,
    near_band: float | None = None,
) -> dict[str, Any]:
    """One deterministic per-symbol scan evaluation.

    Returns the entry decision plus the clause-gap projection. When
    ``near_band`` is supplied, it also applies the monitor's NEAR rule
    (not triggered, but every gap within the band). No caller may re-derive
    these fields independently.
    """
    gaps = entry_clause_gaps(
        pullback,
        ratio,
        strength,
        price,
        entry_pullback_max=entry_pullback_max,
        entry_volume_ratio_min=entry_volume_ratio_min,
    )
    trigger = entry_trigger(
        pullback,
        ratio,
        strength,
        entry_pullback_max=entry_pullback_max,
        entry_volume_ratio_min=entry_volume_ratio_min,
    )
    near = bool(
        not trigger
        and near_band is not None
        and all(value <= near_band for value in gaps.values())
    )
    return {
        "trigger": trigger,
        "near": near,
        "clause_distances": gaps,
    }
