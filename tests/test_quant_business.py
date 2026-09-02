"""Business-dashboard + candidate-discovery tests (offline, fixture-driven).

Protects the spec boundaries (Quant Business Dashboard + Candidate Discovery
v1.0): the legacy watchlist never silently becomes the candidate universe,
an empty/failed universe fails closed instead of becoming a NO_TRADE market
conclusion, negative PE never ranks as cheap, ranking/sector-cap are
deterministic, the business renderer handles zero/multiple triggers and
degraded data, and the server routes map correctly. No live network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("pandas")

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))

import quant_build_candidates as b
import quant_live_scan as scan
import quant_render_business_dashboard as biz
import quant_serve as serve
from quant_live_scan import UniverseError, resolve_universe


def make_policy(**overrides) -> dict:
    policy = {
        "universe": {"pool_target_min": 2, "pool_target_max": 50, "active_max_symbols": 50},
        "coverage": {"essential_min": 0.80, "deep_max_symbols": 120},
        "value_components": {
            "pe_percentile": 15,
            "pb_percentile": 10,
            "own_3y_percentile": 10,
            "dividend_yield": 5,
            "dividend_yield_full_pct": 4.0,
        },
        "quality_components": {
            "roe": 10,
            "cfo_to_net_profit": 10,
            "cfo_np_full": 1.0,
            "cfo_np_zero": 0.4,
            "growth": 10,
            "growth_full_pct": 10.0,
            "growth_zero_pct": -10.0,
            "balance_safety": 5,
        },
        "tradeability_components": {
            "turnover": 10,
            "turnover_full_cny": 5e8,
            "history": 5,
            "history_full_rows": 250,
        },
        "eligibility": {
            "min_turnover_cny": 5e7,
            "min_history_rows": 120,
            "exclude_name_patterns": ["ST", "退"],
            "financial_stale_days": 400,
            "min_price": 0.0,
        },
        "red_flags": {
            "cfo_np_min": 0.6,
            "leverage_margin_pp": 15.0,
            "roe_decline_frac": 0.7,
            "valuation_stale_days": 14,
        },
        "financial_sector": {"industry_gate_names": ["金融业", "银行"]},
        "ranking": {
            "sector_cap": 4,
            "top_n_board": 30,
            "min_industry_peers": 8,
            "tier_a_min": 75.0,
            "tier_b_min": 60.0,
            "tier_c_min": 50.0,
            "critical_red_flags": ["CFO_BELOW_NET_PROFIT_PERSISTENT"],
        },
    }
    policy.update(overrides)
    return policy


# ---------------------------------------------------------------------------
# universe resolution (T005 / T002): legacy stays separate, empty fails closed
# ---------------------------------------------------------------------------


class TestUniverseResolution:
    def test_candidate_handoff_wins_over_frozen_subset(self, tmp_path):
        active = tmp_path / "active_symbols.json"
        active.write_text(json.dumps({"symbols": ["600000", "600519"], "as_of": "x"}))
        subset = tmp_path / "subset.json"
        subset.write_text(json.dumps({"symbols": ["000001"]}))
        r = resolve_universe(None, active_path=active, subset_meta_path=subset)
        assert r["symbols"] == ["600000", "600519"]
        assert r["source"] == "candidate_pool_active"

    def test_frozen_subset_is_compatibility_fallback(self, tmp_path):
        subset = tmp_path / "subset.json"
        subset.write_text(json.dumps({"symbols": ["000001", "000002"]}))
        r = resolve_universe(None, active_path=tmp_path / "missing.json", subset_meta_path=subset)
        assert r["source"] == "csi500_subset" and len(r["symbols"]) == 2

    def test_empty_handoff_fails_closed(self, tmp_path):
        active = tmp_path / "active_symbols.json"
        active.write_text(json.dumps({"symbols": [], "count": 0}))
        with pytest.raises(UniverseError):
            resolve_universe(None, active_path=active, subset_meta_path=tmp_path / "nope.json")

    def test_broken_handoff_is_loud_not_silent_fallback(self, tmp_path):
        active = tmp_path / "active_symbols.json"
        active.write_text("{not json")
        subset = tmp_path / "subset.json"
        subset.write_text(json.dumps({"symbols": ["000001"]}))
        with pytest.raises(UniverseError):
            resolve_universe(None, active_path=active, subset_meta_path=subset)

    def test_nothing_resolvable_is_loud(self, tmp_path):
        with pytest.raises(UniverseError):
            resolve_universe(None, active_path=tmp_path / "a.json", subset_meta_path=tmp_path / "b.json")

    def test_explicit_universe_file_wins_and_may_be_legacy_watchlist(self, tmp_path):
        legacy = tmp_path / "legacy_watchlist.toml"
        legacy.write_text('schema = 1\nname = "legacy_watchlist"\nsymbols = ["601233", "002460", "002415", "000009"]\n')
        active = tmp_path / "active_symbols.json"
        active.write_text(json.dumps({"symbols": ["600519"]}))
        r = resolve_universe(legacy, active_path=active)
        assert r["symbols"] == ["601233", "002460", "002415", "000009"]
        assert r["source"] == "legacy_watchlist"

    def test_explicit_empty_file_is_loud(self, tmp_path):
        p = tmp_path / "u.toml"
        p.write_text('schema = 1\nname = "x"\nsymbols = []\n')
        with pytest.raises(UniverseError):
            resolve_universe(p)

    def test_committed_legacy_watchlist_keeps_original_names_separated(self):
        # T002: user names live in legacy_watchlist.toml, separated from the
        # candidate universe; universe.toml no longer claims to be the
        # default live opportunity set. The list is user-owned and grows by
        # explicit user nomination (2026-09-02: +11 自选股截图名单), so pin
        # the invariant, not the exact list: the original four names must
        # survive any future edit.
        gen1 = Path(__file__).parents[1] / "benchmarks" / "quant" / "gen1"
        legacy = scan.load_config(gen1 / "legacy_watchlist.toml")
        symbols = legacy["symbols"]
        assert legacy["name"] == "legacy_watchlist"
        assert symbols and len(symbols) == len(set(symbols))
        assert {"601233", "002460", "002415", "000009"} <= set(symbols)
        uni_text = (gen1 / "universe.toml").read_text(encoding="utf-8")
        assert "不再是默认活跃宇宙" in uni_text


# ---------------------------------------------------------------------------
# candidate scoring / ranking (T003): transparent, deterministic, fail-closed
# ---------------------------------------------------------------------------


class TestScoring:
    def test_negative_pe_is_missing_not_cheap(self):
        policy = make_policy()
        pcts = {"pe": None, "pb": 0.5, "roe": None, "debt": None}
        ctx = {
            "quote": {"pe_ttm": -5.0, "pb": 1.0, "dividend_yield_pct": 0.0, "turnover_cny": 2e8},
            "sector_model": "industrial",
            "financials": None,
            "hist_rows": 300,
        }
        frac, missing, _reasons, _names = b.score_value(ctx, pcts, {"pe": "missing", "pb": "pool", "roe": "missing"}, policy)
        assert "pe_percentile" in missing
        # negative PE is treated exactly like missing PE — it never enters the
        # percentile rank as "cheapest", so it can't buy a fake value advantage
        no_pe_ctx = {**ctx, "quote": {**ctx["quote"], "pe_ttm": None}}
        frac_no_pe, missing_no_pe, _r2, _n2 = b.score_value(no_pe_ctx, pcts, {"pe": "missing", "pb": "pool", "roe": "missing"}, policy)
        assert frac == frac_no_pe and missing == missing_no_pe
        # while a genuinely cheap positive PE does score the PE component
        cheap_ctx = {**ctx, "quote": {**ctx["quote"], "pe_ttm": 5.0}}
        frac_cheap, _m3, _r3, _n3 = b.score_value(cheap_ctx, {"pe": 0.05, "pb": 0.5, "roe": None, "debt": None}, {"pe": "pool", "pb": "pool", "roe": "missing"}, policy)
        assert frac_cheap > frac

    def test_percentile_map_ties_share_average_rank(self):
        m = b.percentile_map({"a": 1.0, "b": 2.0, "c": 1.0})
        assert m["a"] == m["c"] == 0.25 and m["b"] == 1.0

    def test_industry_relative_deterministic_with_pool_fallback(self):
        vals = {f"0{i:05d}": float(i) for i in range(10)}
        vals["900001"] = 4.0
        groups = {**{f"0{i:05d}": "钢铁" for i in range(10)}, "900001": "小行业"}
        pct, basis = b.group_percentiles(vals, groups, min_peers=8)
        assert basis["000000"] == "industry" and pct["000000"] == 0.0
        assert basis["900001"] == "pool"

    def test_sector_cap_deterministic(self):
        policy = make_policy()
        rows = [{"symbol": f"00000{i}", "composite_score": 90 - i, "industry": "银行"} for i in range(6)]
        rows += [{"symbol": f"10000{i}", "composite_score": 70 - i, "industry": "食品饮料"} for i in range(2)]
        ranked = sorted(rows, key=lambda r: (-r["composite_score"], r["symbol"]))
        pool, concentration = b.select_pool(ranked, policy)
        top_industries = [r["industry"] for r in pool[:8]]
        assert top_industries.count("银行") == 4
        assert concentration == "enforced"
        # identical input -> identical output
        pool2, _ = b.select_pool(sorted(rows, key=lambda r: (-r["composite_score"], r["symbol"])), policy)
        assert [r["symbol"] for r in pool] == [r["symbol"] for r in pool2]

    def test_unknown_industry_marks_concentration_unknown(self):
        policy = make_policy()
        rows = [{"symbol": f"00000{i}", "composite_score": 90 - i, "industry": None} for i in range(6)]
        pool, concentration = b.select_pool(sorted(rows, key=lambda r: (-r["composite_score"], r["symbol"])), policy)
        assert concentration == "unknown" and len(pool) == 6

    def test_candidate_output_sorted_stable(self):
        rows = [
            {"symbol": "600000", "composite_score": 70.0},
            {"symbol": "000001", "composite_score": 80.0},
            {"symbol": "300750", "composite_score": 70.0},
        ]
        ranked = sorted(rows, key=lambda r: (-r["composite_score"], r["symbol"]))
        assert [r["symbol"] for r in ranked] == ["000001", "300750", "600000"]

    def test_eligibility_hard_exclusions(self):
        policy = make_policy()
        base = {
            "name": "好公司",
            "quote": {"price": 10.0, "pe_ttm": 10.0, "turnover_cny": 2e8},
            "timing": (0.0, 1.0),
            "hist_rows": 300,
            "financials": {"fresh": True},
        }
        assert b.evaluate_eligibility(base, policy)[0] is True
        st = {**base, "name": "ST 某某"}  # ST / risk-warning excluded
        assert "ST_OR_RISK_WARNING_NAME" in b.evaluate_eligibility(st, policy)[1]
        neg = {**base, "quote": {**base["quote"], "pe_ttm": -2.0}}
        assert "NEGATIVE_EARNINGS" in b.evaluate_eligibility(neg, policy)[1]
        illiq = {**base, "quote": {**base["quote"], "turnover_cny": 1e6}}
        assert "LOW_LIQUIDITY" in b.evaluate_eligibility(illiq, policy)[1]
        nohist = {**base, "hist_rows": 10, "timing": None}
        assert "INSUFFICIENT_HISTORY" in b.evaluate_eligibility(nohist, policy)[1]
        stale = {**base, "financials": {"fresh": False}}
        assert "FINANCIAL_DATA_STALE" in b.evaluate_eligibility(stale, policy)[1]

    def test_coverage_below_threshold_is_degraded(self):
        policy = make_policy()
        assert b.coverage_status(81, 100, policy)[1] == "OK"
        assert b.coverage_status(79, 100, policy)[1] == "DEGRADED"
        assert b.coverage_status(0, 0, policy)[1] == "DEGRADED"

    def test_financial_sector_skips_industrial_rules(self):
        policy = make_policy()
        ctx = {
            "quote": {},
            "sector_model": "financial",
            "financials": {
                "roe_3y_avg": 11.0,
                "cfo_np_annual": [("2024-12-31", 0.1), ("2025-12-31", 0.1)],
                "debt_ratio": 92.0,
                "rev_growth": 5.0,
                "np_growth": 6.0,
                "fresh": True,
                "roe_annual": [("2023-12-31", 10.0), ("2024-12-31", 11.0), ("2025-12-31", 12.0)],
            },
            "hist_rows": 300,
        }
        _frac, missing, _r, flags, _n = b.score_quality(ctx, {"roe": 0.5, "debt": None}, {"roe": "pool"}, policy)
        assert "CFO_BELOW_NET_PROFIT_PERSISTENT" not in flags
        assert "HIGH_LEVERAGE_REL_SECTOR" not in flags
        assert any("financial sector model" in m for m in missing)

    def test_financial_sector_marked_unsupported_without_industry(self):
        assert b.sector_model_for(None, make_policy()) == "unsupported"


# ---------------------------------------------------------------------------
# business renderer (T006): zero/multiple triggers, degraded banner
# ---------------------------------------------------------------------------


def write_snapshot(path: Path, candidates: list[dict], **overrides) -> None:
    snap = {
        "as_of": "2026-09-03T08:30:00+08:00",
        "status": "OK",
        "base_count": 800,
        "eligible_count": max(len(candidates), 1),
        "candidate_count": len(candidates),
        "coverage": 0.93,
        "pool_target": {"min": 20, "max": 50, "met": len(candidates) >= 20},
        "deep_coverage_basis": "test",
        "concentration": "enforced",
        "sources": {"financial": {"source": "sina", "retrieved_at": "t"}, "valuation_history": {"source": "baidu"}, "quotes": {"source": "tencent"}},
        "source_degradations": [],
        "candidates": candidates,
        "legacy_diagnosis": [
            {"symbol": "601233", "name": "桐昆股份", "eligible": True, "qualifies_for_pool": False, "legacy_status": "LEGACY_ONLY", "red_flags": ["PROFIT_GROWTH_NEGATIVE"]},
            {"symbol": "002460", "name": "赣锋锂业", "eligible": False, "legacy_status": "LEGACY_ONLY", "exclusions": ["NEGATIVE_EARNINGS"], "red_flags": ["NEGATIVE_EARNINGS"]},
            {"symbol": "002415", "name": "海康威视", "eligible": True, "qualifies_for_pool": True, "legacy_status": "POOL_QUALIFIED", "red_flags": []},
            {"symbol": "000009", "name": "中国宝安", "eligible": False, "legacy_status": "LEGACY_ONLY", "exclusions": ["LOW_LIQUIDITY"], "red_flags": []},
        ],
    }
    snap.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, ensure_ascii=False))


def cand(symbol: str, composite: float = 70.0, industry: str = "银行") -> dict:
    return {
        "symbol": symbol,
        "name": f"股票{symbol}",
        "industry": industry,
        "sector_model": "industrial",
        "tier": "B",
        "composite_score": composite,
        "value_score": 30.0,
        "quality_score": 25.0,
        "tradeability_score": 10.0,
        "timing_score": 5.0,
        "timing_state": "WAIT",
        "metrics": {"pe_ttm": 8.0, "pb": 0.9, "dividend_yield_pct": 3.0, "roe_3y_pct": 11.0, "valuation_percentile_3y": 0.2},
        "reasons": ["low valuation vs peers"],
        "red_flags": [],
        "data_freshness": {"financial_date": "2026-06-30", "valuation_at": "2026-09-02"},
    }


def write_scan(path: Path, triggers: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "as_of": "2026-09-03T10:00:00+08:00",
                "universe": "candidate_pool_active",
                "universe_size": 30,
                "triggers": triggers,
            },
            ensure_ascii=False,
        )
    )


@pytest.fixture()
def biz_env(tmp_path):
    return {
        "snapshot": tmp_path / "snap" / "candidate_snapshot.json",
        "scan": tmp_path / "snap" / "last_scan.json",
        "briefs": tmp_path / "briefs",
        "obs": tmp_path / "OBSERVATION_LOG.md",
        "status": tmp_path / "STATUS.md",
        "active": tmp_path / "active.toml",
        "legacy": tmp_path / "legacy_watchlist.toml",
        "outcomes": tmp_path / "outcomes.jsonl",
    }


class TestBusinessRenderer:
    def test_zero_triggers_shows_no_action_candidate(self, biz_env):
        write_snapshot(biz_env["snapshot"], [cand("600000")])
        write_scan(biz_env["scan"], [])
        biz_env["status"].write_text("| Profitability Proof | **NOT YET** | e |\n")
        biz_env["legacy"].write_text('symbols = ["601233", "002460", "002415", "000009"]\n')
        data = biz.build_data(
            snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
            briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
        )
        html = biz.render_html(data)
        assert "无今日动作候选" in html
        assert "当前没有符合条件的股票满足确定性时序规则" in html
        assert data["kpi"]["strategy_evidence"] == "UNPROVEN"
        assert data["kpi"]["live_triggers"] == 0
        assert "历史 S3 证据薄弱" in html
        # legacy four are visible under 历史持仓 (display in Chinese)
        assert "601233" in html and "000009" in html
        assert "LEGACY_ONLY" in html  # canonical code in the data payload
        assert "仅存量持仓" in html  # Chinese display

    def test_multiple_triggers_render_with_candidate_join(self, biz_env):
        write_snapshot(biz_env["snapshot"], [cand("600000"), cand("600519", 80.0, "食品饮料")])
        write_scan(
            biz_env["scan"],
            [
                {"symbol": "600519", "name": "贵州茅台", "price": 1500.0, "pullback_5d": -0.06, "volume_ratio_20d": 2.1, "quote_time": "20260903 100000"},
                {"symbol": "600000", "name": "浦发银行", "price": 10.0, "pullback_5d": -0.055, "volume_ratio_20d": 1.9, "quote_time": "20260903 100000"},
            ],
        )
        biz_env["status"].write_text("| Profitability Proof | **NOT YET** | e |\n")
        biz_env["legacy"].write_text("symbols = []\n")
        data = biz.build_data(
            snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
            briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
        )
        html = biz.render_html(data)
        assert data["kpi"]["live_triggers"] == 2
        assert len(data["trigger_rows"]) == 2
        joined = next(r for r in data["trigger_rows"] if r["symbol"] == "600519")
        assert joined["composite_score"] == 80.0
        assert joined["industry"] == "食品饮料"
        assert "600519" in html
        # the JSON payload drives the client-side empty-state, so the static
        # string may appear in JS; the data itself must hold both triggers
        assert '"trigger_rows": [' in html

    def test_degraded_coverage_shows_banner_and_no_a_claim(self, biz_env):
        write_snapshot(biz_env["snapshot"], [cand("600000")], status="DEGRADED", coverage=0.55,
                       source_degradations=[{"source": "financial:600000", "error": "sina transport"}])
        write_scan(biz_env["scan"], [])
        biz_env["status"].write_text("| Profitability Proof | **NOT YET** | e |\n")
        biz_env["legacy"].write_text("symbols = []\n")
        data = biz.build_data(
            snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
            briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
        )
        html = biz.render_html(data)
        assert "DATA DEGRADED" in html
        assert data["data_quality"]["degraded"] is True

    def test_missing_snapshot_is_degraded_not_crash(self, biz_env):
        biz_env["status"].write_text("| Profitability Proof | **NOT YET** | e |\n")
        biz_env["legacy"].write_text("symbols = []\n")
        data = biz.build_data(
            snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
            briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
        )
        html = biz.render_html(data)
        assert data["data_quality"]["status"] == "MISSING"
        assert "DATA DEGRADED" in html
        assert "quant_build_candidates.py" in html

    def test_first_viewport_free_of_engineering_jargon(self, biz_env):
        write_snapshot(biz_env["snapshot"], [cand("600000")])
        write_scan(biz_env["scan"], [])
        biz_env["status"].write_text("| Profitability Proof | **NOT YET** | e |\n")
        biz_env["legacy"].write_text("symbols = []\n")
        data = biz.build_data(
            snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
            briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
        )
        html = biz.render_html(data)
        # engineering proof-chain stage identifiers must not lead the page
        for jargon in (">U0<", "P5.5", "ENGINEERING FREEZE", "Harness"):
            assert jargon not in html
        for needed in ("今日决策", "实时触发", "活跃候选", "前向已结算交易",
                       "策略证据", "NOT YET"):
            assert needed in html

    def test_today_decision_not_run_when_stale(self, biz_env):
        write_snapshot(biz_env["snapshot"], [])
        write_scan(biz_env["scan"], [])
        biz_env["status"].write_text("| Profitability Proof | **NOT YET** | e |\n")
        biz_env["legacy"].write_text("symbols = []\n")
        briefs = biz_env["briefs"]
        briefs.mkdir(parents=True)
        (briefs / "brief-live-1.json").write_text(json.dumps({"decision_id": "brief-live-1", "action": "NO_TRADE", "recorded_at": "2020-01-01T03:00:00+00:00", "symbol": "NONE"}))
        data = biz.build_data(
            snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
            briefs_dir=briefs, obs_path=biz_env["obs"], status_path=biz_env["status"],
            active_path=biz_env["active"], legacy_path=biz_env["legacy"], outcomes_path=biz_env["outcomes"],
        )
        assert data["kpi"]["today_decision"] == "NOT_RUN_TODAY"


# ---------------------------------------------------------------------------
# server routes (T007)
# ---------------------------------------------------------------------------


class TestServerRoutes:
    def test_page_routes(self, tmp_path):
        serve.PAGES["business"] = tmp_path / "business.html"
        serve.PAGES["engineering"] = tmp_path / "dashboard.html"
        assert serve.page_for_path("/") == serve.PAGES["business"]
        assert serve.page_for_path("/business") == serve.PAGES["business"]
        assert serve.page_for_path("/index.html") == serve.PAGES["business"]
        assert serve.page_for_path("/engineering") == serve.PAGES["engineering"]
        assert serve.page_for_path("/api/scan") is None
        assert serve.page_for_path("/nope") is None

    def test_api_routes(self):
        assert serve.api_command_for_path("/api/scan") == serve.SCAN_CMD
        watch = serve.api_command_for_path("/api/watchlist")
        assert watch is not None and watch[-1] == "benchmarks/quant/gen1/legacy_watchlist.toml"
        assert watch[-2] == "--universe-file"
        assert serve.api_command_for_path("/") is None
