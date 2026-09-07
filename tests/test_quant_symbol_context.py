"""symbol-context auto-hydration (quant research service v0.2, T004).

The reproduced 600550 incident: quote existed, history cache missed (0 bars),
the agent refused the full analysis. These tests pin the repaired contract:
symbol-context hydrates a never-cached symbol on demand, reports hydration as
separate evidence, and a hydration failure never wipes the quote.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

pytest.importorskip("pandas")

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))

import pandas as pd
import quant_core
import quant_trading_monitor as mon
from quant_core import StrategySpec

TZ_SH = ZoneInfo("Asia/Shanghai")
NOW = datetime(2026, 9, 2, 10, 0, tzinfo=TZ_SH)  # a Wednesday, in session
SPEC = StrategySpec(
    name="volume_pullback_reversal", universe="csi500_subset", max_holding_days=5,
    stop_loss_pct=0.03, take_profit_pct=0.06, position_fraction=0.10, max_positions=5,
    entry_pullback_max=-0.06, entry_volume_ratio_min=1.80,
)


def _raw_history(n_bars: int, last_date: str = "2026-02-20") -> pd.DataFrame:
    dates = pd.bdate_range(end=last_date, periods=n_bars).strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "date": dates,
            "open": [10.0] * n_bars,
            "high": [10.5] * n_bars,
            "low": [9.8] * n_bars,
            "close": [10.2] * n_bars,
            "volume": [1_000_000.0] * n_bars,
            "amount": [10_200_000.0] * n_bars,
        }
    )


def _quote(symbol: str, price: float, prev_close: float) -> dict:
    return {
        "name": symbol, "price": price, "prev_close": prev_close, "open": prev_close,
        "volume": 19_758_500.0, "date": "20260902", "time": "10:00:00",
    }


@pytest.fixture
def sym_env(tmp_path, monkeypatch):
    """Fixture plane for cmd_symbol_context: frozen clock, fixture strategy,
    fixture universe — and cwd inside tmp so the relative quant-cache writes
    stay out of the real cache."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mon, "now_sh", lambda: NOW)
    monkeypatch.setattr(
        mon, "_load_strategy", lambda: ({"monitor": {"near_band": 0.25}}, SPEC)
    )
    monkeypatch.setattr(
        mon, "resolve_universe",
        lambda *a, **k: {"symbols": ["600001"], "source": "fixture",
                         "source_path": "fixture", "as_of": "fixture"},
    )
    return SimpleNamespace(
        args=lambda symbol="600550": SimpleNamespace(symbol=symbol, scope=None),
        store=mon.Store(tmp_path / "trading"),
    )


def _run(env, symbol: str = "600550") -> dict:
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        mon.cmd_symbol_context(env.args(symbol), env.store)
    return json.loads(buffer.getvalue().strip().splitlines()[-1])


def test_cache_miss_auto_hydrates(sym_env, monkeypatch):
    monkeypatch.setattr(
        mon, "fetch_batch_quotes", lambda symbols: {s: _quote(s, 10.97, 11.10) for s in symbols}
    )
    monkeypatch.setitem(
        sys.modules, "akshare",
        SimpleNamespace(stock_zh_a_hist_tx=lambda **_kw: _raw_history(60)),
    )
    result = _run(sym_env)

    assert result["quote"]["available"] is True
    history = result["history"]
    assert history["bars_available"] == 60
    assert history["sufficient"] is True
    assert history["hydration_status"] == "hydrated"
    assert history["hydration_last_date"] == "2026-02-20"
    # the hydrated cache lands in the sandbox-visible layout
    assert Path("data/quant-cache/daily/600550_qfq.csv").is_file()


def test_hydration_failure_never_wipes_the_quote(sym_env, monkeypatch):
    monkeypatch.setattr(
        mon, "fetch_batch_quotes", lambda symbols: {s: _quote(s, 10.97, 11.10) for s in symbols}
    )

    def failing(**_kw):
        raise RuntimeError("network down")

    monkeypatch.setattr(quant_core.time, "sleep", lambda _s: None)
    monkeypatch.setitem(
        sys.modules, "akshare", SimpleNamespace(stock_zh_a_hist_tx=failing)
    )
    result = _run(sym_env)

    assert result["quote"]["available"] is True
    assert result["quote"]["price"] == 10.97
    history = result["history"]
    assert history["hydration_status"] == "failed"
    assert "network down" in history["hydration_error"]
    assert history["bars_available"] == 0
    assert history["sufficient"] is False
    assert result["strategy_distance"]["available"] is False


def test_cached_symbol_reports_hydration_cache_hit(sym_env, monkeypatch):
    monkeypatch.setattr(
        mon, "fetch_batch_quotes", lambda symbols: {s: _quote(s, 10.97, 11.10) for s in symbols}
    )
    monkeypatch.setitem(
        sys.modules, "akshare",
        SimpleNamespace(stock_zh_a_hist_tx=lambda **_kw: _raw_history(60)),
    )
    # first run hydrates, second run must not fetch again
    _run(sym_env)

    def must_not_fetch(**_kw):
        raise AssertionError("fresh cache must not trigger a fetch")

    monkeypatch.setitem(
        sys.modules, "akshare", SimpleNamespace(stock_zh_a_hist_tx=must_not_fetch)
    )
    result = _run(sym_env)
    assert result["history"]["hydration_status"] == "cache"
    assert result["history"]["bars_available"] == 60
