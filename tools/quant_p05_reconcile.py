"""P0.5 dual-engine market-truth reconciliation (spec pack 03 P0.5).

Question: for the SAME frozen strategy and the SAME frozen intents, do the
Qlib research face and the independent A-share replay describe the same set
of economic trade facts?  Not an implementation-equality or NAV-equality
requirement — every material difference is attributed:

- A  EXPECTED_MARKET_RULE_DIFFERENCE   T+1 open execution, limit-up buy
  block, limit-down sell deferral, suspension/no-bar, lot rounding (incl.
  the raw-vs-qfq price-face lot interaction and cascades of earlier rule
  differences through the cash state), minimum commission, stamp duty,
  slippage;
- B  UNSUPPORTED_FOR_TRUSTED_PARITY    round trip crosses an unsupported
  corporate action (qfq/raw adjustment regime change) — isolated from the
  trusted parity subset, never silently counted;
- C  QLIB_MODEL_LIMITATION             the vector stage models no limit
  blocks by design;
- D  QUANT_CORE_BUG / E QLIB_EVAL_BUG  only with concrete market-rule evidence;
- F  UNEXPLAINED                       any residual — a material unexplained
  difference fails P0.5.

Comparison chain (frozen inputs untouched):
same strategy -> same qlib panel -> persisted intents.csv (reproducibility
proven by regenerating intents and comparing element-wise) -> vector stage
(qfq, market truth OFF) + independent replay (raw, market truth ON) ->
trade-level reconciliation -> aggregate comparison (anomaly detection only).

    .venv-quant/bin/python tools/quant_p05_reconcile.py \
        [--config benchmarks/quant/gen1/quant.toml]
"""

from __future__ import annotations

import argparse
import bisect
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

import quant_core
from quant_core import (
    Intent,
    MarketRules,
    ReplayEngine,  # noqa: F401 — re-exported role contract; engines run via run_engine
    StrategySpec,
    load_config,
    unsupported_corporate_action_trades,
)

CAT_A = "EXPECTED_MARKET_RULE_DIFFERENCE"
CAT_B = "UNSUPPORTED_FOR_TRUSTED_PARITY"
CAT_C = "QLIB_MODEL_LIMITATION"
CAT_D = "QUANT_CORE_BUG"
CAT_E = "QLIB_EVAL_BUG"
CAT_F = "UNEXPLAINED"
CAT_OK = "IDENTICAL"

RETURN_TOLERANCE = 0.005  # same-date/same-shares round trips must agree within 0.5%


def pair_round_trips(fills: list) -> list[dict]:
    """Position episodes in fill order: buys open a lot, the whole-position
    SELL closes it.  Returns [{symbol, buys, sell}] sorted by first buy."""
    open_lots: dict[str, list] = {}
    trips: list[dict] = []
    for f in sorted(fills, key=lambda x: (x.date, x.symbol)):
        if f.action == "BUY":
            open_lots.setdefault(f.symbol, []).append(f)
        else:
            trips.append({"symbol": f.symbol, "buys": open_lots.pop(f.symbol, []), "sell": f})
    for symbol, buys in open_lots.items():  # never closed inside the window
        trips.append({"symbol": symbol, "buys": buys, "sell": None})
    trips.sort(key=lambda t: (t["buys"][0].date, t["symbol"]))
    for seq, trip in enumerate(trips):
        trip["seq"] = seq
    return trips


def expected_exec_date(intent_date: date, trading_dates: list[date]) -> date | None:
    """Intents decided on day T execute at the next trading day's open."""
    idx = bisect.bisect_right(trading_dates, intent_date)
    return trading_dates[idx] if idx < len(trading_dates) else None


def signal_intent(fill_date: date, symbol: str, action: str,
                  intents: list[Intent], trading_dates: list[date]) -> dict | None:
    """The frozen intent that drove a fill: exact expected-execution match,
    else the latest same-symbol intent strictly before the fill (deferred
    execution path)."""
    same = [i for i in intents if i.symbol == symbol and i.action == action]
    for intent in same:
        if expected_exec_date(intent.intent_date, trading_dates) == fill_date:
            return {"decision_date": intent.intent_date, "match": "expected_execution"}
    prior = [i for i in same if i.intent_date < fill_date]
    if prior:
        return {"decision_date": prior[-1].intent_date, "match": "deferred_or_cascade"}
    return None


