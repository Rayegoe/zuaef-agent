"""P1 baseline strategy evaluation for ZUAEF-ASHARE-001 (spec pack 05).

Pipeline (evaluate_strategy, host-owned and deterministic):
1. stage normalized qfq daily CSVs -> qlib bin store via the canonical
   upstream dump_bin script (public supported mechanism);
2. evaluate declarative entry/exit features with Qlib expressions
   (D.features panel) — the fast vector test;
3. build frozen trade intents with the host-owned execution rule
   (day-T decision, T+1 open execution, deterministic candidate order);
4. run two engines over the SAME frozen intents:
   - vector stage: qlib-derived qfq panel, market truth OFF;
   - independent replay: raw executable prices, market truth ON (P2 rules);
5. write artifacts: intents.csv, trades.csv, equity_{vector,replay}.csv,
   evidence.json, result.md; surface cross-engine divergence against the
   frozen consistency tolerance.

Runs in the .venv-quant side environment (qlib + akshare):

    .venv-quant/bin/python tools/quant_eval_qlib.py \
        --config benchmarks/quant/gen1/quant.toml \
        --strategy benchmarks/quant/gen1/strategy.toml \
        --out workspace/artifacts/quant/gen1 [--window research]
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "quant" / "upstream"))

import quant_core
from quant_core import (
    Intent,
    MarketRules,
    ReplayEngine,
    StrategySpec,
    compute_metrics,
    load_config,
    to_tx_symbol,
    trade_records,
)

CACHE_DIR = Path("data/quant-cache")


def stage_qlib_csvs(symbols: list[str], stage_dir: Path, *, refresh: bool) -> None:
    stage_dir.mkdir(parents=True, exist_ok=True)
    for symbol in symbols:
        out = stage_dir / f"{to_tx_symbol(symbol)}.csv"
        if out.exists() and not refresh:
            continue
        df, _, _ = quant_core.fetch_history(symbol, "qfq", cache_dir=CACHE_DIR)
        df[["date", "open", "close", "high", "low", "volume"]].to_csv(out, index=False)


def build_qlib_store(stage_dir: Path, qlib_dir: Path, symbols: list[str], *, refresh: bool) -> None:
    if qlib_dir.exists() and not refresh:
        return
    if qlib_dir.exists():
        shutil.rmtree(qlib_dir)
    import dump_bin

    dumper = dump_bin.DumpDataAll(data_path=str(stage_dir), qlib_dir=str(qlib_dir))
    dumper.dump()
    # Narrow instrument universe file with per-symbol actual date coverage.
    inst_dir = qlib_dir / "instruments"
    inst_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for symbol in symbols:
        df, _, _ = quant_core.fetch_history(symbol, "qfq", cache_dir=CACHE_DIR)
        lines.append(
            f"{to_tx_symbol(symbol).upper()}\t{df['date'].min()}\t{df['date'].max()}"
        )
    (inst_dir / "csi500_subset.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_panel(qlib_dir: Path, symbols: list[str], start: str, end: str) -> pd.DataFrame:
    import qlib
    from qlib.data import D

    qlib.init(provider_uri=str(qlib_dir), region="cn")
    instruments = sorted(to_tx_symbol(s).upper() for s in symbols)
    fields = [
        "$open",
        "$close",
        "$volume",
        "Ref($close, 1)",
        "Ref($close, 5)",
        "Mean($close, 5)",
        "Mean($volume, 20)",
    ]
    panel = D.features(instruments, fields, start_time=start, end_time=end)
    panel.columns = [
        "open", "close", "volume", "prev_close", "close_5d_ago", "ma5", "volume_ma20",
    ]
    # qlib 0.9.7 returns (instrument, datetime); normalize to (datetime, instrument)
    if panel.index.names[0] == "instrument":
        panel = panel.swaplevel().sort_index()
    return panel


def build_intents(panel: pd.DataFrame, spec: StrategySpec, window: tuple[str, str]) -> list[Intent]:
    """Deterministic intent builder: day-T decisions, T+1 open execution.

    Walks the trading calendar once; entry when the strategy's three clauses
    hold on day T (and the stock actually traded that day); exit when
    holding_days >= max, close < ma5, stop-loss or take-profit triggers on
    day T's close. Candidates are taken in ascending symbol order when
    position slots are contended.
    """
    # qlib instruments are prefixed codes (SZ300285); the replay/caches use
    # bare codes — normalize the panel's symbol namespace once, up front.
    panel = panel.copy()
    panel.index = panel.index.set_levels(
        [lvl[-6:] if isinstance(lvl, str) and len(lvl) == 8 else lvl
         for lvl in panel.index.levels[panel.index.names.index("instrument")]],
        level="instrument",
    )
    entry = (
        (panel["close"] / panel["close_5d_ago"] - 1 <= spec.entry_pullback_max)
        & (panel["volume"] / panel["volume_ma20"] >= spec.entry_volume_ratio_min)
        & (panel["close"] - panel["prev_close"] >= 0)
        & (panel["volume"] > 0)
    )
    panel = panel.copy()
    panel["entry"] = entry
    bar_index: dict[str, dict] = {}
    intents: list[Intent] = []
    positions: dict[str, dict] = {}
    pending_entries: dict[str, None] = {}
    sell_decided: set[str] = set()

    dates = sorted({d for d, _ in panel.index})
    dates = [d for d in dates if date.fromisoformat(str(d)[:10]) >= date.fromisoformat(window[0])]
    dates = [d for d in dates if date.fromisoformat(str(d)[:10]) <= date.fromisoformat(window[1])]
    for sym in panel.index.get_level_values(1).unique():
        sym_idx = panel.xs(sym, level=1).index
        bar_index[sym] = {d: i for i, d in enumerate(sorted(sym_idx))}

    def bar_number(sym: str, d) -> int:
        return bar_index[sym].get(d, -1)

    for today in dates:
        # settle yesterday's pending entries
        for sym in list(pending_entries):
            try:
                open_price = float(panel.loc[(today, sym), "open"])
            except KeyError:
                # suspended on fill day: entry idea dropped (recorded at replay)
                del pending_entries[sym]
                continue
            if open_price <= 0:
                del pending_entries[sym]
                continue
            del pending_entries[sym]
            positions[sym] = {
                "entry_price": open_price,
                "entry_bar": bar_number(sym, today),
            }
        # drop positions whose sell already decided yesterday (fills T+1)
        for sym in sell_decided:
            positions.pop(sym, None)
        sell_decided = set()
        # exits decided on today's close
        for sym, pos in sorted(positions.items()):
            try:
                row = panel.loc[(today, sym)]
            except KeyError:
                continue
            if pos["entry_bar"] < 0 or bar_number(sym, today) < 0:
                continue
            holding = bar_number(sym, today) - pos["entry_bar"]
            exit_hit = (
                holding >= spec.max_holding_days
                or row["close"] < row["ma5"]
                or row["close"] <= pos["entry_price"] * (1 - spec.stop_loss_pct)
                or row["close"] >= pos["entry_price"] * (1 + spec.take_profit_pct)
            )
            if exit_hit:
                intents.append(Intent("SELL", sym, _as_date(today)))
                sell_decided.add(sym)
        # entries decided today, ascending symbol order, free slots only
        if len(positions) + len(pending_entries) < spec.max_positions:
            todays = panel.loc[(today, slice(None))]
            todays = todays[todays["entry"] == True]
            for sym in sorted(todays.index):
                if sym in positions or sym in pending_entries or sym in sell_decided:
                    continue
                if len(positions) + len(pending_entries) >= spec.max_positions:
                    break
                intents.append(Intent("BUY", sym, _as_date(today)))
                pending_entries[sym] = None
    return intents


def _as_date(d) -> date:
    return date.fromisoformat(str(d)[:10])


def run_engine(prices: dict[str, pd.DataFrame], rules: MarketRules, spec: StrategySpec,
               intents: list[Intent], *, market_truth: bool) -> dict:
    engine = ReplayEngine(rules, spec, prices, enforce_market_truth=market_truth)
    result = engine.run(intents)
    result["metrics"] = compute_metrics(result["equity"], result["fills"], rules)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("benchmarks/quant/gen1/quant.toml"))
    parser.add_argument("--strategy", type=Path, default=Path("benchmarks/quant/gen1/strategy.toml"))
    parser.add_argument("--out", type=Path, default=Path("workspace/artifacts/quant/gen1"))
    parser.add_argument("--window", choices=["research", "promotion", "holdout"], default="research")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    strategy_cfg = load_config(args.strategy)
    rules = MarketRules.from_config(cfg)
    spec = StrategySpec.from_config(strategy_cfg)
    research = cfg["research"]
    window = (research[f"{args.window}_start"], research[f"{args.window}_end"])

    universe_meta = json.loads(
        (CACHE_DIR / "universe" / "csi500_subset.meta.json").read_text(encoding="utf-8")
    )
    symbols = universe_meta["symbols"]
    print(f"universe={len(symbols)} window={args.window} {window[0]}..{window[1]}")

    stage_dir = CACHE_DIR / "qlib_stage"
    qlib_dir = CACHE_DIR / "qlib_data"
    stage_qlib_csvs(symbols, stage_dir, refresh=args.refresh)
    build_qlib_store(stage_dir, qlib_dir, symbols, refresh=args.refresh)

    # lookback pad so Ref/Mean features are warm at window start
    pad_start = str(date.fromisoformat(window[0]).replace(year=date.fromisoformat(window[0]).year - 1))
    panel = load_panel(qlib_dir, symbols, pad_start, window[1])
    print(f"panel={panel.shape[0]} rows x {panel.shape[1]} cols, "
          f"{panel.index.get_level_values(1).nunique()} instruments")

    intents = build_intents(panel, spec, window)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    intents_df = pd.DataFrame(
        [{"decision_date": i.intent_date, "symbol": i.symbol, "action": i.action} for i in intents]
    )
    intents_df.to_csv(out / "intents.csv", index=False)
    print(f"intents={len(intents)} (BUY={sum(1 for i in intents if i.action == 'BUY')}, "
          f"SELL={sum(1 for i in intents if i.action == 'SELL')})")

    # raw executable prices for the independent replay
    prices_raw: dict[str, pd.DataFrame] = {}
    prices_qfq: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        raw, _, _ = quant_core.fetch_history(symbol, "", cache_dir=CACHE_DIR)
        qfq, _, _ = quant_core.fetch_history(symbol, "qfq", cache_dir=CACHE_DIR)
        prices_raw[symbol] = raw
        prices_qfq[symbol] = qfq

    vector = run_engine(prices_qfq, rules, spec, intents, market_truth=False)
    replay = run_engine(prices_raw, rules, spec, intents, market_truth=True)
    unsupported_actions = quant_core.unsupported_corporate_action_trades(
        replay["fills"], prices_raw, prices_qfq
    )

    trade_records(replay["fills"]).to_csv(out / "trades.csv", index=False)
    pd.DataFrame(replay["blocked"]).to_csv(out / "blocked_trades.csv", index=False)
    vector["equity"].to_csv(out / "equity_vector.csv", index=False)
    replay["equity"].to_csv(out / "equity_replay.csv", index=False)

    diff_pp = replay["metrics"]["annualized_return_pct"] - vector["metrics"]["annualized_return_pct"]
    tolerance = float(cfg["consistency"]["max_annualized_return_diff_pct"])
    blocked_summary: dict[str, int] = {}
    for b in replay["blocked"]:
        blocked_summary[b.reason] = blocked_summary.get(b.reason, 0) + 1

    evidence = {
        "spec_id": "ZUAEF-ASHARE-001",
        "generation": "gen1",
        "window": {"name": args.window, "start": window[0], "end": window[1]},
        "strategy": {
            "name": spec.name,
            "universe": spec.universe,
            "universe_size": len(symbols),
            "universe_selection": universe_meta["selection"],
            "max_holding_days": spec.max_holding_days,
            "stop_loss_pct": spec.stop_loss_pct,
            "take_profit_pct": spec.take_profit_pct,
            "position_fraction": spec.position_fraction,
            "max_positions": spec.max_positions,
        },
        "data": {
            "source": "akshare 1.18.4 stock_zh_a_hist_tx (Tencent), index_stock_cons_csindex (CSIndex)",
            "pit_limitation": universe_meta["pit_limitation"],
            "research_prices": "qfq adjusted",
            "replay_prices": "raw executable",
        },
        "intents": {"total": len(intents)},
        "vector_stage": vector["metrics"],
        "independent_replay": replay["metrics"],
        "blocked_trades": blocked_summary,
        "corporate_action_gate": {
            "status": "UNSUPPORTED" if unsupported_actions else "PASS",
            "unsupported_trades": unsupported_actions,
            "meaning": "raw replay has no corporate-action accounting; detected crossings cannot support trusted metrics",
        },
        "consistency": {
            "annualized_return_diff_pp": round(diff_pp, 4),
            "tolerance_pp": tolerance,
            "within_tolerance": abs(diff_pp) <= tolerance,
        },
    }
    (out / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Strategy Result — {spec.name} ({args.window} window)",
        "",
        f"- Window: {window[0]} .. {window[1]}",
        f"- Universe: {spec.universe} ({len(symbols)} symbols, current-membership PIT limitation)",
        f"- Intents frozen: {len(intents)}",
        "",
        "## Independent replay (authoritative, raw prices, market truth)",
        f"- total return: {replay['metrics']['total_return_pct']}%",
        f"- annualized: {replay['metrics']['annualized_return_pct']}%",
        f"- max drawdown: {replay['metrics']['max_drawdown_pct']}%",
        f"- trades: {replay['metrics']['trade_count']}, total cost: {replay['metrics']['total_cost']} CNY",
        f"- blocked: {blocked_summary or 'none'}",
        "",
        "## Vector stage (qfq panel, no limit blocks)",
        f"- annualized: {vector['metrics']['annualized_return_pct']}%",
        "",
        (
            f"## Consistency: diff {diff_pp:.2f}pp vs tolerance {tolerance}pp -> "
            f"{'WITHIN' if evidence['consistency']['within_tolerance'] else 'EXCEEDED'}"
        ),
        "",
        "## Limitations",
        "- Universe uses current CSI500 membership for all dates (survivorship/lookahead bias).",
        "- Entry signals require a traded day (volume > 0); suspension days defer sells.",
        "- Status data (ST/suspension/delisting) excluded by name match and lookback only.",
    ]
    (out / "result.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(evidence["consistency"], indent=2))
    print(f"artifacts -> {out}")
    if unsupported_actions:
        print(
            f"TRUST GATE FAILED: {len(unsupported_actions)} trade(s) cross unsupported corporate actions",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
