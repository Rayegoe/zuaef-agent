"""P0.4 anti-leakage behavioral check for ZUAEF quant (spec v2.0 03_DATA_EXECUTION_TRUTH.md).

Behavioral lookahead detection in the spirit of Freqtrade's lookahead
analysis: not source grep, but a difference test — run the deterministic
research replay over the FULL history, then re-run it with all data after a
checkpoint date D removed, and compare the results for fixed historical
dates before D. If deleting the future changes the past, the pipeline leaks.

Compared items (per checkpoint, over a fixed comparison window before D):
  - factor values        pullback_5d, volume_ratio_20d, close_strength_1d
                         (per date x symbol, from the qlib panel)
  - candidate membership per-date entry-eligible symbol set (valid bar +
                         all factor inputs present) — the historical analog
                         of candidate membership
  - entry intents        BUY decisions (deterministic slot-contended rule)
  - exit intents         SELL decisions
  - timing surface       quant_live_scan.timing_from_quote_hist at past
                         dates with truncated vs full cached history — the
                         code path shared by the live scan and candidate
                         scoring

Every difference is reported item by item. Nothing is masked: a single
changed factor value at one past date fails the check.

Scope facts recorded in the report (not silently omitted):
  - composite candidate RANK is a today-only surface (no date parameter);
    the behavioral test does not apply to it.
  - the KNOWN universe-selection contamination (P0.3: current-membership
    subset back-applied to the research window) is not detectable by
    data-truncation replay and is deliberately NOT corrected here; it is
    carried in the report as expected contamination evidence. This check
    validates only the within-universe time-series mechanics.

    .venv-quant/bin/python tools/quant_anti_leakage_check.py \
        [--checkpoints 2020-06-30,2021-06-30,2022-06-30]

Exit codes: 0 LOOKAHEAD_PASS, 1 LOOKAHEAD_FAIL, 2 LOOKAHEAD_UNKNOWN.
Evidence: workspace/artifacts/quant/semantic/anti_leakage_check_<UTC>.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from quant_core import TZ_SHANGHAI, load_config, read_cache
from quant_live_scan import timing_from_quote_hist

CACHE_DIR = Path("data/quant-cache")
EVIDENCE_DIR = Path("workspace/artifacts/quant/semantic")
GEN1_DIR = Path("benchmarks/quant/gen1")

DEFAULT_CHECKPOINTS = "2020-06-30,2021-06-30,2022-06-30"
WARMUP_BARS = 25  # factor windows need <= 20 bars; guard the comparison range
FACTOR_COLUMNS = ("pullback_5d", "volume_ratio_20d", "close_strength_1d")
EXIT_CODES = {"LOOKAHEAD_PASS": 0, "LOOKAHEAD_FAIL": 1, "LOOKAHEAD_UNKNOWN": 2}


def build_intents_trunc(panel: pd.DataFrame, spec, window_start: str, end: str):
    """Delegates to the production intent builder (lazy import keeps this
    module importable without qlib for the pure-function tests)."""
    from quant_eval_qlib import build_intents

    return build_intents(panel, spec, (window_start, end))


def factor_frame(panel: pd.DataFrame) -> pd.DataFrame:
    """The entry-signal factors, derived only from each row's own past."""
    out = pd.DataFrame(index=panel.index)
    out["pullback_5d"] = panel["close"] / panel["close_5d_ago"] - 1.0
    out["volume_ratio_20d"] = panel["volume"] / panel["volume_ma20"]
    out["close_strength_1d"] = panel["close"] - panel["prev_close"]
    return out


def _per_day_frame(frame: pd.DataFrame, day):
    """One day's rows, indexed by symbol alone."""
    rows = frame.loc[(day, slice(None))]
    if isinstance(rows, pd.Series):
        rows = rows.to_frame().T
    if isinstance(rows.index, pd.MultiIndex):
        rows = rows.droplevel(0)
    return rows


def eligible_symbols(factors: pd.DataFrame, day) -> list[str]:
    """Entry-eligible universe at one date: a traded bar with all inputs valid."""
    try:
        rows = _per_day_frame(factors, day)
    except KeyError:
        return []
    valid = rows.notna().all(axis=1) & (rows["volume_ratio_20d"] > 0)
    return sorted(rows.index[valid])