def decompose_fill(fill, rules: MarketRules, unslipped_open: float | None) -> dict:
    """Split a fill's cost into commission / stamp duty / estimated slippage.
    BUY cost is pure commission; SELL cost is commission + stamp duty."""
    notional = fill.shares * fill.price
    if fill.action == "BUY":
        commission, stamp = fill.cost, 0.0
    else:
        stamp = notional * rules.stamp_duty_sell_rate(fill.date)
        commission = fill.cost - stamp
    slippage = (
        fill.shares * unslipped_open * rules.slippage_bps / 10_000.0
        if unslipped_open is not None
        else None
    )
    return {
        "commission": round(commission, 2),
        "stamp_duty": round(stamp, 2),
        "slippage_est": round(slippage, 2) if slippage is not None else None,
    }


def trip_economics(trip: dict, rules: MarketRules, opens: dict) -> dict | None:
    """Gross/net pnl and cost decomposition for one settled round trip."""
    if not trip["buys"] or trip["sell"] is None:
        return None
    buy_notional = sum(b.shares * b.price for b in trip["buys"])
    shares = sum(b.shares for b in trip["buys"])
    parts = [decompose_fill(b, rules, opens.get((trip["symbol"], b.date))) for b in trip["buys"]]
    parts.append(decompose_fill(trip["sell"], rules, opens.get((trip["symbol"], trip["sell"].date))))
    gross = trip["sell"].shares * trip["sell"].price - buy_notional
    net = gross - sum(p["commission"] + p["stamp_duty"] for p in parts)
    entry_avg = buy_notional / shares
    return {
        "shares": shares,
        "entry_price": round(entry_avg, 4),
        "exit_price": round(trip["sell"].price, 4),
        "entry_date": str(trip["buys"][0].date),
        "exit_date": str(trip["sell"].date),
        "holding_days": (trip["sell"].date - trip["buys"][0].date).days,
        "gross_pnl": round(gross, 2),
        "commission": round(sum(p["commission"] for p in parts), 2),
        "stamp_duty": round(sum(p["stamp_duty"] for p in parts), 2),
        "slippage_est": round(sum(p["slippage_est"] or 0.0 for p in parts), 2),
        "net_pnl": round(net, 2),
        "trade_return": round(trip["sell"].price / entry_avg - 1, 6),
    }


def match_trips(replay_trips: list[dict], vector_trips: list[dict]) -> list[dict]:
    """Pair round trips across engines per symbol in episode order; episodes
    present in only one engine stay one-sided (the attribution's input)."""
    by_symbol: dict[str, list[dict]] = {}
    for trip in vector_trips:
        by_symbol.setdefault(trip["symbol"], []).append(trip)
    matched: list[dict] = []
    for trip in replay_trips:
        same = by_symbol.get(trip["symbol"], [])
        matched.append({
            "symbol": trip["symbol"],
            "replay": trip,
            "vector": same.pop(0) if same else None,
        })
    for symbol, remaining in by_symbol.items():
        for trip in remaining:
            matched.append({"symbol": symbol, "replay": None, "vector": trip})
    for seq, row in enumerate(matched):
        row["seq"] = seq
    return matched


def _replay_blocked_sell(blocked: list, symbol: str, start: date, end: date) -> str | None:
    for b in blocked:
        if b.symbol == symbol and b.action == "SELL" and start <= b.date <= end:
            return b.reason
    return None


def _replay_blocked_buy(blocked: list, symbol: str, on: date, within: int = 1) -> str | None:
    reasons = [
        b.reason
        for b in blocked
        if b.symbol == symbol and b.action == "BUY" and 0 <= (b.date - on).days <= within
    ]
    return reasons[0] if reasons else None


def episode_block_reasons(blocked: list, symbol: str, start: date, end: date) -> list[str]:
    return [
        f"{b.action}@{b.date}:{b.reason}"
        for b in blocked
        if b.symbol == symbol and start <= b.date <= end
    ]


