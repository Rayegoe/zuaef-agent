"""P0.1 volume semantic validator for ZUAEF quant (spec v2.0 03_DATA_EXECUTION_TRUTH.md).

Proves whether live quote volume and the historical cached volume share one
canonical unit across the active candidate universe, and records the exact
inputs (live raw volume, normalization, recent cached volumes, 20d average,
recomputed volume ratio) so any run can be recalculated from the evidence file.

Method (deterministic, host-owned, no LLM):
- cached unit inference per symbol from the symbol's own recent rows:
  amount / (volume * close) clusters at ~1 when volume is in shares (股) and
  at ~100 when volume is in lots (手) — self-consistent because amount is
  raw CNY and recent qfq closes equal raw closes;
- same-date cross-check when the live quote date equals the last cached
  date (both are the Tencent source, so at the close they must agree after
  unit normalization);
- volume_ratio_20d recomputed both as the live scan computes it today
  (live shares / cached MA20) and unit-consistently (denominator x factor).

Verdict:
- FAIL   BROKEN_VOLUME_UNIT: both units present in the sampled universe —
  the historical cache has no canonical unit (live trigger must fail closed,
  strategy optimization stops per spec P0.1);
- WARN   units uniform but a same-date cross-check failed or a symbol could
  not be classified;
- PASS   one canonical unit and every datable cross-check consistent.

    .venv-quant/bin/python tools/quant_validate_semantics.py [--min-sample 20]

Exit codes: 0 PASS/WARN, 1 FAIL, 2 insufficient evidence.
Evidence: workspace/artifacts/quant/semantic/semantic_proof_<UTC>.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from quant_core import TZ_SHANGHAI, read_cache
from quant_live_scan import (
    ACTIVE_SYMBOLS_PATH,
    fetch_batch_quotes,
    load_active_symbols,
)

CACHE_DIR = Path("data/quant-cache")
EVIDENCE_DIR = Path("workspace/artifacts/quant/semantic")

CROSS_CHECK_TOLERANCE = (0.9, 1.1)  # same source, same date: must agree after normalization
SHARE_FACTOR_MAX = 10.0  # amount/(volume*close): ~1 -> shares, ~100 -> lots


def classify_cached_unit(hist) -> tuple[str, float | None]:
    """Infer the cached volume unit from the symbol's own recent rows.

    Returns (unit, factor) where factor is amount/(volume*close) — the
    multiplier that converts cached volume to shares. unit is "share",
    "lot", or "unknown" (no usable amount data).
    """
    if hist is None or "amount" not in hist.columns or len(hist) == 0:
        return "unknown", None
    recent = hist.tail(5)
    factors = [
        float(row["amount"]) / (float(row["volume"]) * float(row["close"]))
        for _, row in recent.iterrows()
        if float(row["volume"]) > 0 and float(row["close"]) > 0 and float(row["amount"]) > 0
    ]
    if not factors:
        return "unknown", None
    factor = statistics.median(factors)
    if factor >= SHARE_FACTOR_MAX:
        return "lot", factor
    return "share", factor


def validate_symbol(symbol: str, quote: dict | None, hist) -> dict:
    """One symbol's semantic record: unit inference + ratio recomputation."""
    row: dict = {"symbol": symbol}
    unit, factor = classify_cached_unit(hist)
    row["cached_volume_unit"] = unit
    row["cached_unit_factor_to_shares"] = round(factor, 3) if factor is not None else None

    if hist is None or len(hist) < 21:
        row["skip_reason"] = "insufficient_history"
        return row
    hist = hist.sort_values("date")
    recent_volumes = [float(v) for v in hist["volume"].tail(3)]
    ma20 = float(hist["volume"].tail(20).mean())
    row["cached_recent_volumes"] = [round(v, 1) for v in recent_volumes]
    row["cached_last_date"] = str(hist["date"].iloc[-1])
    row["cached_volume_ma20"] = round(ma20, 1)

    if quote is None or quote.get("price", 0) <= 0:
        row["skip_reason"] = "no_quote"
        return row
    live_shares = float(quote["volume"])  # fetch_batch_quotes already normalized 手 -> shares
    row["live_raw_volume_lots"] = round(live_shares / 100.0, 1)
    row["live_normalization"] = "tencent field6 lots * 100 -> shares"
    row["live_volume_shares"] = round(live_shares, 1)
    row["quote_date"] = quote.get("date", "")

    if unit == "unknown":
        row["skip_reason"] = "unit_unclassifiable"
        return row

    factor_to_shares = factor if unit == "lot" else 1.0
    row["volume_ratio_as_scan_computes"] = round(live_shares / ma20, 3) if ma20 > 0 else None
    row["volume_ratio_unit_consistent"] = (
        round(live_shares / (ma20 * factor_to_shares), 3) if ma20 > 0 else None
    )

    if row["quote_date"] == row["cached_last_date"]:
        expected_cached_shares = recent_volumes[-1] * factor_to_shares
        ratio = live_shares / expected_cached_shares if expected_cached_shares > 0 else None
        lo, hi = CROSS_CHECK_TOLERANCE
        row["same_date_cross_check"] = {
            "live_vs_cached": round(ratio, 4) if ratio is not None else None,
            "consistent": bool(ratio is not None and lo <= ratio <= hi),
        }
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-sample", type=int, default=20, help="spec P0.1 minimum sample")
    args = parser.parse_args()

    started = time.perf_counter()
    try:
        symbols, as_of = load_active_symbols(ACTIVE_SYMBOLS_PATH)
    except Exception as exc:  # noqa: BLE001 — loud failure, never an empty verdict
        print(f"FATAL: active universe unreadable: {exc}", file=sys.stderr)
        return 2
    symbols = sorted(symbols)
    if len(symbols) < args.min_sample:
        print(
            f"FATAL: sample {len(symbols)} < required {args.min_sample}; "
            "rebuild the candidate pool first",
            file=sys.stderr,
        )
        return 2

    quotes = fetch_batch_quotes(symbols)

    rows = []
    for symbol in symbols:
        hist, _meta = read_cache("daily", f"{symbol}_qfq", CACHE_DIR)
        rows.append(validate_symbol(symbol, quotes.get(symbol), hist))

    classified = [r for r in rows if r.get("cached_volume_unit") in ("share", "lot")]
    units = {r["cached_volume_unit"] for r in classified}
    cross_checks = [r["same_date_cross_check"] for r in rows if r.get("same_date_cross_check")]
    cross_failed = [c for c in cross_checks if not c["consistent"]]
    skipped = [r for r in rows if r.get("skip_reason")]
    unit_counts = {u: sum(1 for r in classified if r["cached_volume_unit"] == u) for u in sorted(units)}

    if not classified:
        status, reason = "INSUFFICIENT_EVIDENCE", "no symbol classifiable (no cached amount data)"
    elif len(units) > 1:
        status = "FAIL"
        reason = (
            "BROKEN_VOLUME_UNIT: historical cached volume has no canonical unit — "
            + ", ".join(f"{u} n={unit_counts[u]}" for u in sorted(units))
            + "; live trigger volume clause must fail closed (spec P0.1)"
        )
    elif cross_failed or skipped:
        status = "WARN"
        reason = "unit uniform but cross-check failures or unclassified symbols present"
    else:
        status = "PASS"
        reason = f"single canonical unit ({next(iter(units))}) and all cross-checks consistent"

    mismatched_ratios = [
        {"symbol": r["symbol"], "volume_ratio_as_scan_computes": r.get("volume_ratio_as_scan_computes")}
        for r in rows
        if r.get("volume_ratio_unit_consistent") is not None
        and r.get("volume_ratio_as_scan_computes") is not None
        and abs(r["volume_ratio_as_scan_computes"] / r["volume_ratio_unit_consistent"] - 1) > 0.5
    ]

    evidence = {
        "spec": "zuaef-quant-final-spec-v2.0 P0.1",
        "as_of": datetime.now(TZ_SHANGHAI).isoformat(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "universe": "candidate_pool_active",
        "universe_source_path": str(ACTIVE_SYMBOLS_PATH),
        "universe_as_of": as_of,
        "sample_size": len(symbols),
        "classified": len(classified),
        "skipped": [{"symbol": r["symbol"], "reason": r.get("skip_reason")} for r in skipped],
        "cached_unit_counts": unit_counts,
        "same_date_cross_checks": len(cross_checks),
        "same_date_cross_check_failures": len(cross_failed),
        "scan_ratio_mismatch_gt_50pct": mismatched_ratios,
        "status": status,
        "reason": reason,
        "quote_source": "qt.gtimg.cn batch quote (Tencent); history: local cache of akshare stock_zh_a_hist_tx",
        "symbols": rows,
    }

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = EVIDENCE_DIR / f"semantic_proof_{stamp}.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=1), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": status,
                "sample": len(symbols),
                "classified": len(classified),
                "cached_unit_counts": unit_counts,
                "cross_check_failures": len(cross_failed),
                "scan_ratio_mismatches": len(mismatched_ratios),
                "reason": reason,
                "evidence": str(out),
                "elapsed_s": round(time.perf_counter() - started, 1),
            },
            ensure_ascii=False,
        )
    )
    return 0 if status in ("PASS", "WARN") else 1


if __name__ == "__main__":
    sys.exit(main())