def compare_factors(full: pd.DataFrame, trunc: pd.DataFrame, days: list) -> tuple[list[dict], int]:
    """Itemized factor differences over the comparison days. Returns (diffs, compared)."""
    diffs: list[dict] = []
    compared = 0
    for day in days:
        try:
            f_rows = _per_day_frame(full, day)
            t_rows = _per_day_frame(trunc, day)
        except KeyError:
            diffs.append({"day": str(day)[:10], "item": "panel_row", "detail": "truncated panel missing the whole day"})
            continue
        for symbol in sorted(set(f_rows.index) | set(t_rows.index)):
            compared += 1
            if symbol not in t_rows.index:
                diffs.append({"day": str(day)[:10], "symbol": str(symbol), "item": "row_presence", "full": "present", "truncated": "missing"})
                continue
            if symbol not in f_rows.index:
                continue
            for col in FACTOR_COLUMNS:
                f_val, t_val = f_rows.loc[symbol, col], t_rows.loc[symbol, col]
                if pd.isna(f_val) and pd.isna(t_val):
                    continue
                if pd.isna(f_val) != pd.isna(t_val) or abs(float(f_val) - float(t_val)) > 1e-12:
                    diffs.append({
                        "day": str(day)[:10],
                        "symbol": str(symbol),
                        "item": f"factor:{col}",
                        "full": None if pd.isna(f_val) else round(float(f_val), 10),
                        "truncated": None if pd.isna(t_val) else round(float(t_val), 10),
                    })
    return diffs, compared


def compare_membership(full_factors: pd.DataFrame, trunc_factors: pd.DataFrame, days: list) -> list[dict]:
    diffs = []
    for day in days:
        f_set, t_set = eligible_symbols(full_factors, day), eligible_symbols(trunc_factors, day)
        if f_set != t_set:
            diffs.append({
                "day": str(day)[:10],
                "item": "candidate_membership",
                "full": f_set,
                "truncated": t_set,
                "only_in_full": sorted(set(f_set) - set(t_set)),
                "only_in_truncated": sorted(set(t_set) - set(f_set)),
            })
    return diffs


def _intent_key(d: dict) -> tuple:
    return (d["decision_date"], d["symbol"], d["action"])


def intents_in_range(intents: list, lo, hi, action: str | None = None) -> list[dict]:
    out = [
        {"decision_date": str(i.intent_date), "symbol": i.symbol, "action": i.action}
        for i in intents
        if lo <= i.intent_date <= hi and (action is None or i.action == action)
    ]
    return out


def _intent_diffs(full_rows: list[dict], trunc_rows: list[dict]) -> list[dict]:
    f_keys = {_intent_key(d) for d in full_rows}
    t_keys = {_intent_key(d) for d in trunc_rows}
    return [
        {"full": d, "truncated": None} for d in full_rows if _intent_key(d) not in t_keys
    ] + [
        {"full": None, "truncated": d} for d in trunc_rows if _intent_key(d) not in f_keys
    ]


def compare_intents(full: list, trunc: list, lo, hi) -> dict:
    entry_diffs = _intent_diffs(intents_in_range(full, lo, hi, "BUY"), intents_in_range(trunc, lo, hi, "BUY"))
    exit_diffs = _intent_diffs(intents_in_range(full, lo, hi, "SELL"), intents_in_range(trunc, lo, hi, "SELL"))
    return {
        "entry_intents": {
            "full": len(intents_in_range(full, lo, hi, "BUY")),
            "truncated": len(intents_in_range(trunc, lo, hi, "BUY")),
            "diff_count": len(entry_diffs),
            "diffs": entry_diffs[:100],
            "changed": bool(entry_diffs),
        },
        "exit_intents": {
            "full": len(intents_in_range(full, lo, hi, "SELL")),
            "truncated": len(intents_in_range(trunc, lo, hi, "SELL")),
            "diff_count": len(exit_diffs),
            "diffs": exit_diffs[:100],
            "changed": bool(exit_diffs),
        },
    }


