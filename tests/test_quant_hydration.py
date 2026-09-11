"""ensure_history hydration seam (quant research service v0.2, T003).

The reproduced 600550 failure: cache miss → 0 bars → the agent refused to
research. These tests pin the seam contract: miss hydrates, fresh cache is
reused, stale cache refreshes bounded, suspended symbols do not re-fetch all
day, failure is evidence (never an exception), and a held per-symbol lock
fails gracefully instead of blocking the whole cache.
"""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pandas as pd
import pytest
from zuaef_quant import quant_core


def _raw_history(n_bars: int, last_date: str = "2026-02-20") -> pd.DataFrame:
    """n_bars daily sessions ending at ``last_date`` (skipping weekends is
    irrelevant: the cache contract only checks date ordering/uniqueness)."""
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


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(quant_core.time, "sleep", lambda _s: None)


def test_cache_miss_hydrates_and_reports_evidence(tmp_path, monkeypatch, no_sleep):
    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(stock_zh_a_hist_tx=lambda **_kw: _raw_history(60)),
    )
    out = quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)
    assert out["status"] == "hydrated"
    assert out["source"] == "live"
    assert out["bars_available"] == 60
    assert out["sufficient"] is True
    assert out["history_last_date"] == "2026-02-20"
    assert (tmp_path / "daily" / "600550_qfq.csv").is_file()
    # A hydrated cache stays under the read-only sandbox mount layout.
    assert not (tmp_path / "daily" / "locks").exists()


def test_fresh_valid_cache_is_reused_without_fetch(tmp_path, monkeypatch, no_sleep):
    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(stock_zh_a_hist_tx=lambda **_kw: _raw_history(60)),
    )
    quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)

    def must_not_fetch(**_kw):
        raise AssertionError("fresh cache must not trigger a fetch")

    monkeypatch.setitem(
        sys.modules, "akshare", SimpleNamespace(stock_zh_a_hist_tx=must_not_fetch)
    )
    out = quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)
    assert out["status"] == "cache"
    assert out["bars_available"] == 60


def test_stale_cache_refreshes_once(tmp_path, monkeypatch, no_sleep):
    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(stock_zh_a_hist_tx=lambda **_kw: _raw_history(60)),
    )
    quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)
    meta_path = tmp_path / "daily" / "600550_qfq.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["retrieved_at"] = "2026-08-01T09:00:00+08:00"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    calls = []

    def fetch(**_kw):
        calls.append(1)
        return _raw_history(61)

    monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_zh_a_hist_tx=fetch))
    out = quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)
    assert out["status"] == "hydrated"
    assert out["bars_available"] == 61
    assert calls == [1]

    # Same-day re-ask: the refresh already happened today — no re-fetch.
    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(
            stock_zh_a_hist_tx=lambda **_kw: (_ for _ in ()).throw(AssertionError("no second fetch"))
        ),
    )
    out = quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)
    assert out["status"] == "cache"


def test_hydration_failure_is_evidence_not_exception(tmp_path, monkeypatch, no_sleep):
    def failing(**_kw):
        raise RuntimeError("network down")

    monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_zh_a_hist_tx=failing))
    out = quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)
    assert out["status"] == "failed"
    assert "network down" in out["error"]
    assert out["bars_available"] == 0
    assert out["sufficient"] is False
    assert not (tmp_path / "daily" / "600550_qfq.csv").exists()


def test_hydrated_but_insufficient_bars_reports_sufficient_false(tmp_path, monkeypatch, no_sleep):
    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(stock_zh_a_hist_tx=lambda **_kw: _raw_history(10)),
    )
    out = quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)
    assert out["status"] == "hydrated"
    assert out["bars_available"] == 10
    assert out["sufficient"] is False


def test_held_symbol_lock_fails_gracefully(tmp_path, monkeypatch, no_sleep):
    import fcntl

    (tmp_path / "locks").mkdir()
    lock = open(tmp_path / "locks" / "600550_qfq.lock", "w")  # noqa: SIM115
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        def must_not_fetch(**_kw):
            raise AssertionError("lock holder must prevent a fetch attempt")

        monkeypatch.setitem(
            sys.modules, "akshare", SimpleNamespace(stock_zh_a_hist_tx=must_not_fetch)
        )
        out = quant_core.ensure_history("600550", "qfq", cache_dir=tmp_path)
        assert out["status"] == "failed"
        assert "lock" in out["error"]
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