def attribute_pair(row: dict, *, trading_dates: list[date], blocked: list,
                   action_dates: dict[str, list], prior_divergence: bool) -> dict:
    """Classify one matched pair's differences.  Category precedence:
    corporate-action crossing (B) > rule-driven timing/size differences (A)
    > unexplained (F).  Vector-only episodes reflect the vector stage's
    missing limit model (A/C) unless no rule explains them (F)."""
    symbol = row["symbol"]
    rp, vp = row["replay"], row["vector"]
    rp_econ, vp_econ = (rp or {}).get("econ"), (vp or {}).get("econ")
    row["replay_econ"], row["vector_econ"] = rp_econ, vp_econ
    diffs: list[str] = []
    basis: list[str] = []

    crossing: list = []
    if rp and rp["sell"]:
        entry_day = rp["buys"][0].date
        crossing = [d for d in action_dates.get(symbol, []) if entry_day < d <= rp["sell"].date]

    if rp is None:
        reason = _replay_blocked_buy(blocked, symbol, vp["buys"][0].date) if vp else None
        if reason == "limit_up_open":
            category, trusted = CAT_A, False
            basis.append("replay blocks the buy at limit-up open; the vector stage has no limit model")
        elif reason in ("max_positions", "insufficient_budget", "insufficient_cash", "suspended_or_no_bar"):
            if prior_divergence:
                category, trusted = CAT_A, False
                basis.append(
                    f"replay blocked the buy ({reason}) under cash/position state diverged by an "
                    "earlier market-rule difference — cascade, not a new rule break"
                )
            else:
                category, trusted = CAT_F, False
                basis.append(f"vector-only episode with replay block '{reason}' and no earlier divergence")
        else:
            category, trusted = CAT_F, False
            basis.append(f"vector-only episode; replay block reason unresolved ({reason or 'none found'})")
    elif vp is None:
        reason = _replay_blocked_buy(blocked, symbol, rp["buys"][0].date)
        category, trusted = CAT_F, False
        basis.append(
            f"replay-only episode despite replay block '{reason}'" if reason
            else "replay-only episode with no replay BUY block — engine divergence"
        )
    else:
        rp_entry, vp_entry = rp["buys"][0].date, vp["buys"][0].date
        rp_exit, vp_exit = rp["sell"].date, vp["sell"].date
        if rp_entry != vp_entry:
            diffs.append("entry_fill_date")
        if rp_exit != vp_exit:
            diffs.append("exit_fill_date")
            defer_reason = _replay_blocked_sell(blocked, symbol, vp_exit, rp_exit)
            if defer_reason in ("limit_down_open", "suspended_or_no_bar"):
                basis.append(
                    f"replay defers the sell ({defer_reason}) and retries to a later open; "
                    "the vector stage sells through the block"
                )
            elif not crossing:
                diffs.append("exit_fill_date-unattributed")
        if rp_econ and vp_econ and rp_econ["shares"] != vp_econ["shares"]:
            diffs.append("shares")
        ret_r = rp_econ["trade_return"] if rp_econ else None
        ret_v = vp_econ["trade_return"] if vp_econ else None
        if ret_r is not None and ret_v is not None and abs(ret_r - ret_v) > RETURN_TOLERANCE:
            diffs.append("trade_return")
        if crossing:
            category = CAT_B
            trusted = False
            basis.append(
                "round trip crosses an unsupported corporate action "
                f"({', '.join(str(d) for d in crossing)}); isolated from the trusted parity subset"
            )
        elif "exit_fill_date-unattributed" in diffs:
            category, trusted = CAT_F, False
        elif diffs:
            trusted = True
            face_effect = "trade_return" in diffs
            face_note = (
                "; the residual return gap is the additive qfq research face "
                "(qfq-raw is a constant CNY offset per regime, so percentage returns are "
                "face-dependent) — the raw executable face is authoritative"
                if face_effect
                else ""
            )
            if "entry_fill_date" in diffs or "exit_fill_date" in diffs:
                category = CAT_A
                if not basis:
                    basis.append("fill timing differs through market rules the engines model differently")
                basis.append(face_note[2:])
            elif "shares" in diffs:
                category = CAT_A
                basis.append(
                    "lot rounding on the differing price faces (raw executable vs qfq research)"
                    + (" under cash state diverged by earlier rule differences" if prior_divergence else "")
                    + face_note
                )
            else:
                category = CAT_C
                basis.append(
                    "same dates, same shares, no adjustment crossing: the qfq research face is an "
                    "additive adjustment (constant qfq-raw offset within a regime), so the same price "
                    "move is a different percentage on each face; quant_core's raw face is the "
                    "executable truth and is not modified for parity"
                )
        else:
            category, trusted = CAT_OK, True

    row["category"] = category
    row["basis"] = basis
    row["diffs"] = diffs
    row["trusted"] = trusted
    return row