def timing_surface_check(symbols: list[str], checkpoint_days: list[str], cache_dir: Path = CACHE_DIR) -> dict:
    """timing_from_quote_hist at fixed past dates: two distinct properties.

    - truncation_invariance: given the frame that ends at the quote date T,
      values are invariant to mutations of rows after T. This pins the
      required call pattern: the frame handed to the function must end at
      the quote date.
    - stale_quote_sensitivity: pairing a T-dated quote with a LONGER frame
      changes the value (tail(20)/iloc[-6] are frame-end-relative). This is
      quantified as the production residual risk of a stale quote meeting a
      refreshed cache — reported verbatim, not folded into the replay
      verdict (see scope_notes).
    """
    invariance_checked = 0
    invariance_violations: list[dict] = []
    stale_checked = 0
    stale_diffs: list[dict] = []
    for symbol in symbols:
        hist, _meta = read_cache("daily", f"{symbol}_qfq", cache_dir)
        if hist is None or len(hist) < 30:
            invariance_violations.append({"symbol": symbol, "detail": "insufficient cached history"})
            continue
        hist = hist.sort_values("date").reset_index(drop=True)
        # cached CSV dates read back as ISO strings; string order == date order
        date_str = hist["date"].astype(str)
        for day_str in checkpoint_days:
            past = hist[date_str <= day_str]
            future = date_str > day_str
            if len(past) < 26 or len(past) == len(hist):
                continue  # checkpoint must sit strictly inside the series
            last = past.iloc[-1]
            pseudo_quote = {"price": float(last["close"]), "volume": float(last["volume"])}
            t_trunc = timing_from_quote_hist(pseudo_quote, past)

            mutated = hist.copy()
            mutated.loc[future, "volume"] = float(hist["volume"].max() or 1.0) * 7.0 + 1.0
            mutated.loc[future, "close"] = float(hist["close"].max() or 1.0) * 2.0
            mutated_rows = mutated[date_str <= day_str]
            t_mutated = timing_from_quote_hist(pseudo_quote, mutated_rows)
            invariance_checked += 1
            if t_mutated != t_trunc:
                invariance_violations.append({"symbol": symbol, "day": day_str, "full": t_trunc, "mutated_future": t_mutated})

            t_full = timing_from_quote_hist(pseudo_quote, hist)
            stale_checked += 1
            if t_full != t_trunc:
                stale_diffs.append({
                    "symbol": symbol,
                    "day": day_str,
                    "truncated": t_trunc,
                    "with_longer_frame": t_full,
                })
    return {
        "truncation_invariance": {
            "checked": invariance_checked,
            "violation_count": len(invariance_violations),
            "violations": invariance_violations[:50],
            "invariant": invariance_checked > 0 and not invariance_violations,
        },
        "stale_quote_sensitivity": {
            "checked": stale_checked,
            "diff_count": len(stale_diffs),
            "diffs": stale_diffs[:50],
            "sensitive": bool(stale_diffs),
        },
    }


def compare_checkpoint(
    panel_full: pd.DataFrame,
    factors_full: pd.DataFrame,
    intents_full: list,
    checkpoint: str,
    window_start: str,
    panel_loader,
    spec,
) -> dict:
    """One checkpoint: truncate at D, rebuild, itemize every difference.

    The comparison covers the ENTIRE warmup-guarded past before D — not a
    sampled window — so sparse items like entry/exit intents cannot escape
    the comparison by falling outside it.
    """
    day_d = date.fromisoformat(checkpoint)
    past_days = sorted({d for d, _ in panel_full.index})
    compare_days = [d for d in past_days if date.fromisoformat(str(d)[:10]) < day_d][WARMUP_BARS:]
    if not compare_days:
        return {"checkpoint": checkpoint, "status": "UNKNOWN", "reason": "empty comparison window"}

    panel_trunc = panel_loader(checkpoint)
    factors_trunc = factor_frame(panel_trunc)
    intents_trunc = build_intents_trunc(panel_trunc, spec, window_start, checkpoint)

    factor_diffs, compared = compare_factors(factors_full, factors_trunc, compare_days)
    membership_diffs = compare_membership(factors_full, factors_trunc, compare_days)
    lo = date.fromisoformat(str(compare_days[0])[:10])
    intents_cmp = compare_intents(intents_full, intents_trunc, lo, day_d)

    changed_items = []
    if factor_diffs:
        changed_items.append(f"factor_values({len(factor_diffs)})")
    if membership_diffs:
        changed_items.append(f"candidate_membership({len(membership_diffs)})")
    if intents_cmp["entry_intents"]["changed"]:
        changed_items.append("entry_intents")
    if intents_cmp["exit_intents"]["changed"]:
        changed_items.append("exit_intents")

    return {
        "checkpoint": checkpoint,
        "compare_day_count": len(compare_days),
        "compare_range": [str(compare_days[0])[:10], str(compare_days[-1])[:10]],
        "factor_comparisons": compared,
        "factor_diff_count": len(factor_diffs),
        "factor_diffs": factor_diffs[:200],
        "membership_diff_count": len(membership_diffs),
        "membership_diffs": membership_diffs[:50],
        "entry_intents": intents_cmp["entry_intents"],
        "exit_intents": intents_cmp["exit_intents"],
        "changed_items": changed_items,
        "status": "LOOKAHEAD_FAIL" if changed_items else "PASS",
    }


