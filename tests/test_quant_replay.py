"""P2 replay failure-mode tests (ZUAEF-ASHARE-001): the false-alpha defenses.

Each test protects one execution-truth rule that can manufacture fake alpha
if broken (spec pack 04 §7). Runs under the quant dependency group
(`uv run --group quant pytest tests/test_quant_replay.py`); the default
suite skips when pandas is absent.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("pandas")

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))

import pandas as pd
import quant_core
from quant_core import (
    Intent,
    MarketRules,
    ReplayEngine,
    StrategySpec,
)


def make_rules(**overrides) -> MarketRules:
    base = {
        "commission_rate": 0.00025,
        "commission_min": 5.0,
        "stamp_duty_periods": ({"effective_from": "2018-01-01", "sell_rate": 0.001},
                               {"effective_from": "2023-08-28", "sell_rate": 0.0005}),
        "slippage_bps": 10,
        "lot_size": 100,
        "t_plus_1": True,
        "price_limit_periods": (
            {"prefixes": ("600", "000"), "effective_from": "2018-01-01", "limit_pct": 0.10},
            {"prefixes": ("300",), "effective_from": "2018-01-01", "limit_pct": 0.10},
            {"prefixes": ("300",), "effective_from": "2020-08-24", "limit_pct": 0.20},
        ),
        "initial_capital": 1_000_000.0,
    }
    base.update(overrides)
    return MarketRules(**base)


def make_spec(**overrides) -> StrategySpec:
    base = {
        "name": "test",
        "universe": "test",
        "max_holding_days": 5,
        "stop_loss_pct": 0.03,
        "take_profit_pct": 0.06,
        "position_fraction": 0.10,
        "max_positions": 5,
    }
    base.update(overrides)
    return StrategySpec(**base)


def prices(symbol: str, rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"date": date.fromisoformat(d), "open": o, "close": c} for d, o, c in rows]
    ).assign(symbol=symbol)


def run(prices_by_symbol, intents, rules=None, spec=None, market_truth=True):
    rules = rules or make_rules()
    spec = spec or make_spec()
    engine = ReplayEngine(rules, spec, prices_by_symbol, enforce_market_truth=market_truth)
    return engine.run(intents)


class TestTPlusOne:
    def test_no_sell_settles_on_or_before_its_buy(self):
        px = {"600519": prices("600519", [
            ("2024-01-02", 100.0, 101.0),
            ("2024-01-03", 102.0, 103.0),
            ("2024-01-04", 103.0, 104.0),
            ("2024-01-05", 104.0, 105.0),
        ])}
        result = run(px, [Intent("BUY", "600519", date(2024, 1, 2)),
                          Intent("SELL", "600519", date(2024, 1, 2)),
                          Intent("SELL", "600519", date(2024, 1, 3))])
        buy_fills = [f for f in result["fills"] if f.action == "BUY"]
        sell_fills = [f for f in result["fills"] if f.action == "SELL"]
        assert buy_fills and sell_fills
        assert all(s.date > buy_fills[0].date for s in sell_fills)

    def test_deferred_t_plus_one_sell_fills_next_day(self):
        px = {"600519": prices("600519", [
            ("2024-01-02", 100.0, 101.0),
            ("2024-01-03", 102.0, 103.0),
            ("2024-01-04", 103.0, 104.0),
            ("2024-01-05", 104.0, 105.0),
        ])}
        engine = ReplayEngine(make_rules(), make_spec(), px)
        # force a position bought 01-03 and a sell attempted same day
        engine.run([Intent("BUY", "600519", date(2024, 1, 2)),
                    Intent("SELL", "600519", date(2024, 1, 3))])
        sells = [f for f in engine.fills if f.action == "SELL"]
        assert len(sells) == 1
        assert sells[0].date == date(2024, 1, 4)  # blocked 01-03 (T+1), filled 01-04


class TestPriceLimits:
    def test_buy_blocked_at_limit_up_open(self):
        # prev close 100 -> +10% limit 110; open at 110 = blocked
        px = {"600519": prices("600519", [
            ("2024-01-02", 100.0, 100.0),
            ("2024-01-03", 110.0, 110.0),
        ])}
        result = run(px, [Intent("BUY", "600519", date(2024, 1, 2))])
        assert not any(f.action == "BUY" for f in result["fills"])
        assert any(b.reason == "limit_up_open" for b in result["blocked"])

    def test_sell_blocked_at_limit_down_open_then_fills(self):
        # buy fills 01-03 at open 100; 01-04 opens at limit-down 90 -> defer; 01-05 fills
        px = {"600519": prices("600519", [
            ("2024-01-02", 100.0, 100.0),
            ("2024-01-03", 100.0, 100.0),
            ("2024-01-04", 90.0, 90.0),
            ("2024-01-05", 95.0, 96.0),
        ])}
        result = run(px, [Intent("BUY", "600519", date(2024, 1, 2)),
                          Intent("SELL", "600519", date(2024, 1, 3))])
        sells = [f for f in result["fills"] if f.action == "SELL"]
        assert len(sells) == 1
        assert sells[0].date == date(2024, 1, 5)
        assert any(b.reason == "limit_down_open" for b in result["blocked"])

    def test_chinext_twenty_pct_limit_after_effective_date(self):
        rules = make_rules()
        # ChiNext: 10%% from 2018, 20%% from 2020-08-24 (frozen rules config)
        assert rules.price_limit_pct("300750", date(2020, 8, 21)) == 0.10
        assert rules.price_limit_pct("300750", date(2020, 8, 24)) == 0.20

    def test_market_truth_off_does_not_block_limit_up(self):
        px = {"600519": prices("600519", [
            ("2024-01-02", 100.0, 100.0),
            ("2024-01-03", 110.0, 110.0),
        ])}
        result = run(px, [Intent("BUY", "600519", date(2024, 1, 2))], market_truth=False)
        assert any(f.action == "BUY" for f in result["fills"])


class TestSuspension:
    def test_buy_on_suspended_day_blocked_without_position(self):
        px = {"600519": prices("600519", [
            ("2024-01-02", 100.0, 100.0),
            # 01-03 suspended for this name (no bar) but market open (calendar)
            ("2024-01-04", 101.0, 102.0),
        ])}
        engine = ReplayEngine(make_rules(), make_spec(), px)
        result = engine.run([Intent("BUY", "600519", date(2024, 1, 2))],
                            trading_dates=[date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)])
        assert not any(f.action == "BUY" for f in result["fills"])
        assert any(b.date == date(2024, 1, 3) and b.reason == "suspended_or_no_bar"
                   for b in result["blocked"])

    def test_sell_deferred_through_suspension(self):
        px = {"600519": prices("600519", [
            ("2024-01-02", 100.0, 100.0),
            ("2024-01-03", 100.0, 100.0),
            # 01-04 suspended
            ("2024-01-05", 99.0, 100.0),
        ])}
        engine = ReplayEngine(make_rules(), make_spec(), px)
        result = engine.run([Intent("BUY", "600519", date(2024, 1, 2)),
                             Intent("SELL", "600519", date(2024, 1, 3))],
                            trading_dates=[date(2024, 1, d) for d in (2, 3, 4, 5)])
        sells = [f for f in result["fills"] if f.action == "SELL"]
        assert len(sells) == 1 and sells[0].date == date(2024, 1, 5)
        assert any(b.date == date(2024, 1, 4) and b.reason == "suspended_or_no_bar"
                   for b in result["blocked"])

    def test_no_bar_marks_at_last_known_close_not_entry(self):
        px = {"600519": prices("600519", [
            ("2024-01-02", 10.0, 10.0),
            ("2024-01-03", 10.0, 15.0),
        ])}
        engine = ReplayEngine(make_rules(), make_spec(), px)
        result = engine.run(
            [Intent("BUY", "600519", date(2024, 1, 2))],
            trading_dates=[date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
        )
        equity = result["equity"].set_index("date")["equity"]
        assert equity.loc[date(2024, 1, 4)] == pytest.approx(equity.loc[date(2024, 1, 3)])


class TestLotsAndCosts:
    def test_shares_round_to_lot_and_cash_stays_positive(self):
        px = {"600519": prices("600519", [("2024-01-02", 100.0, 100.0),
                                          ("2024-01-03", 33.33, 33.33)])}
        result = run(px, [Intent("BUY", "600519", date(2024, 1, 2))])
        buys = [f for f in result["fills"] if f.action == "BUY"]
        assert len(buys) == 1
        assert buys[0].shares % 100 == 0 and buys[0].shares > 0
        # budget = 10% of 1M = 100k; slippage lifts 33.33 to 33.36333;
        # floor(100000 / 33.36333 / 100) = 29 lots -> 2900 shares
        assert buys[0].shares == 2900
        assert result["equity"]["cash"].min() >= 0

    def test_commission_minimum_applies(self):
        px = {"600519": prices("600519", [("2024-01-02", 100.0, 100.0),
                                          ("2024-01-03", 5.0, 5.0)])}
        # tiny position: ~500 notional; 0.025% = 0.125 -> minimum 5.0 applies
        spec = make_spec(position_fraction=0.001)
        result = run(px, [Intent("BUY", "600519", date(2024, 1, 2))], spec=spec)
        buys = [f for f in result["fills"] if f.action == "BUY"]
        assert buys[0].cost == 5.0

    def test_stamp_duty_effective_dated_on_sells(self):
        rules = make_rules()
        assert rules.stamp_duty_sell_rate(date(2023, 8, 25)) == 0.001
        assert rules.stamp_duty_sell_rate(date(2023, 8, 28)) == 0.0005


class TestPositionLimits:
    def test_max_positions_blocks_extra_buys(self):
        rows = [("2024-01-02", 100.0, 100.0), ("2024-01-03", 100.0, 100.0)]
        px = {f"60051{i}": prices(f"60051{i}", rows) for i in range(6)}
        intents = [Intent("BUY", s, date(2024, 1, 2)) for s in sorted(px)]
        result = run(px, intents)
        buys = [f for f in result["fills"] if f.action == "BUY"]
        assert len(buys) == 5
        assert any(b.reason == "max_positions" for b in result["blocked"])


class TestNoLookahead:
    def test_entry_decided_on_t_fills_strictly_after_t(self):
        px = {"600519": prices("600519", [
            ("2024-01-02", 100.0, 100.0),
            ("2024-01-03", 101.0, 102.0),
            ("2024-01-04", 103.0, 103.5),
        ])}
        result = run(px, [Intent("BUY", "600519", date(2024, 1, 3))])
        buys = [f for f in result["fills"] if f.action == "BUY"]
        assert len(buys) == 1
        assert buys[0].date == date(2024, 1, 4)
        # fill price = T+1 open plus adverse slippage, never T's close
        expected = 103.0 * (1 + 10 / 10_000)
        assert buys[0].price == pytest.approx(expected)

    def test_builder_property_against_truncated_panel(self):
        from quant_eval_qlib import build_intents

        dates = pd.date_range("2024-01-02", periods=40, freq="B")
        base = (100.0 + (pd.Series(range(40)) % 7) * 5).values
        volume = pd.Series(1_000_000.0, index=range(40))
        volume.iloc[30:] = 5_000_000.0  # volume spike late in the window
        idx = pd.MultiIndex.from_product([dates, ["SYM"]], names=["datetime", "instrument"])
        panel = pd.DataFrame(
            {
                "open": base,
                "close": base * 1.01,
                "volume": volume.values,
                "prev_close": pd.Series(base).shift(1).fillna(pd.Series(base)).values,
                "close_5d_ago": pd.Series(base).shift(5).bfill().values,
                "ma5": pd.Series(base).rolling(5, min_periods=1).mean().values,
                "volume_ma20": volume.rolling(20, min_periods=1).mean().values,
            },
            index=idx,
        )

        spec = make_spec()
        intents = build_intents(panel, spec, ("2024-01-02", "2024-02-23"))
        buys = [i for i in intents if i.action == "BUY"]
        assert buys, "fixture should produce at least one entry"
        for intent in buys:
            truncated = panel[panel.index.get_level_values(0) <= pd.Timestamp(intent.intent_date)]
            row = truncated.loc[(pd.Timestamp(intent.intent_date), "SYM")]
            signal = (
                row["close"] / row["close_5d_ago"] - 1 <= -0.06
                and row["volume"] / row["volume_ma20"] >= 1.80
                and row["close"] - row["prev_close"] >= 0
                and row["volume"] > 0
            )
            assert bool(signal), f"intent at {intent.intent_date} fails truncated-signal check"


# ---------------------------------------------------------------------------
# P0.1 volume unit canonicalization at the quant data boundary
# ---------------------------------------------------------------------------


class TestVolumeUnitNormalization:
    @staticmethod
    def _hist(volumes, closes, amounts=None):
        n = len(volumes)
        return pd.DataFrame(
            {
                "date": [f"2026-01-{i + 1:02d}" for i in range(n)],
                "open": closes,
                "high": closes,
                "low": closes,
                "close": closes,
                "volume": volumes,
                "amount": amounts if amounts is not None else [v * c for v, c in zip(volumes, closes)],
            }
        )

    def test_lot_unit_series_rescaled_to_shares(self):
        # real 000807 row: amount/(volume*close) ~ 100 -> cached volume was lots
        df = self._hist([568369.0] * 5, [26.57] * 5, [1508687500.0] * 5)
        out, info = quant_core.normalize_volume_unit(df)
        assert info == {"volume_unit": "share", "volume_source_unit": "lot", "volume_unit_factor_applied": 100.0}
        assert out["volume"].iloc[0] == pytest.approx(56836900.0)

    def test_share_unit_series_unchanged(self):
        # real 600015 row: amount/(volume*close) ~ 1 -> cached volume already shares
        df = self._hist([147909500.0] * 5, [6.23] * 5, [927360100.0] * 5)
        out, info = quant_core.normalize_volume_unit(df)
        assert info == {"volume_unit": "share", "volume_source_unit": "share", "volume_unit_factor_applied": 1.0}
        assert out["volume"].iloc[-1] == pytest.approx(147909500.0)

    def test_missing_amount_leaves_series_unknown_not_guessed(self):
        df = self._hist([100.0] * 5, [10.0] * 5).drop(columns=["amount"])
        out, info = quant_core.normalize_volume_unit(df)
        assert info["volume_unit"] == "unknown"
        assert out["volume"].equals(df["volume"])

    def test_suspended_tail_rows_do_not_break_inference(self):
        volumes = [568369.0] * 5 + [0.0, 0.0]
        closes = [26.57] * 7
        amounts = [1508687500.0] * 5 + [0.0, 0.0]
        out, info = quant_core.normalize_volume_unit(self._hist(volumes, closes, amounts))
        assert info["volume_source_unit"] == "lot"
        assert out["volume"].iloc[-1] == 0.0


class TestHistoryCacheContract:
    @staticmethod
    def _raw_history():
        return pd.DataFrame({
            "date": ["2026-01-02"], "open": [10.0], "high": [10.0],
            "low": [10.0], "close": [10.0], "volume": [1000.0],
            "amount": [10000.0],
        })

    def test_legacy_cache_is_refetched_and_current_cache_is_reused(self, tmp_path, monkeypatch):
        daily = tmp_path / "daily"
        daily.mkdir()
        old = self._raw_history().assign(symbol="600000")
        old.to_csv(daily / "600000_qfq.csv", index=False)
        (daily / "600000_qfq.meta.json").write_text(
            '{"symbol":"600000","adjust":"qfq","start_date":"20180101"}'
        )
        calls = []

        def fetch(**_kwargs):
            calls.append(1)
            return self._raw_history()

        monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_zh_a_hist_tx=fetch))
        _df, meta, source = quant_core.fetch_history("600000", "qfq", cache_dir=tmp_path)
        assert source == "live" and calls == [1]
        assert meta["cache_schema"] == quant_core.HISTORY_CACHE_SCHEMA

        def must_not_fetch(**_kwargs):
            raise AssertionError("current cache should be reused")

        monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_zh_a_hist_tx=must_not_fetch))
        _df, _meta, source = quant_core.fetch_history("600000", "qfq", cache_dir=tmp_path)
        assert source == "cache"


class TestAccountingTruth:
    def test_first_day_cost_is_in_total_return(self):
        rules = make_rules(initial_capital=1000.0)
        equity = pd.DataFrame({"date": [date(2024, 1, 2)], "equity": [995.0]})
        metrics = quant_core.compute_metrics(equity, [], rules)
        assert metrics["total_return_pct"] == pytest.approx(-0.5)

    def test_corporate_action_crossing_is_detected_and_unsupported(self):
        days = pd.date_range("2024-01-02", periods=13, freq="B")
        raw_rows = []
        qfq_rows = []
        for i, day in enumerate(days):
            raw_close = 10.0 + i * 0.1
            # Stable affine mapping, then a one-unit adjustment-regime break.
            qfq_close = raw_close - (1.0 if i < 11 else 0.0)
            raw_rows.append((str(day.date()), raw_close, raw_close))
            qfq_rows.append((str(day.date()), qfq_close, qfq_close))
        raw = prices("600000", raw_rows)
        qfq = prices("600000", qfq_rows)
        events = quant_core.detect_corporate_action_dates(raw, qfq)
        assert events == [days[11].date()]
        fills = [
            quant_core.FillRecord(days[9].date(), "600000", "BUY", 100, 10.0, 5.0),
            quant_core.FillRecord(days[12].date(), "600000", "SELL", 100, 9.2, 5.0),
        ]
        unsupported = quant_core.unsupported_corporate_action_trades(
            fills, {"600000": raw}, {"600000": qfq}
        )
        assert unsupported and unsupported[0]["detected_action_dates"] == [str(days[11].date())]


# ---------------------------------------------------------------------------
# P0.5 dual-engine reconciliation: attribution logic (pure, host-owned)
# ---------------------------------------------------------------------------


import quant_p05_reconcile as p05


def _fill(day, action, shares, price, cost=5.0, symbol="600000"):
    return quant_core.FillRecord(day, symbol, action, shares, price, cost)


def _trip(day_buy, price_buy, day_sell, price_sell, shares=100, symbol="600000"):
    trip = {
        "symbol": symbol,
        "buys": [_fill(day_buy, "BUY", shares, price_buy, symbol=symbol)],
        "sell": _fill(day_sell, "SELL", shares, price_sell, symbol=symbol),
    }
    trip["econ"] = {
        "shares": shares,
        "entry_date": str(day_buy),
        "exit_date": str(day_sell),
        "trade_return": round(price_sell / price_buy - 1, 6),
        "net_pnl": 1.0,
    }
    return trip


def _pair(replay_trip, vector_trip):
    return {"symbol": "600000", "replay": replay_trip, "vector": vector_trip, "seq": 0}


class TestP05Attribution:
    def test_identical_episode_stays_unattributed_and_trusted(self):
        d1, d2 = date(2024, 3, 4), date(2024, 3, 5)
        row = _pair(_trip(d1, 10.0, d2, 10.5), _trip(d1, 10.0, d2, 10.5))
        out = p05.attribute_pair(row, trading_dates=[d1, d2], blocked=[], action_dates={}, prior_divergence=False)
        assert out["category"] == "IDENTICAL" and out["trusted"] is True and out["diffs"] == []

    def test_same_dates_same_shares_return_gap_is_qlib_face_limitation(self):
        d1, d2 = date(2024, 3, 4), date(2024, 3, 5)
        row = _pair(_trip(d1, 100.0, d2, 103.0), _trip(d1, 80.0, d2, 83.2))
        out = p05.attribute_pair(row, trading_dates=[d1, d2], blocked=[], action_dates={}, prior_divergence=False)
        assert out["category"] == p05.CAT_C and out["trusted"] is True
        assert "additive" in out["basis"][0]

    def test_adjustment_crossing_is_isolated_from_trusted_parity(self):
        d1, d2, d3 = date(2024, 3, 4), date(2024, 3, 5), date(2024, 3, 6)
        row = _pair(_trip(d1, 100.0, d3, 103.0), _trip(d1, 80.0, d3, 83.2))
        out = p05.attribute_pair(
            row, trading_dates=[d1, d2, d3], blocked=[],
            action_dates={"600000": [d2]}, prior_divergence=False,
        )
        assert out["category"] == p05.CAT_B and out["trusted"] is False

    def test_share_difference_is_expected_lot_rounding(self):
        d1, d2 = date(2024, 3, 4), date(2024, 3, 5)
        row = _pair(_trip(d1, 10.0, d2, 10.1, shares=200), _trip(d1, 10.0, d2, 10.1, shares=300))
        out = p05.attribute_pair(row, trading_dates=[d1, d2], blocked=[], action_dates={}, prior_divergence=False)
        assert out["category"] == p05.CAT_A and "lot rounding" in out["basis"][0]

    def test_vector_only_episode_with_limit_up_block_is_expected(self):
        d1, d2 = date(2024, 3, 4), date(2024, 3, 5)
        row = _pair(None, _trip(d1, 10.0, d2, 10.5))
        blocked = [quant_core.BlockedRecord(d1, "600000", "BUY", "limit_up_open")]
        out = p05.attribute_pair(row, trading_dates=[d1, d2], blocked=blocked, action_dates={}, prior_divergence=False)
        assert out["category"] == p05.CAT_A and out["trusted"] is False
        assert "limit-up" in out["basis"][0]

    def test_unattributed_exit_deferral_fails_closed(self):
        d1, d2, d3 = date(2024, 3, 4), date(2024, 3, 5), date(2024, 3, 6)
        row = _pair(_trip(d1, 10.0, d3, 10.5), _trip(d1, 10.0, d2, 10.5))
        out = p05.attribute_pair(row, trading_dates=[d1, d2, d3], blocked=[], action_dates={}, prior_divergence=False)
        assert out["category"] == p05.CAT_F and out["trusted"] is False

    def test_pairing_and_open_position_survive(self):
        fills = [
            _fill(date(2024, 3, 4), "BUY", 100, 10.0),
            _fill(date(2024, 3, 8), "SELL", 100, 10.5),
            _fill(date(2024, 3, 11), "BUY", 100, 10.2),  # second episode, same symbol
        ]
        trips = p05.pair_round_trips(fills)
        assert len(trips) == 2
        assert trips[0]["sell"] is not None and trips[1]["sell"] is None

    def test_expected_exec_skips_to_next_trading_day(self):
        assert p05.expected_exec_date(date(2024, 3, 8), [date(2024, 3, 8), date(2024, 3, 11)]) == date(2024, 3, 11)

    def test_sell_cost_decomposition_respects_stamp_duty_effective_date(self):
        rules = make_rules()
        before = p05.decompose_fill(_fill(date(2023, 8, 25), "SELL", 1000, 10.0, cost=15.0), rules, 10.0)
        after = p05.decompose_fill(_fill(date(2023, 8, 28), "SELL", 1000, 10.0, cost=10.0), rules, 10.0)
        assert before["stamp_duty"] == 10.0 and before["commission"] == 5.0
        assert after["stamp_duty"] == 5.0 and after["commission"] == 5.0
