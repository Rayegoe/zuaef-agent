"""P0.1 volume semantic validator for ZUAEF quant (spec v2.0 03_DATA_EXECUTION_TRUTH.md).

Proves whether the historical cached volume of the active candidate universe
carries one canonical unit, and separately health-checks today's live quote
against the cached EOD truth.  Records the exact inputs (live raw volume,
normalization, recent cached volumes, 20d average, recomputed volume ratio)
so any run can be recalculated from the evidence file.

Two responsibilities, deliberately separated (P0.1-R4):

- ingest_semantics — the persistent data-boundary truth.  Cached unit
  inference per symbol from the symbol's own recent rows: amount /
  (volume * close) clusters at ~1 when volume is in shares (股) and at ~100
  when volume is in lots (手); the cache contract (schema, normalization,
  rows, date_range) must be current.  A proven canonical share cache is a
  standing PASS basis and does not depend on today's quote being comparable.

- same_date_cross_check — today's quote health check.  When the live quote
  date equals the last cached date (both Tencent source, at the close they
  must agree after unit normalization).  During trading hours today's EOD
  bar is legitimately not in the cache yet -> PENDING, recorded as such and
  never allowed to downgrade the persistent proof; an inconsistent
  cross-check is a detectable quote anomaly -> FAIL.

Overall verdict (drives the live fail-closed gate):
- FAIL                  broken canonical unit (mixed or uniform lot), or a
                        detectable quote anomaly (inconsistent cross-check);
- INSUFFICIENT_EVIDENCE cache canonical truth itself unproven (missing/
                        invalid cache contract, unclassifiable unit,
                        coverage gap);
- PASS                  canonical share volume proven under current cache
                        contracts — quote health may be PASS or PENDING.

    .venv-quant/bin/python tools/quant_validate_semantics.py [--min-sample 20]

Exit codes: 0 PASS, 1 otherwise.
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

import pandas as pd
from quant_core import TZ_SHANGHAI, history_cache_is_current, read_cache
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


def validate_symbol(symbol: str, quote: dict | None, hist, meta: dict | None = None) -> dict:
    """One symbol's semantic record: unit inference + ratio + quote health.

    quote_health is today's quote check only — it never feeds the persistent
    ingest verdict (P0.1-R4): "today's EOD bar not in cache" must not read
    as "historical volume semantics unknown".
    """
    row: dict = {"symbol": symbol}
    if hist is None or meta is None:
        row["cache_contract_current"] = False
        row["cached_volume_unit"] = "unknown"
        row["skip_reason"] = "no_cache" if hist is None else "cache_meta_missing"
        row["quote_health"] = {"status": "not_available", "reason": row["skip_reason"]}
        return row
    contract_current = history_cache_is_current(
        hist, meta, symbol=symbol, adjust="qfq", start_date="20180101"
    )
    row["cache_contract_current"] = contract_current
    if not contract_current:
        row["cached_volume_unit"] = "unknown"
        row["skip_reason"] = "cache_contract_invalid"
        row["quote_health"] = {"status": "not_available", "reason": "cache contract invalid"}
        return row
    unit, factor = classify_cached_unit(hist)
    row["cached_volume_unit"] = unit
    row["cached_unit_factor_to_shares"] = round(factor, 3) if factor is not None else None

    if hist is None or len(hist) < 21:
        row["skip_reason"] = "insufficient_history"
        row["quote_health"] = {"status": "not_available", "reason": "insufficient_history"}
        return row
    hist = hist.sort_values("date")
    recent_volumes = [float(v) for v in hist["volume"].tail(3)]
    ma20 = float(hist["volume"].tail(20).mean())
    row["cached_recent_volumes"] = [round(v, 1) for v in recent_volumes]
    cached_last = pd.to_datetime(hist["date"].iloc[-1], format="mixed", errors="coerce")
    row["cached_last_date"] = (
        cached_last.strftime("%Y%m%d") if not pd.isna(cached_last) else ""
    )
    row["cached_volume_ma20"] = round(ma20, 1)

    if quote is None or quote.get("price", 0) <= 0:
        row["skip_reason"] = "no_quote"
        row["quote_health"] = {"status": "not_available", "reason": "no_quote"}
        return row
    live_shares = float(quote["volume"])  # fetch_batch_quotes already normalized 手 -> shares
    row["live_raw_volume_lots"] = round(live_shares / 100.0, 1)
    row["live_normalization"] = "tencent field6 lots * 100 -> shares"
    row["live_volume_shares"] = round(live_shares, 1)
    quote_date = pd.to_datetime(str(quote.get("date", "")), format="mixed", errors="coerce")
    row["quote_date"] = (
        quote_date.strftime("%Y%m%d") if not pd.isna(quote_date) else ""
    )

    if unit == "unknown":
        row["skip_reason"] = "unit_unclassifiable"
        row["quote_health"] = {"status": "not_available", "reason": "unit_unclassifiable"}
        return row

    factor_to_shares = factor if unit == "lot" else 1.0
    row["volume_ratio_as_scan_computes"] = round(live_shares / ma20, 3) if ma20 > 0 else None
    row["volume_ratio_unit_consistent"] = (
        round(live_shares / (ma20 * factor_to_shares), 3) if ma20 > 0 else None
    )

    if not row["quote_date"]:
        row["quote_health"] = {"status": "not_available", "reason": "unparseable_quote_date"}
    elif pd.isna(cached_last):
        row["quote_health"] = {"status": "not_available", "reason": "unparseable_cached_date"}
    elif quote_date > cached_last:
        # Normal intraday state, not an evidence gap: the persistent cache
        # truth is checkable on its own; today's EOD bar arrives after close.
        row["quote_health"] = {
            "status": "pending_eod",
            "reason": "today's EOD bar not yet in cache — same-date cross-check pending",
        }
    elif quote_date < cached_last:
        row["quote_health"] = {"status": "quote_stale", "reason": "quote date behind cached last date"}
    else:
        expected_cached_shares = recent_volumes[-1] * factor_to_shares
        ratio = live_shares / expected_cached_shares if expected_cached_shares > 0 else None
        lo, hi = CROSS_CHECK_TOLERANCE
        consistent = bool(ratio is not None and lo <= ratio <= hi)
        row["quote_health"] = {
            "status": "consistent" if consistent else "inconsistent",
            "live_vs_cached": round(ratio, 4) if ratio is not None else None,
        }
    return row


def ingest_semantics_status(
    units: set[str], unit_counts: dict, expected_count: int, classified_count: int
) -> tuple[str, str]:
    """Persistent cache-truth verdict (P0.1-R4): independent of today's quote.

    PASS requires the single canonical unit to be SHARES with every sampled
    symbol classifiable under a current cache contract: live quotes are
    always shares (Tencent field6 x 100), so a uniform LOT cache is exactly
    the ~100x volume-ratio hazard and must FAIL, not pass.  An unverifiable
    cache (missing/invalid contract, unclassifiable unit, coverage gap) is
    INSUFFICIENT_EVIDENCE — suppress, never guess.
    """
    if expected_count <= 0 or classified_count != expected_count:
        return (
            "INSUFFICIENT_EVIDENCE",
            (
                f"cache coverage incomplete: classified {classified_count}/{expected_count} "
                "(cache contract invalid or unit unclassifiable)"
            ),
        )
    if not units:
        return "INSUFFICIENT_EVIDENCE", "no symbol classifiable (no cached amount data)"
    if len(units) > 1:
        detail = ", ".join(f"{u} n={unit_counts[u]}" for u in sorted(units))
        return "FAIL", (
            f"BROKEN_VOLUME_UNIT: historical cached volume has no canonical unit — {detail}; "
            "live trigger volume clause must fail closed (spec P0.1)"
        )
    unit = next(iter(units))
    if unit != "share":
        return "FAIL", (
            f"BROKEN_VOLUME_UNIT: all {unit_counts[unit]} sampled symbols cache volume in '{unit}' "
            "but live quotes are always shares — the volume ratio would be inflated ~100x; "
            "fail closed (spec P0.1, review 2026-09-03)"
        )
    return "PASS", (
        f"all {classified_count} sampled symbols cache canonical share volume "
        "under current cache contracts"
    )


def quote_health_status(healths: list[dict]) -> tuple[str, str]:
    """Today's quote health: PASS / FAIL / PENDING / NOT_AVAILABLE.

    A daily check, not the semantic proof: PENDING (today's EOD bar not in
    cache yet — every normal intraday run) never downgrades the persistent
    ingest verdict; an inconsistent same-date cross-check is a detectable
    quote anomaly and FAILs the run.
    """
    if not healths:
        return "NOT_AVAILABLE", "no quote health record evaluated"
    inconsistent = [h for h in healths if h.get("status") == "inconsistent"]
    if inconsistent:
        return "FAIL", (
            f"{len(inconsistent)} same-date quote/EOD cross-check(s) inconsistent — "
            "today's quote shows a detectable semantic anomaly; fail closed"
        )
    consistent = [h for h in healths if h.get("status") == "consistent"]
    if consistent:
        pending = len(healths) - len(consistent)
        return (
            "PASS",
            f"{len(consistent)} same-date cross-check(s) consistent; {pending} not aligned today",
        )
    return "PENDING", (
        "today's EOD bar not yet in cache — same-date cross-check pending; "
        "persistent ingest semantics stand on their own"
    )


def compose_overall(ingest: tuple[str, str], health: tuple[str, str]) -> tuple[str, str]:
    """Overall verdict consumed by the fail-closed live gate (P0.1-R4).

    FAIL wins (broken semantics or a quote anomaly), then the persistent
    ingest verdict; a PENDING / NOT_AVAILABLE quote health never demotes a
    proven ingest PASS.
    """
    ing_status, ing_reason = ingest
    h_status, h_reason = health
    if ing_status == "FAIL" or h_status == "FAIL":
        parts = [reason for status, reason in (ingest, health) if status == "FAIL"]
        return "FAIL", "; ".join(parts)
    if ing_status != "PASS":
        return ing_status, ing_reason
    return "PASS", f"{ing_reason}; same-date quote health {h_status}: {h_reason}"


def aggregate_rows(rows: list[dict], expected_count: int) -> dict:
    """Pure aggregation shared by main() and tests (single source of truth)."""
    classified = [r for r in rows if r.get("cached_volume_unit") in ("share", "lot")]
    units = {r["cached_volume_unit"] for r in classified}
    unit_counts = {u: sum(1 for r in classified if r["cached_volume_unit"] == u) for u in sorted(units)}
    healths = [
        r.get("quote_health") or {"status": "not_available", "reason": "not_evaluated"}
        for r in rows
    ]
    health_counts: dict[str, int] = {}
    for h in healths:
        health_counts[h["status"]] = health_counts.get(h["status"], 0) + 1
    skipped = [r for r in rows if r.get("skip_reason")]
    mismatched_ratios = [
        {"symbol": r["symbol"], "volume_ratio_as_scan_computes": r.get("volume_ratio_as_scan_computes")}
        for r in rows
        if r.get("volume_ratio_unit_consistent") is not None
        and r.get("volume_ratio_as_scan_computes") is not None
        and abs(r["volume_ratio_as_scan_computes"] / r["volume_ratio_unit_consistent"] - 1) > 0.5
    ]
    ingest = ingest_semantics_status(units, unit_counts, expected_count, len(classified))
    health = quote_health_status(healths)
    status, reason = compose_overall(ingest, health)
    return {
        "status": status,
        "reason": reason,
        "ingest": ingest,
        "health": health,
        "classified_count": len(classified),
        "unit_counts": unit_counts,
        "health_counts": health_counts,
        "skipped": skipped,
        "aligned_cross_checks": health_counts.get("consistent", 0) + health_counts.get("inconsistent", 0),
        "cross_check_failures": health_counts.get("inconsistent", 0),
        "mismatched_ratios": mismatched_ratios,
    }


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
        hist, meta = read_cache("daily", f"{symbol}_qfq", CACHE_DIR)
        rows.append(validate_symbol(symbol, quotes.get(symbol), hist, meta))

    agg = aggregate_rows(rows, len(symbols))
    status, reason = agg["status"], agg["reason"]

    evidence = {
        "spec": "zuaef-quant-final-spec-v2.0 P0.1",
        "as_of": datetime.now(TZ_SHANGHAI).isoformat(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "universe": "candidate_pool_active",
        "universe_source_path": str(ACTIVE_SYMBOLS_PATH),
        "universe_as_of": as_of,
        "sample_size": len(symbols),
        "validated_symbols": symbols,
        "classified": agg["classified_count"],
        "skipped": [{"symbol": r["symbol"], "reason": r.get("skip_reason")} for r in agg["skipped"]],
        "cached_unit_counts": agg["unit_counts"],
        "ingest_semantics": {"status": agg["ingest"][0], "reason": agg["ingest"][1]},
        "same_date_cross_check": {"status": agg["health"][0], "reason": agg["health"][1], **agg["health_counts"]},
        "same_date_cross_checks": agg["aligned_cross_checks"],
        "same_date_cross_check_failures": agg["cross_check_failures"],
        "scan_ratio_mismatch_gt_50pct": agg["mismatched_ratios"],
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
                "ingest_semantics": agg["ingest"][0],
                "same_date_cross_check": agg["health"][0],
                "sample": len(symbols),
                "classified": agg["classified_count"],
                "cached_unit_counts": agg["unit_counts"],
                "quote_health_counts": agg["health_counts"],
                "cross_check_failures": agg["cross_check_failures"],
                "scan_ratio_mismatches": len(agg["mismatched_ratios"]),
                "reason": reason,
                "evidence": str(out),
                "elapsed_s": round(time.perf_counter() - started, 1),
            },
            ensure_ascii=False,
        )
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