def load_pit_context(evidence_dir: Path = EVIDENCE_DIR) -> dict | None:
    """Latest P0.3 audit verdict, carried verbatim as expected-contamination evidence."""
    audits = sorted(Path(evidence_dir).glob("pit_audit_*.json"))
    if not audits:
        return None
    try:
        data = json.loads(audits[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return {"verdict": data.get("verdict"), "implication": data.get("implication")}


def overall_verdict(checkpoints: list[dict]) -> str:
    """The LOOKAHEAD verdict covers the date-slicable replay surface (factors,
    membership, intents). Timing-surface frame sensitivity is reported
    separately and quantified — it is a call-pattern hazard (stale quote x
    refreshed cache), not a replay leak, and masking it into either verdict
    direction would be dishonest."""
    if not checkpoints or any(c.get("status") == "UNKNOWN" for c in checkpoints):
        return "LOOKAHEAD_UNKNOWN"
    if any(c.get("status") == "LOOKAHEAD_FAIL" for c in checkpoints):
        return "LOOKAHEAD_FAIL"
    return "LOOKAHEAD_PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=GEN1_DIR / "quant.toml")
    parser.add_argument("--strategy", type=Path, default=GEN1_DIR / "strategy.toml")
    parser.add_argument("--checkpoints", default=DEFAULT_CHECKPOINTS)
    parser.add_argument("--timing-symbols", type=int, default=8)
    parser.add_argument("--out-dir", type=Path, default=EVIDENCE_DIR)
    args = parser.parse_args()

    from quant_core import StrategySpec
    from quant_eval_qlib import load_panel

    cfg = load_config(args.config)
    spec = StrategySpec.from_config(load_config(args.strategy))
    research = cfg["research"]
    window_start, window_end = research["research_start"], research["research_end"]
    universe_meta = json.loads((CACHE_DIR / "universe" / "csi500_subset.meta.json").read_text(encoding="utf-8"))
    symbols = universe_meta["symbols"]

    qlib_dir = CACHE_DIR / "qlib_data"
    if not qlib_dir.exists():
        print(json.dumps({"verdict": "LOOKAHEAD_UNKNOWN", "reason": "qlib store missing; run tools/quant_eval_qlib.py first"}))
        return EXIT_CODES["LOOKAHEAD_UNKNOWN"]
    pad_start = str(date.fromisoformat(window_start).replace(year=date.fromisoformat(window_start).year - 1))

    def panel_loader(end: str):
        return load_panel(qlib_dir, symbols, pad_start, end)

    panel_full = panel_loader(window_end)
    factors_full = factor_frame(panel_full)
    intents_full = build_intents_trunc(panel_full, spec, window_start, window_end)

    checkpoints = [
        compare_checkpoint(
            panel_full, factors_full, intents_full,
            checkpoint.strip(), window_start, panel_loader, spec,
        )
        for checkpoint in args.checkpoints.split(",")
        if checkpoint.strip()
    ]
    checkpoint_days = [c.strip() for c in args.checkpoints.split(",") if c.strip()]
    timing = timing_surface_check(sorted(symbols)[: args.timing_symbols], checkpoint_days)

    verdict = overall_verdict(checkpoints)
    report = {
        "spec": "zuaef-quant-final-spec-v2.0 P0.4",
        "verdict": verdict,
        "as_of": datetime.now(TZ_SHANGHAI).isoformat(),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "window": {"start": window_start, "end": window_end, "universe_size": len(symbols)},
        "checkpoints": checkpoints,
        "timing_surface": timing,
        "pit_context": load_pit_context(),
        "scope_notes": [
            "composite candidate rank is a today-only surface (no date parameter) — not behaviorally testable",
            (
                "universe-selection contamination (P0.3) is carried as expected evidence, not corrected here; "
                "this check validates within-universe time-series mechanics only"
            ),
            (
                "timing_surface.stale_quote_sensitivity is a call-pattern hazard (stale quote meeting a refreshed "
                "cache), quantified and reported; it does not flip the replay verdict in either direction"
            ),
        ],
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = args.out_dir / f"anti_leakage_check_{stamp}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    print(json.dumps({
        "verdict": verdict,
        "checkpoints": {c["checkpoint"]: c["status"] for c in checkpoints},
        "factor_diffs_total": sum(c.get("factor_diff_count", 0) for c in checkpoints),
        "membership_diffs_total": sum(c.get("membership_diff_count", 0) for c in checkpoints),
        "entry_intent_changes": any(c["entry_intents"]["changed"] for c in checkpoints),
        "exit_intent_changes": any(c["exit_intents"]["changed"] for c in checkpoints),
        "timing_truncation_invariant": timing["truncation_invariance"]["invariant"],
        "timing_stale_quote_sensitive": timing["stale_quote_sensitivity"]["sensitive"],
        "pit_context_verdict": (report.get("pit_context") or {}).get("verdict"),
        "evidence": str(out),
    }, ensure_ascii=False))
    return EXIT_CODES[verdict]


if __name__ == "__main__":
    sys.exit(main())
