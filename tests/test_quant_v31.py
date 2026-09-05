"""隔离适配器：PIT 对抗、真实生产函数、可重复性与研究治理。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import quant_trading_monitor as monitor
import quant_v31 as v31
from quant_core import load_config

NOW = "2026-09-02T10:00:00+08:00"


def record(kind, payload, *, at=NOW, symbol=None, **extra):
    return {"kind": kind, "payload": payload, "source": "offline-test-fixture",
            "event_time": at, "available_at": at, "revision_state": "original", "symbol": symbol, **extra}


def successful_bundle():
    # Fixtures prove code semantics, not real historical market evidence.
    dates = pd.bdate_range(end="2026-09-01", periods=30)
    closes = [10.] * 25 + [10.6, 10.5, 10.35, 10.1, 9.95]
    records = [record("daily", {"date": d.strftime("%Y-%m-%d"), "close": c,
                                "open": c, "high": c * 1.01, "low": c * .99, "volume": 1_000_000.},
                      at=d.strftime("%Y-%m-%dT16:00:00+08:00"), symbol="600001")
               for d, c in zip(dates, closes)]
    records += [record("candidate", {"symbols": ["600001"], "valid_for": "2026-09-02", "frozen": True},
                       at="2026-09-01T18:00:00+08:00"),
                record("semantics", {"status": "PASS", "symbols": ["600001"], "universe_as_of": "2026-09-01T18:00:00+08:00"}, at="2026-09-01T18:00:00+08:00"),
                record("quote", {"price": 9.95, "prev_close": 9.9, "volume": 2_000_000.,
                                 "date": "20260902", "time": "10:00:00"}, symbol="600001")]
    return {"calendar": ["2026-09-02"], "source": "OFFLINE_FIXTURE_NOT_REAL_EVIDENCE", "records": records}


@pytest.mark.parametrize("change,expected", [
    ({"available_at": "2026-09-02T10:01:00+08:00"}, "AVAILABLE_AFTER_DECISION"),
    ({"available_at": None}, "AVAILABILITY_UNKNOWN"),
    ({"available_at": "2026-09-02T10:00:00"}, "INVALID_TIME"),
    ({"revision_state": "unknown"}, "REVISION_UNKNOWN"),
    ({"revision_state": "as_of_revision"}, "REVISION_AVAILABILITY_UNKNOWN"),
    ({"revision_available_at": "2026-09-03T10:00:00+08:00"}, "REVISION_AFTER_DECISION"),
])
def test_availability_rejects_before_payload(change, expected):
    row = record("announcement", {"secret_future_alpha": 900}, **change)
    adapter = v31.PITAdapter([row], v31.timestamp(NOW))
    assert adapter.accepted == []
    assert adapter.rejected[0]["reason"] == expected
    assert "secret_future_alpha" not in json.dumps(adapter.rejected)


def test_intraday_eod_and_future_announcement_excluded():
    rows = [record("daily", {"date": "2026-09-02", "close": 999}, symbol="600001"),
            record("announcement", {"text": "future"}, at="2026-09-03T10:00:00+08:00")]
    adapter = v31.PITAdapter(rows, v31.timestamp(NOW))
    assert not adapter.accepted
    assert {r["reason"] for r in adapter.rejected} == {"INCOMPLETE_EOD_BAR", "AVAILABLE_AFTER_DECISION"}


@pytest.mark.parametrize("mutation", ["current", "unknown_publication", "not_frozen"])
def test_current_membership_never_projects_backward(mutation):
    bundle = successful_bundle()
    row = next(r for r in bundle["records"] if r["kind"] == "candidate")
    if mutation == "current":
        row["available_at"] = "2026-09-04T18:00:00+08:00"
    elif mutation == "unknown_publication":
        row["available_at"] = None
    else:
        row["payload"]["frozen"] = False
    with pytest.raises(ValueError, match="HISTORICAL_CANDIDATE_UNAVAILABLE"):
        v31.PITAdapter(bundle["records"], v31.timestamp(NOW)).resolve_universe()


def test_production_ready_path_and_reproducibility_isolated(tmp_path, monkeypatch):
    production_paths = [v31.ROOT / monitor.STATE_DIR / p for p in ("forward.json", "positions.json", "opportunities.json", "alerts.jsonl")]
    production_paths.append(v31.ROOT / monitor.ACTIVE_STRATEGY)
    before = {p: p.read_bytes() for p in production_paths if p.exists()}
    original = monitor.run_cycle
    calls = []
    def observe(*args, **kwargs):
        calls.append(kwargs["now"])
        return original(*args, **kwargs)
    monkeypatch.setattr(monitor, "run_cycle", observe)
    monkeypatch.setattr(monitor, "fetch_batch_quotes", lambda *a, **kw: pytest.fail("replay touched live transport"))
    cfg = load_config(v31.ROOT / monitor.ACTIVE_STRATEGY)
    first = v31.replay(successful_bundle(), cfg, "fixture-version", tmp_path / "a", "same")
    second = v31.replay(successful_bundle(), cfg, "fixture-version", tmp_path / "b", "same")
    assert first == second
    assert len(calls) == 2
    daily = first["payload"]["days"][0]
    assert daily["observation_count"] == 1
    assert daily["transitions"][0]["type"] == "NEW_READY"
    assert daily["outcomes"][0]["settlement_state"] == "PENDING"
    assert first["payload"]["live_forward_increment"] == 0
    assert all(p.read_bytes() == data for p, data in before.items())
    assert cfg == load_config(v31.ROOT / monitor.ACTIVE_STRATEGY)


def test_position_exit_uses_pit_history(tmp_path):
    bundle = successful_bundle()
    for row in bundle["records"]:
        if row["kind"] == "daily":
            row["payload"]["close"] = 10.
        if row["kind"] == "quote":
            row["payload"]["price"] = 10.
    # A later revised close would spuriously cause the MA5 exit if observed.
    bundle["records"].append(record("daily", {"date": "2026-09-01", "close": .1},
                                     at="2026-09-01T16:00:00+08:00", symbol="600001",
                                     available_at="2026-09-03T16:00:00+08:00"))
    adapter = v31.PITAdapter(bundle["records"], v31.timestamp(NOW))
    hist, _ = adapter.read_cache("daily", "600001_qfq")
    assert hist.iloc[-1]["close"] == 10.
    assert len(hist) == 30
    store = monitor.Store(tmp_path / "state")
    store.open_position("600001", 10., 100, NOW, "active")
    cfg = load_config(v31.ROOT / monitor.ACTIVE_STRATEGY)
    result = monitor.run_cycle(store, active_cfg=cfg, spec=v31.StrategySpec.from_config(cfg),
                               now=v31.timestamp(NOW), state_dir=store.dir,
                               semantic_status="PASS", data_adapter=adapter)
    assert store.positions["open"][0]["state"] == "HOLD"
    assert not any(e["type"] == "POSITION_EXIT_ALERT" for e in result["events"])


def test_ten_real_cache_days_are_cache_grounded_but_pit_blocked(tmp_path):
    # Explicit date fixture proves observed trading days; the CLI separately
    # proves the real cache calendar.  Cache dates never become availability.
    cache = tmp_path / "observed_dates.csv"
    cache.write_text("date\n2026-08-24\n2026-08-25\n2026-08-26\n2026-08-27\n2026-08-28\n2026-08-31\n2026-09-01\n2026-09-02\n2026-09-03\n2026-09-04\n")
    candidate = tmp_path / "active_symbols.json"
    v31.write_once(candidate, {"as_of": "2026-09-03T18:27:56+08:00", "count": 50})
    bundle = v31.local_bundle(cache, "2026-09-05", candidate)
    assert bundle["current_candidate_snapshot"]["pit_status"] == "NON_PIT_FOR_HISTORICAL_REPLAY"
    assert "CACHE_RETRIEVED_AT_IS_NOT_PUBLICATION_AVAILABLE_AT" in bundle["limitations"]
    report = v31.replay(bundle, load_config(v31.ROOT / monitor.ACTIVE_STRATEGY), "active", tmp_path, "ten")
    assert report["payload"]["cache_source"]["pit_status"] == "NON_PIT_FOR_HISTORICAL_REPLAY"
    days = report["payload"]["days"]
    assert len(days) == 10
    assert days[0]["day"] == "2026-08-24" and days[-1]["day"] == "2026-09-04"
    assert all(d["observation_count"] == 0 and d["status"] == "blocked" for d in days)
    assert all("HISTORICAL_QUOTE_ARCHIVE_UNAVAILABLE" in d["blocked_reasons"] for d in days)
    assert all("HISTORICAL_CANDIDATE_UNAVAILABLE" in d["blocked_reasons"] for d in days)
    assert "NO_TRIGGER" not in [v["decision"] for d in days for v in d["decisions"]]


def test_forward_reuses_shared_math_and_five_day_window():
    bars = pd.DataFrame({"date": pd.bdate_range("2026-09-03", periods=8).strftime("%Y-%m-%d"),
                         "close": [11.] * 8, "high": [12.] * 5 + [100.] * 3, "low": [9.] * 8})
    result = v31.outcome({"symbol": "600001", "day": "2026-09-02", "kind": "READY", "ref_price": 10.},
                         "replay", "fixture", "active", bars)
    assert [result[f"d{d}"] for d in (1, 3, 5, 8)] == [.1] * 4
    assert result["mfe"] == .2 and result["mae"] == -.1
    assert result["settlement_state"] == "SETTLED"


def test_shadow_rules_and_schema_never_change_production():
    values = {"csi300_trend": .02, "csi500_trend": .01, "realized_volatility": .01,
              "market_breadth": .6, "sector_breadth": .6, "turnover_change": .1,
              "trigger_degradation": 0., "abnormal_trading": 0.}
    rows = [record(k, {"value": v}) for k, v in values.items()]
    normal = v31.market_regime(rows, NOW)
    assert normal["regime"] == "NORMAL"
    rows[2]["payload"]["value"] = .05
    assert v31.market_regime(rows, NOW)["regime"] == "SELECTIVE"
    rows[-1]["payload"]["value"] = 1.
    assert v31.market_regime(rows, NOW)["regime"] == "DO_NOT_PARTICIPATE"
    blocked = v31.market_regime([], NOW)
    assert blocked["status"] == "blocked" and blocked["confidence"] is None
    assert "market_no_trade" not in normal
    assert normal["production_effect"] is False
    assert normal["regime_reason_codes"] == normal["reason_codes"]
    jsonschema = pytest.importorskip("jsonschema")
    schema = v31.load_json(v31.ROOT / "zuaef-quant-spec-v3.1-20260905/schemas/market_regime.schema.json")
    jsonschema.validate(normal, schema)


def test_targeted_events_unknown_publication_non_pit():
    data = v31.targeted_evidence([record("corporate_action", {"report_period": "2025-12-31"}, available_at=None)], NOW)
    assert data["corporate_action"]["status"] == "NON_PIT"
    assert data["corporate_action"]["records"][0]["payload"] is None
    assert data["market_breadth"]["limitation"] == "SOURCE_UNAVAILABLE"


@pytest.mark.parametrize("field,value", [("symbols", ["600002"]), ("universe_as_of", "2026-08-31T18:00:00+08:00")])
def test_volume_semantics_proof_must_match_pool(field, value):
    bundle = successful_bundle()
    next(r for r in bundle["records"] if r["kind"] == "semantics")["payload"][field] = value
    reasons, semantic = v31.PITAdapter(bundle["records"], v31.timestamp(NOW)).preflight()
    assert semantic == "UNKNOWN"
    assert "HISTORICAL_VOLUME_SEMANTICS_UNPROVEN" in reasons


def proposal():
    return {"experiment_id": "test", "hypothesis": "pre-stated", "baseline_version": "frozen",
            "change": "one variable", "mechanism": "independent shadow", "data_window": ["2026-09-01", "2026-09-02"],
            "primary_metric": "d5", "risk_metric": "mae", "rejection_condition": "no live-forward",
            "variable_changes": {"regime": ["OFF", "shadow"]}}


def test_experiment_one_variable_immutable_namespace_and_promotion(tmp_path):
    registry = v31.Experiments(tmp_path)
    bad = proposal()
    bad["variable_changes"]["threshold"] = [1, 2]
    with pytest.raises(ValueError):
        registry.propose(bad)
    directory = registry.propose(proposal())
    with pytest.raises(FileExistsError):
        registry.propose(proposal())
    source = tmp_path / "research.json"
    v31.write_once(source, {"namespace": "research", "window": ["2018", "2022"]})
    with pytest.raises(ValueError, match="EVIDENCE_NAMESPACE_MISMATCH"):
        registry.record(directory, "S1_REPLAY", {"verdict": "PASS"}, [source])
    result = registry.record(directory, "RESEARCH_EVAL", {"verdict": "PASS"}, [source])
    assert result["sources"][0]["original_window"] == ["2018", "2022"]
    with pytest.raises(FileExistsError):
        registry.record(directory, "RESEARCH_EVAL", {"verdict": "PASS"}, [source])
    decision = registry.decide(directory, "promote", "better research")
    assert decision["state"] == "BLOCKED" and not decision["production_config_changed"]


def test_skip_analysis_no_synthetic_fill_or_lifecycle_write(tmp_path):
    source = tmp_path / "forward.json"
    v31.write_once(source, {"observations": [{"kind": "SKIP", "opportunity_state": "NEAR", "d5": -.1,
                                            "mfe_5d": .02, "mae_5d": -.2}]})
    before = source.read_bytes()
    report = v31.skip_analysis(source)
    assert report["groups"]["SYSTEM_NEAR_HUMAN_SKIPPED"]["count"] == 1
    assert report["groups"]["SYSTEM_READY_HUMAN_EXECUTED"]["count"] == 0
    assert report["synthetic_fills"] == 0 and source.read_bytes() == before
    empty = tmp_path / "empty.json"
    v31.write_once(empty, {"observations": []})
    assert v31.skip_analysis(empty)["total"] == 0
    assert v31.degradation_metrics([])["groups"] == {}


def test_isolation_blocks_production_namespace_and_path(tmp_path):
    with pytest.raises(ValueError):
        v31.run_directory(tmp_path, "live_forward", "bad")
    with pytest.raises(ValueError):
        v31.run_directory(v31.ROOT / monitor.STATE_DIR, "replay", "bad")
    with pytest.raises(ValueError):
        v31.run_directory(tmp_path, "replay", "../bad")
    (tmp_path / "replay").symlink_to(v31.ROOT / monitor.STATE_DIR)
    with pytest.raises(ValueError, match="OUTPUT_ESCAPE"):
        v31.run_directory(tmp_path, "replay", "bad")