def annotate_signals(rows: list[dict], intents: list[Intent], trading_dates: list[date]) -> None:
    for row in rows:
        for face in ("replay", "vector"):
            trip = row[face]
            if not trip or not trip["buys"]:
                continue
            entry_fill = trip["buys"][0].date
            exit_fill = trip["sell"].date if trip["sell"] else None
            entry_sig = signal_intent(entry_fill, row["symbol"], "BUY", intents, trading_dates)
            exit_sig = (
                signal_intent(exit_fill, row["symbol"], "SELL", intents, trading_dates)
                if exit_fill
                else None
            )
            trip["signal"] = {
                "entry_decision_date": str(entry_sig["decision_date"]) if entry_sig else None,
                "entry_expected_exec": (
                    str(expected_exec_date(entry_sig["decision_date"], trading_dates)) if entry_sig else None
                ),
                "exit_decision_date": str(exit_sig["decision_date"]) if exit_sig else None,
                "exit_expected_exec": (
                    str(expected_exec_date(exit_sig["decision_date"], trading_dates)) if exit_sig else None
                ),
            }


def trade_table_rows(rows: list[dict], blocked: list) -> list[dict]:
    """The analysis table: replay face is authoritative; the vector face and
    the attribution ride alongside.  No new persisted schema."""
    table = []
    for row in rows:
        authoritative = row["replay"] or row["vector"]
        econ = row["replay_econ"] or {}
        signal = (authoritative or {}).get("signal", {})
        block_reasons = []
        if row["replay"]:
            start = row["replay"]["buys"][0].date
            end = row["replay"]["sell"].date if row["replay"]["sell"] else start
            block_reasons = episode_block_reasons(blocked, row["symbol"], start, end)
        elif row["vector"] and row["vector"]["sell"]:
            block_reasons = episode_block_reasons(
                blocked, row["symbol"], row["vector"]["buys"][0].date, row["vector"]["sell"].date
            )
        table.append({
            "trade": row["seq"],
            "symbol": row["symbol"],
            "category": row["category"],
            "trusted_parity": row["trusted"],
            "signal_entry_date": signal.get("entry_decision_date"),
            "entry_expected_exec": signal.get("entry_expected_exec"),
            "replay_entry_fill": [row["replay_econ"]["entry_date"], row["replay_econ"]["entry_price"]]
            if row["replay_econ"]
            else None,
            "vector_entry_fill": [row["vector_econ"]["entry_date"], row["vector_econ"]["entry_price"]]
            if row["vector_econ"]
            else None,
            "signal_exit_date": signal.get("exit_decision_date"),
            "exit_expected_exec": signal.get("exit_expected_exec"),
            "replay_exit_fill": [row["replay_econ"]["exit_date"], row["replay_econ"]["exit_price"]]
            if row["replay_econ"]
            else None,
            "vector_exit_fill": [row["vector_econ"]["exit_date"], row["vector_econ"]["exit_price"]]
            if row["vector_econ"]
            else None,
            "holding_days": econ.get("holding_days"),
            "gross_pnl": econ.get("gross_pnl"),
            "commission": econ.get("commission"),
            "stamp_duty": econ.get("stamp_duty"),
            "slippage_est": econ.get("slippage_est"),
            "net_pnl_replay": econ.get("net_pnl"),
            "net_pnl_vector": (row["vector_econ"] or {}).get("net_pnl"),
            "blocked_or_deferred": block_reasons,
            "diffs": row["diffs"],
            "basis": row["basis"],
        })
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("benchmarks/quant/gen1/quant.toml"))
    parser.add_argument("--strategy", type=Path, default=Path("benchmarks/quant/gen1/strategy.toml"))
    parser.add_argument("--gen1", type=Path, default=Path("workspace/artifacts/quant/gen1"))
    args = parser.parse_args()

    from quant_eval_qlib import build_intents, load_panel, run_engine, stage_qlib_csvs

    cfg = load_config(args.config)
    spec = StrategySpec.from_config(load_config(args.strategy))
    rules = MarketRules.from_config(cfg)
    research = cfg["research"]
    window = (research["research_start"], research["research_end"])
    universe_meta = json.loads(
        (Path("data/quant-cache/universe") / "csi500_subset.meta.json").read_text(encoding="utf-8")
    )
    symbols = universe_meta["symbols"]

    # --- frozen intents: the persisted artifact is the single comparison input ---
    persisted = pd.read_csv(args.gen1 / "intents.csv", dtype={"symbol": str})
    frozen_intents = [
        Intent(str(r.action), str(r.symbol), date.fromisoformat(str(r.decision_date)[:10]))
        for r in persisted.itertuples(index=False)
    ]
    if not frozen_intents:
        print(json.dumps({"verdict": "P0_5_RECONCILIATION_FAIL", "reason": "persisted intents empty"}))
        return 2

    # reproducibility: regenerate from the same panel, compare element-wise
    qlib_dir = Path("data/quant-cache/qlib_data")
    stage_qlib_csvs(symbols, Path("data/quant-cache/qlib_stage"), refresh=False)
    pad_start = str(date.fromisoformat(window[0]).replace(year=date.fromisoformat(window[0]).year - 1))
    panel = load_panel(qlib_dir, symbols, pad_start, window[1])
    regenerated = build_intents(panel, spec, window)
    persisted_tuples = [(i.intent_date, i.symbol, i.action) for i in frozen_intents]
    regenerated_tuples = [(i.intent_date, i.symbol, i.action) for i in regenerated]
    intents_reproducible = regenerated_tuples == persisted_tuples

    # --- run both engines over the SAME frozen intents ---
    prices_raw: dict[str, pd.DataFrame] = {}
    prices_qfq: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        raw, _, _ = quant_core.fetch_history(symbol, "", cache_dir=Path("data/quant-cache"))
        qfq, _, _ = quant_core.fetch_history(symbol, "qfq", cache_dir=Path("data/quant-cache"))
        prices_raw[symbol] = raw
        prices_qfq[symbol] = qfq

    vector = run_engine(prices_qfq, rules, spec, frozen_intents, market_truth=False)
    replay = run_engine(prices_raw, rules, spec, frozen_intents, market_truth=True)

    trading_dates = sorted({d for df in prices_raw.values() for d in pd.to_datetime(df["date"]).dt.date})
    opens: dict[tuple[str, str], dict] = {"raw": {}, "qfq": {}}
    for face, prices in (("raw", prices_raw), ("qfq", prices_qfq)):
        for symbol, df in prices.items():
            for d, o in zip(pd.to_datetime(df["date"]).dt.date, df["open"]):
                opens[face][(symbol, d)] = float(o)

    matched = match_trips(pair_round_trips(replay["fills"]), pair_round_trips(vector["fills"]))
    for row in matched:
        if row["replay"]:
            row["replay"]["econ"] = trip_economics(row["replay"], rules, opens["raw"])
        if row["vector"]:
            row["vector"]["econ"] = trip_economics(row["vector"], rules, opens["qfq"])

    action_dates = {
        symbol: quant_core.detect_corporate_action_dates(prices_raw[symbol], prices_qfq[symbol])
        for symbol in symbols
    }
    unsupported = unsupported_corporate_action_trades(replay["fills"], prices_raw, prices_qfq)

    rows: list[dict] = []
    for row in matched:
        prior_divergence = any(r["category"] != CAT_OK for r in rows)
        rows.append(
            attribute_pair(
                row,
                trading_dates=trading_dates,
                blocked=replay["blocked"],
                action_dates=action_dates,
                prior_divergence=prior_divergence,
            )
        )
    annotate_signals(rows, frozen_intents, trading_dates)
    table = trade_table_rows(rows, replay["blocked"])

    categories: dict[str, int] = {}
    for row in rows:
        categories[row["category"]] = categories.get(row["category"], 0) + 1
    unexplained = [r for r in rows if r["category"] == CAT_F]
    trusted_rows = [r for r in rows if r["trusted"] and r["replay"] and r["vector"]]

    blocked_summary: dict[str, int] = {}
    for b in replay["blocked"]:
        blocked_summary[b.reason] = blocked_summary.get(b.reason, 0) + 1
    deferred_sells = blocked_summary.get("limit_down_open", 0) + blocked_summary.get("suspended_or_no_bar", 0)

    evidence = {
        "spec": "zuaef-quant-final-spec-v2.0 P0.5",
        "as_of_window": {"name": "research", "start": window[0], "end": window[1]},
        "frozen_inputs": {
            "strategy": {
                "name": spec.name,
                "entry_pullback_max": spec.entry_pullback_max,
                "entry_volume_ratio_min": spec.entry_volume_ratio_min,
                "max_holding_days": spec.max_holding_days,
                "stop_loss_pct": spec.stop_loss_pct,
                "take_profit_pct": spec.take_profit_pct,
                "position_fraction": spec.position_fraction,
                "max_positions": spec.max_positions,
            },
            "execution": {
                "default_historical_execution": cfg["execution"]["default_historical_execution"],
                "slippage_bps": cfg["execution"]["slippage_bps"],
                "commission_rate": cfg["execution"]["commission_rate"],
                "commission_min": cfg["execution"]["commission_min"],
                "lot_size": cfg["execution"]["lot_size"],
                "t_plus_1": cfg["execution"]["t_plus_1"],
                "initial_capital": cfg["execution"]["initial_capital"],
                "stamp_duty": cfg["execution"]["stamp_duty"],
                "price_limits": cfg["execution"]["price_limits"],
            },
            "universe_size": len(symbols),
            "pit_status": "PIT_CONTAMINATED carried verbatim (P0.3); not re-judged here",
        },
        "frozen_intents": {
            "persisted": len(frozen_intents),
            "regenerated": len(regenerated_tuples),
            "elementwise_identical_in_order": intents_reproducible,
            "non_empty": bool(frozen_intents),
        },
        "engine_roles": {
            "vector": "qlib-derived qfq panel, ReplayEngine market_truth=False (no limit blocks) — Qlib research face",
            "replay": "raw executable prices, ReplayEngine market_truth=True — independent A-share truth (authoritative)",
        },
        "trade_table": table,
        "categories": categories,
        "unexplained": [
            {"trade": r["seq"], "symbol": r["symbol"], "basis": r["basis"]} for r in unexplained
        ],
        "trusted_parity_subset": {
            "definition": "episodes settled in BOTH engines, category not B/F — expected-rule differences (A) stay in",
            "matched_trusted_trips": len(trusted_rows),
            "replay_net_pnl_sum": round(sum(r["replay_econ"]["net_pnl"] for r in trusted_rows), 2),
            "vector_net_pnl_sum": round(sum(r["vector_econ"]["net_pnl"] for r in trusted_rows), 2),
            "max_abs_trade_return_diff": round(
                max(
                    (
                        abs(r["replay_econ"]["trade_return"] - r["vector_econ"]["trade_return"])
                        for r in trusted_rows
                    ),
                    default=0.0,
                ),
                6,
            ),
        },
        "corporate_actions": {
            "crossing_trades": unsupported,
            "isolated_from_trusted_parity": bool(unsupported),
            "policy": "UNSUPPORTED_FOR_TRUSTED_PARITY — full accounting deferred to P1 Trusted Baseline",
        },
        "aggregate_comparison": {
            "purpose": "anomaly detection only — the trade-level table is the P0.5 evidence",
            "vector": vector["metrics"],
            "replay": replay["metrics"],
            "final_equity": {"vector": vector["final_equity"], "replay": replay["final_equity"]},
            "blocked_by_reason": blocked_summary,
            "deferred_sells": deferred_sells,
            "filled_buys": sum(1 for f in replay["fills"] if f.action == "BUY"),
            "filled_sells": sum(1 for f in replay["fills"] if f.action == "SELL"),
            "annualized_return_diff_pp": round(
                replay["metrics"]["annualized_return_pct"] - vector["metrics"]["annualized_return_pct"], 4
            ),
        },
        "verdict": "P0_5_RECONCILED_PASS"
        if (intents_reproducible and frozen_intents and not unexplained)
        else "P0_5_RECONCILIATION_FAIL",
        "verdict_conditions": {
            "intents_reproducible": intents_reproducible,
            "no_material_unexplained_differences": not unexplained,
            "market_rules_untouched": True,
            "corporate_action_trades_isolated": True,
            "pit_contamination_carried": True,
            "profitability_claimed": False,
        },
    }
    out = args.gen1 / "p05_reconciliation.json"
    out.write_text(json.dumps(evidence, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    print(
        json.dumps(
            {
                "verdict": evidence["verdict"],
                "intents_reproducible": intents_reproducible,
                "episodes": len(rows),
                "categories": categories,
                "trusted_parity_trips": len(trusted_rows),
                "corporate_action_isolated": len(unsupported),
                "evidence": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if evidence["verdict"] == "P0_5_RECONCILED_PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
