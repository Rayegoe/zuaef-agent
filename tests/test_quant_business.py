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
import quant_core as core
import quant_live_scan as scan
import quant_render_business_dashboard as biz
import quant_serve as serve
import quant_validate_semantics as semantics
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
        "trading": tmp_path / "trading",
        "diagnostic": tmp_path / "diagnostic",
        "daily": tmp_path / "daily",
        "active_symbols": tmp_path / "active_symbols.json",
        "semantic": tmp_path / "semantic",
    }


class TestBusinessRenderer:
    def test_embedded_artifact_cannot_close_script_tag(self):
        html = biz.render_html({"payload": "</script><script>alert(1)</script>"})
        assert "</script><script>alert(1)" not in html
        assert "\\u003c/script\\u003e" in html

    def test_v31_governance_is_shadow_only_and_namespace_honest(self):
        html = biz.render_html({})
        assert 'id="v31-governance-card"' in html
        assert "V3.1 · SHADOW ONLY" in html
        assert "research / replay / shadow 严格分离" in html
        assert "live-forward 增量" in html
        assert "盘中等价" in html
        assert "synthetic fills" in html
        assert "production config 不变" in html
        assert "本卡不显示也不计入 live-forward 收益" in html

    def test_v31_replay_reasons_are_projected_not_invented(self, tmp_path):
        replay_dir = tmp_path / "replay" / "test-run"
        replay_dir.mkdir(parents=True)
        report = {
            "namespace": "replay", "as_of": "2026-09-05T19:10:00+08:00",
            "payload": {"status": "blocked", "live_forward_increment": 0,
                        "intraday_equivalence": False, "days": [
                            {"status": "blocked", "observation_count": 0,
                             "blocked_reasons": ["HISTORICAL_QUOTE_ARCHIVE_UNAVAILABLE"]},
                            {"status": "blocked", "observation_count": 0,
                             "blocked_reasons": ["HISTORICAL_CANDIDATE_UNAVAILABLE"]}]},
        }
        (replay_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")
        result = biz.load_latest_v31_replay(tmp_path)
        assert result["status"] == "blocked"
        assert result["day_count"] == 2 and result["blocked_day_count"] == 2
        assert result["live_forward_increment"] == 0
        assert set(result["reasons"]) == {
            "HISTORICAL_QUOTE_ARCHIVE_UNAVAILABLE", "HISTORICAL_CANDIDATE_UNAVAILABLE"}

    def test_indicator_notes_default_to_hidden_full_width_board(self):
        html = biz.render_html({})
        assert 'id="glossary-open"' in html
        assert 'aria-expanded="false" aria-controls="glossary-drawer"' in html
        assert 'id="glossary-backdrop" hidden' in html
        assert 'id="glossary-drawer" hidden' in html
        assert 'class="card note-side"' not in html
        assert 'layout-board{display:block' in html
        assert 'grid-template-columns:minmax(0,1fr) 330px' not in html
        assert 'width:min(420px,100vw)' in html

    def test_indicator_notes_drawer_hooks_manage_open_close_and_focus(self):
        html = biz.render_html({})
        for hook in (
            "function openGlossary(){ setGlossaryOpen(true); }",
            "function closeGlossary(){ setGlossaryOpen(false); }",
            "drawer.classList.add('is-open')",
            "backdrop.classList.add('is-open')",
            "e.target.id === 'glossary-close' || e.target.id === 'glossary-backdrop'",
            "if(!$('metric-modal').hidden){ closeMetric(); return; }",
            "if(!$('glossary-drawer').hidden){ closeGlossary(); return; }",
            "$('glossary-close').focus()",
            "trigger.focus()",
        ):
            assert hook in html

    def test_indicator_notes_keep_single_glossary_metric_modal_path(self):
        html = biz.render_html({})
        assert html.count('id="glossary-list"') == 1
        assert html.count("const GLOSSARY = ") == 1
        assert '<button type="button" class="g-item" data-m="${esc(k)}"' in html
        assert "if(!g) return;" in html
        for label in ("定义", "口径 / 计算", "怎么用", "局限", "数据来源"):
            assert label in html

    def test_zero_triggers_shows_no_action_candidate(self, biz_env):
        write_snapshot(biz_env["snapshot"], [cand("600000")])
        write_scan(biz_env["scan"], [])
        biz_env["status"].write_text("| Profitability Proof | **NOT YET** | e |\n")
        biz_env["legacy"].write_text('symbols = ["601233", "002460", "002415", "000009"]\n')
        data = biz.build_data(
            snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
            briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
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
            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
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
            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
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
            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
        )
        html = biz.render_html(data)
        assert data["data_quality"]["status"] == "MISSING"
        # the frontend shows the banner for any non-PASS data-quality status;
        # the payload carries the actionable banner text
        assert "候选快照缺失" in html
        assert "D.data_quality.status !== 'PASS'" in html
        assert "quant_build_candidates.py" in html

    def test_first_viewport_free_of_engineering_jargon(self, biz_env):
        write_snapshot(biz_env["snapshot"], [cand("600000")])
        write_scan(biz_env["scan"], [])
        biz_env["status"].write_text("| Profitability Proof | **NOT YET** | e |\n")
        biz_env["legacy"].write_text("symbols = []\n")
        data = biz.build_data(
            snapshot_path=biz_env["snapshot"], scan_path=biz_env["scan"],
            briefs_dir=biz_env["briefs"], obs_path=biz_env["obs"], status_path=biz_env["status"],
            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
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
            active_path=biz_env["active"], legacy_path=biz_env["legacy"],
        )
        assert data["kpi"]["today_decision"] == "NOT_RUN_TODAY"


# ---------------------------------------------------------------------------
# M1 real-run evidence trend: workspace/artifacts/quant/trading/ is the only
# current trading truth; missing data stays missing, MARKET_CLOSED and
# SYSTEM_UNAVAILABLE keep their real meanings
# ---------------------------------------------------------------------------


CLOSED_POINT = {"ts": "2026-09-04T19:10:35+08:00", "status": "MARKET_CLOSED", "events": 0, "symbols": 0, "ms": 0}


def write_trading(env, soak, forward='{"observations": []}', alerts=None):
    env["trading"].mkdir(parents=True, exist_ok=True)
    (env["trading"] / "soak.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in soak), encoding="utf-8"
    )
    (env["trading"] / "forward.json").write_text(forward, encoding="utf-8")
    if alerts is not None:
        (env["trading"] / "alerts.jsonl").write_text(
            "".join(json.dumps(a, ensure_ascii=False) + "\n" for a in alerts), encoding="utf-8"
        )


def build_with_rt(env):
    return biz.build_data(
        snapshot_path=env["snapshot"], scan_path=env["scan"],
        briefs_dir=env["briefs"], obs_path=env["obs"], status_path=env["status"],
        active_path=env["active"], legacy_path=env["legacy"],
        trading_dir=env["trading"], diagnostic_dir=env["diagnostic"],
        daily_dir=env["daily"], active_symbols_path=env["active_symbols"],
        semantic_dir=env["semantic"],
    )


class TestRealTrend:
    def test_single_closed_point_is_one_real_point_not_a_curve(self, biz_env):
        write_trading(biz_env, [CLOSED_POINT])
        data = build_with_rt(biz_env)
        rt = data["real_trend"]
        assert rt["record_count"] == 1 and len(rt["points"]) == 1
        p = rt["points"][0]
        assert p["status"] == "MARKET_CLOSED"  # verbatim artifact status
        assert p["symbols_scanned"] == 0  # real recorded zero, not missing
        assert p["source"] == "trading/soak.jsonl"
        html = biz.render_html(data)
        assert "真实运行数据趋势" in html
        assert "已收盘（无扫描）" in html
        assert "不是扫描失败" in html

    def test_duplicate_real_record_counts_once(self, biz_env):
        write_trading(biz_env, [CLOSED_POINT, CLOSED_POINT])
        rt = build_with_rt(biz_env)["real_trend"]
        assert rt["record_count"] == 1

    def test_missing_field_stays_missing_never_zero(self, biz_env):
        row = {"ts": "2026-09-04T19:10:35+08:00", "status": "MARKET_CLOSED", "events": 0, "ms": 0}
        write_trading(biz_env, [row])
        p = build_with_rt(biz_env)["real_trend"]["points"][0]
        assert p["symbols_scanned"] is None  # not coerced to 0

    def test_events_refine_from_alerts_stream(self, biz_env):
        alert = {"ts": CLOSED_POINT["ts"], "type": "NEW_READY", "symbol": "600000", "day": "2026-09-04"}
        write_trading(biz_env, [CLOSED_POINT], alerts=[alert])
        p = build_with_rt(biz_env)["real_trend"]["points"][0]
        assert p["events"] == 1

    def test_zero_observations_show_no_forward_evidence_never_zero_winrate(self, biz_env):
        write_trading(biz_env, [CLOSED_POINT])
        data = build_with_rt(biz_env)
        assert data["real_trend"]["forward"]["count"] == 0
        assert data["kpi"]["forward_settled_trades"] == 0
        html = biz.render_html(data)
        assert "尚无正式 forward observation" in html
        assert "尚无正式 forward evidence" in html

    def test_m1_verdict_partial_with_single_scan_but_no_continuous_monitor(self, biz_env):
        write_trading(biz_env, [CLOSED_POINT])
        biz_env["semantic"].mkdir(parents=True)
        (biz_env["semantic"] / "semantic_proof_20260904T110935Z.json").write_text(json.dumps({
            "status": "PASS", "reason": "50 consistent", "sample_size": 50,
            "as_of": "2026-09-04T19:09:35+08:00",
            "same_date_cross_check": {"status": "PASS"},
        }))
        data = build_with_rt(biz_env)
        m1 = data["real_trend"]["m1_evidence"]
        assert m1["market_data_valid"]["ok"] is True
        assert m1["single_scan_valid"]["ok"] is True
        assert m1["continuous_monitoring"]["ok"] is False
        assert m1["formal_forward_count"] == 0
        assert m1["verdict"] == "PARTIAL"
        html = biz.render_html(data)
        assert "M1 production evidence" in html and "PARTIAL" in html
        assert "连续实时监控" in html and "未证明" in html

    def test_system_unavailable_is_never_no_trade_and_scan_is_distinct(self, biz_env):
        soak = [
            {"ts": "2026-09-04T10:00:00+08:00", "status": "SYSTEM_UNAVAILABLE", "events": 1, "symbols": 50, "ms": 10},
            {"ts": "2026-09-04T10:01:00+08:00", "status": "NO_TRADE", "events": 0, "symbols": 50, "ms": 10},
            CLOSED_POINT,
        ]
        write_trading(biz_env, soak)
        html = biz.render_html(build_with_rt(biz_env))
        assert "系统不可用（≠ NO_TRADE）" in html
        assert "有效扫描 · 无机会" in html
        assert "已收盘（无扫描）" in html
        # an in-session scanned point exists -> continuous monitoring has evidence
        m1 = build_with_rt(biz_env)["real_trend"]["m1_evidence"]
        assert m1["continuous_monitoring"]["ok"] is True

    def test_diagnostic_d1_from_real_cache_and_pending_stays_pending(self, biz_env):
        biz_env["diagnostic"].mkdir(parents=True)
        alerts = [
            {"ts": "2026-09-03T14:00:00+08:00", "type": "NEW_NEAR", "symbol": "600015", "day": "2026-09-03",
             "price": 6.27, "conditions": {"pullback_5d": -0.0529, "volume_ratio_20d": 1.462}},
            {"ts": "2026-09-03T14:00:00+08:00", "type": "NEW_NEAR", "symbol": "601799", "day": "2026-09-03",
             "price": 74.88, "conditions": {"pullback_5d": -0.0853, "volume_ratio_20d": 2.204}},
        ]
        (biz_env["diagnostic"] / "alerts.jsonl").write_text(
            "".join(json.dumps(a) + "\n" for a in alerts), encoding="utf-8"
        )
        header = "date,symbol,open,high,low,close,volume,amount,turnover\n"
        biz_env["daily"].mkdir(parents=True)
        (biz_env["daily"] / "600015_qfq.csv").write_text(
            header + "2026-09-03,600015,6.22,6.33,6.22,6.27,1,1,0\n"
            + "2026-09-04,600015,6.26,6.35,6.25,6.32,1,1,0\n", encoding="utf-8"
        )
        (biz_env["daily"] / "601799_qfq.csv").write_text(
            header + "2026-09-03,601799,79.0,79.0,74.18,74.88,1,1,0\n", encoding="utf-8"
        )
        data = build_with_rt(biz_env)
        diag = data["real_trend"]["diagnostic_rows"]
        by_sym = {r["symbol"]: r for r in diag}
        assert by_sym["600015"]["d1"] == 0.007974 and by_sym["600015"]["d1_day"] == "2026-09-04"
        assert "d1" not in by_sym["601799"]  # no future bar -> pending, not 0
        # diagnostic records never become formal forward observations
        assert data["real_trend"]["forward"]["count"] == 0
        html = biz.render_html(data)
        assert "diagnostic forward evidence" in html
        assert "不计入策略收益" in html

    def test_old_outcomes_file_no_longer_drives_current_truth(self, biz_env, tmp_path):
        write_trading(biz_env, [CLOSED_POINT])
        stale = tmp_path / "outcomes.jsonl"
        stale.write_text('{"action": "SELL"}\n{"action": "SELL"}\n', encoding="utf-8")
        data = build_with_rt(biz_env)
        html = biz.render_html(data)
        assert data["kpi"]["forward_settled_trades"] == 0  # truth = forward.json, not outcomes
        assert "outcomes" not in html


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


# ---------------------------------------------------------------------------
# P0.1 volume semantics consumption: only proven FAIL suppresses triggers
# ---------------------------------------------------------------------------


class TestVolumeSemantics:
    def test_missing_evidence_is_unknown_never_pass(self, tmp_path):
        s = scan.load_volume_semantics(evidence_dir=tmp_path)
        assert s["status"] == "UNKNOWN" and s["evidence"] is None

    def test_fail_proof_is_consumed_verbatim(self, tmp_path):
        p = tmp_path / "semantic_proof_20260903T031356Z.json"
        p.write_text(json.dumps({"status": "FAIL", "reason": "BROKEN_VOLUME_UNIT"}))
        s = scan.load_volume_semantics(evidence_dir=tmp_path)
        assert s["status"] == "FAIL" and s["reason"] == "BROKEN_VOLUME_UNIT"
        assert s["evidence"] == str(p)

    def test_latest_proof_wins(self, tmp_path):
        (tmp_path / "semantic_proof_20260901T000000Z.json").write_text(json.dumps({"status": "PASS"}))
        (tmp_path / "semantic_proof_20260903T000000Z.json").write_text(json.dumps({"status": "FAIL"}))
        assert scan.load_volume_semantics(evidence_dir=tmp_path)["status"] == "FAIL"

    def test_unreadable_proof_is_unknown(self, tmp_path):
        (tmp_path / "semantic_proof_20260903T000000Z.json").write_text("{not json")
        assert scan.load_volume_semantics(evidence_dir=tmp_path)["status"] == "UNKNOWN"

    @pytest.mark.parametrize("status", ["FAIL", "WARN", "UNKNOWN", "INSUFFICIENT_EVIDENCE", "STALE"])
    def test_every_non_pass_state_suppresses_live_trigger(self, status):
        assert scan.volume_gate_suppresses(status)
        assert not scan.volume_gate_suppresses("PASS")

    def test_ingest_semantics_wrong_worlds_are_rejected(self):
        assert semantics.ingest_semantics_status({"share"}, {"share": 50}, 50, 50)[0] == "PASS"
        assert semantics.ingest_semantics_status({"lot"}, {"lot": 50}, 50, 50)[0] == "FAIL"
        assert semantics.ingest_semantics_status(
            {"share", "lot"}, {"share": 25, "lot": 25}, 50, 50
        )[0] == "FAIL"
        status, reason = semantics.ingest_semantics_status({"share"}, {"share": 50}, 50, 49)
        assert status == "INSUFFICIENT_EVIDENCE" and "coverage incomplete" in reason

    def test_old_pool_pass_becomes_stale_and_suppressed(self, tmp_path):
        proof = {
            "status": "PASS", "reason": "ok", "universe_as_of": "old",
            "validated_symbols": ["600000"],
        }
        (tmp_path / "semantic_proof_20260903T000000Z.json").write_text(json.dumps(proof))
        result = scan.load_volume_semantics(
            evidence_dir=tmp_path, expected_symbols=["600001"], universe_as_of="new"
        )
        assert result["status"] == "STALE" and scan.volume_gate_suppresses(result["status"])


# ---------------------------------------------------------------------------
# P0.1-R4: persistent ingest semantics vs today's quote health
# ---------------------------------------------------------------------------


def _contract_cache(symbol: str, last_date: str, periods: int = 30):
    """Contract-valid qfq cache whose volume semantics is provably share:
    amount/(volume*close) == 1 on every row, meta satisfies the schema-2
    ingestion contract."""
    days = pd.bdate_range(end=last_date, periods=periods)
    df = pd.DataFrame(
        {
            "symbol": symbol,
            "date": days.strftime("%Y-%m-%d"),
            "open": 10.0,
            "high": 10.5,
            "low": 9.5,
            "close": 10.0,
            "volume": 1_000_000.0,
            "amount": 10_000_000.0,
        }
    )
    meta = {
        "cache_schema": core.HISTORY_CACHE_SCHEMA,
        "normalization": core.HISTORY_NORMALIZATION,
        "volume_unit": "share",
        "symbol": symbol,
        "adjust": "qfq",
        "start_date": "20180101",
        "rows": len(df),
        "date_range": [str(days.min().date()), str(days.max().date())],
    }
    return df, meta


def _quote(date: str, volume: float, price: float = 10.0) -> dict:
    return {"name": "X", "price": price, "prev_close": price, "volume": volume, "date": date, "time": "103000"}


class TestIngestSemanticsVsQuoteHealth:
    """The three R4 counterexamples: intraday PENDING must not suppress,
    an anomalous quote must FAIL, an unverified cache must stay INSUFFICIENT."""

    def test_counterexample_normal_intraday_pending_keeps_semantic_pass(self):
        df, meta = _contract_cache("600001", "2026-09-02")
        row = semantics.validate_symbol("600001", _quote("20260903", 800_000.0), df, meta)
        assert row["cache_contract_current"] is True
        assert row["cached_volume_unit"] == "share"
        assert row["quote_health"]["status"] == "pending_eod"
        agg = semantics.aggregate_rows([row], 1)
        assert agg["ingest"][0] == "PASS"
        assert agg["health"][0] == "PENDING"
        assert agg["status"] == "PASS"
        assert not scan.volume_gate_suppresses(agg["status"])

    def test_counterexample_anomalous_quote_fails_and_suppresses(self):
        df, meta = _contract_cache("600002", "2026-09-02")
        # quote claims the cached EOD date but 3x its cached volume
        row = semantics.validate_symbol("600002", _quote("20260902", 3_000_000.0), df, meta)
        assert row["quote_health"]["status"] == "inconsistent"
        agg = semantics.aggregate_rows([row], 1)
        assert agg["ingest"][0] == "PASS"  # cache truth is fine...
        assert agg["health"][0] == "FAIL"  # ...today's quote is the anomaly
        assert agg["status"] == "FAIL"
        assert scan.volume_gate_suppresses(agg["status"])

    def test_counterexample_unverified_cache_stays_insufficient_and_suppresses(self):
        df, meta = _contract_cache("600003", "2026-09-02")
        legacy_meta = {**meta, "cache_schema": 1}  # pre-normalization contract
        row = semantics.validate_symbol("600003", _quote("20260903", 800_000.0), df, legacy_meta)
        assert row["skip_reason"] == "cache_contract_invalid"
        assert row["cached_volume_unit"] == "unknown"
        assert row["quote_health"]["status"] == "not_available"
        agg = semantics.aggregate_rows([row], 1)
        assert agg["ingest"][0] == "INSUFFICIENT_EVIDENCE"
        assert agg["status"] == "INSUFFICIENT_EVIDENCE"
        assert scan.volume_gate_suppresses(agg["status"])

    def test_quote_anomaly_fails_even_when_all_other_symbols_pending(self):
        good, good_meta = _contract_cache("600004", "2026-09-02")
        bad, bad_meta = _contract_cache("600005", "2026-09-02")
        rows = [
            semantics.validate_symbol("600004", _quote("20260903", 800_000.0), good, good_meta),
            semantics.validate_symbol("600005", _quote("20260902", 3_000_000.0), bad, bad_meta),
        ]
        agg = semantics.aggregate_rows(rows, 2)
        assert agg["health"][0] == "FAIL"
        assert agg["status"] == "FAIL"

    def test_composed_pass_reason_names_both_verdicts(self):
        ingest = semantics.ingest_semantics_status({"share"}, {"share": 50}, 50, 50)
        health = semantics.quote_health_status([{"status": "pending_eod"}] * 50)
        status, reason = semantics.compose_overall(ingest, health)
        assert status == "PASS"
        assert "PENDING" in reason and "canonical share" in reason
        assert not scan.volume_gate_suppresses(status)


class TestTimingTemporalAlignment:
    def test_t_minus_one_t_and_future_histories_are_equivalent(self):
        days = pd.date_range("2021-01-01", periods=40, freq="D")
        t = days[30]
        hist = pd.DataFrame({
            "date": days,
            "close": [10.0] * 31 + [999.0] * 9,
            "volume": [1_000_000.0] * 31 + [999_000_000.0] * 9,
        })
        quote = {"date": t.strftime("%Y%m%d"), "price": 9.0, "volume": 2_000_000.0}
        a = scan.timing_from_quote_hist(quote, hist[hist["date"] < t])
        b = scan.timing_from_quote_hist(quote, hist[hist["date"] <= t])
        c = scan.timing_from_quote_hist(quote, hist)
        assert a == b == c

    def test_unparseable_dates_fail_closed(self):
        hist = pd.DataFrame({"date": ["bad"] * 25, "close": [10.0] * 25, "volume": [1.0] * 25})
        assert scan.timing_from_quote_hist({"date": "bad", "price": 10, "volume": 1}, hist) is None


# ---------------------------------------------------------------------------
# P0.2 separated data-quality dimensions: coverage=100% is not overall green
# ---------------------------------------------------------------------------

from datetime import datetime

DQ_NOW = datetime(2026, 9, 3, 12, 0, tzinfo=biz.TZ_SHANGHAI)


def make_dq_snapshot(**overrides) -> dict:
    snap = {
        "as_of": "2026-09-03T11:42:19+08:00",
        "status": "OK",
        "coverage": 1.0,
        "candidate_count": 1,
        "concentration": "enforced",
        "sources": {},
        "source_degradations": [],
        "candidates": [
            {"symbol": "600000", "red_flags": [], "data_freshness": {"financial_date": "2026-06-30"}}
        ],
    }
    snap.update(overrides)
    return snap


def make_dq_scan(**overrides) -> dict:
    scan = {"as_of": "2026-09-03T11:44:00+08:00", "latest_quote_time": "20260903 114421"}
    scan.update(overrides)
    return scan


def write_semantic_proof(tmp_path, *, status="PASS", universe_as_of="2026-09-03T11:42:19+08:00", sample=1):
    p = tmp_path / "semantic_proof_20260903T120000Z.json"
    p.write_text(json.dumps({"status": status, "reason": "r", "universe_as_of": universe_as_of, "sample_size": sample}))
    return tmp_path


class TestSeparatedDataQuality:
    def test_perfect_coverage_with_unknown_pit_is_not_green(self, tmp_path):
        dq = biz.data_quality(make_dq_snapshot(), make_dq_scan(), semantic_dir=write_semantic_proof(tmp_path), now=DQ_NOW)
        assert dq["dimensions"]["coverage"]["status"] == "PASS"
        assert dq["dimensions"]["semantic_integrity"]["status"] == "PASS"
        assert dq["dimensions"]["pit"]["status"] == "UNKNOWN"
        assert dq["status"] == "UNKNOWN"

    def test_semantic_fail_beats_perfect_coverage(self, tmp_path):
        dq = biz.data_quality(make_dq_snapshot(), make_dq_scan(), semantic_dir=write_semantic_proof(tmp_path, status="FAIL"), now=DQ_NOW)
        assert dq["dimensions"]["coverage"]["status"] == "PASS"
        assert dq["dimensions"]["semantic_integrity"]["status"] == "FAIL"
        assert dq["status"] == "FAIL"
        assert "semantic_integrity=FAIL" in dq["banner"]

    def test_stale_proof_after_pool_rebuild_demotes_to_warn(self, tmp_path):
        dq = biz.data_quality(make_dq_snapshot(), make_dq_scan(), semantic_dir=write_semantic_proof(tmp_path, universe_as_of="2026-09-02T00:00:00+08:00"), now=DQ_NOW)
        assert dq["dimensions"]["semantic_integrity"]["status"] == "WARN"
        assert "池重建后必须重跑 validator" in dq["dimensions"]["semantic_integrity"]["detail"]
        assert dq["status"] == "WARN"

    def test_missing_proof_is_unknown_not_pass(self, tmp_path):
        dq = biz.data_quality(make_dq_snapshot(), make_dq_scan(), semantic_dir=tmp_path, now=DQ_NOW)
        assert dq["dimensions"]["semantic_integrity"]["status"] == "UNKNOWN"

    def test_yesterdays_quotes_warn(self, tmp_path):
        dq = biz.data_quality(make_dq_snapshot(), make_dq_scan(latest_quote_time="20260902 150000"), semantic_dir=write_semantic_proof(tmp_path), now=DQ_NOW)
        assert dq["dimensions"]["freshness"]["status"] == "WARN"

    def test_stale_financial_red_flag_warns_freshness(self, tmp_path):
        snap = make_dq_snapshot()
        snap["candidates"][0]["red_flags"] = ["FINANCIAL_DATA_STALE"]
        dq = biz.data_quality(snap, make_dq_scan(), semantic_dir=write_semantic_proof(tmp_path), now=DQ_NOW)
        assert dq["dimensions"]["freshness"]["status"] == "WARN"

    def test_degraded_source_keeps_degraded_flag_and_source_warn(self, tmp_path):
        snap = make_dq_snapshot(status="DEGRADED", source_degradations=[{"source": "financial", "error": "boom"}])
        dq = biz.data_quality(snap, make_dq_scan(), semantic_dir=write_semantic_proof(tmp_path), now=DQ_NOW)
        assert dq["degraded"] is True
        assert dq["dimensions"]["source_degradation"]["status"] == "WARN"

    def test_no_snapshot_still_missing(self):
        dq = biz.data_quality(None, None)
        assert dq["status"] == "MISSING" and dq["dimensions"] == {}


# ---------------------------------------------------------------------------
# P0.3 PIT correctness audit
# ---------------------------------------------------------------------------

import quant_pit_audit as pit


class TestPitAudit:
    def test_worst_pit_ordering(self):
        assert pit.worst_pit(["CLEAN", "PARTIAL"]) == "PARTIAL"
        assert pit.worst_pit(["PARTIAL", "UNKNOWN"]) == "PARTIAL"
        assert pit.worst_pit(["UNKNOWN", "CLEAN"]) == "UNKNOWN"
        assert pit.worst_pit(["CONTAMINATED", "PARTIAL"]) == "CONTAMINATED"

    def test_current_membership_backapplied_is_contaminated(self):
        meta = {"pit_limitation": "current membership applied to all historical dates", "basis": "b"}
        a = pit.membership_historical_aspect(meta, ("2018-01-01", "2022-12-31"))
        assert a["status"] == "CONTAMINATED"

    def test_financial_without_announcement_dates_is_partial(self):
        a = pit.financial_announcement_aspect([{"report_date": "2026-06-30"}, {"report_date": "2025-12-31"}])
        assert a["status"] == "PARTIAL"
        assert "公告日期" in a["finding"]

    def test_financial_with_announcement_dates_is_clean(self):
        a = pit.financial_announcement_aspect([{"report_date": "2026-06-30", "announcement_date": "2026-08-20"}])
        assert a["status"] == "CLEAN"

    def test_partial_announcement_coverage_is_not_clean(self):
        a = pit.financial_announcement_aspect([
            {"report_date": "2026-06-30", "announcement_date": "2026-08-20"},
            {"report_date": "2025-12-31"},
        ])
        assert a["status"] == "PARTIAL" and "1/2" in a["finding"]

    def test_valuation_complete_metas_clean(self):
        a = pit.valuation_asof_aspect([{"series_last_date": "2026-09-02", "retrieved_at": "2026-09-03T10:00:00+08:00"}])
        assert a["status"] == "CLEAN"

    def test_adjustment_needs_both_faces_and_rules(self):
        assert pit.adjustment_semantics_aspect([{"adjust": "qfq"}, {"adjust": "raw"}], True)["status"] == "CLEAN"
        assert pit.adjustment_semantics_aspect([{"adjust": "qfq"}], True)["status"] == "PARTIAL"
        assert pit.adjustment_semantics_aspect([{"adjust": "qfq"}, {"adjust": "raw"}], False)["status"] == "PARTIAL"

    def test_adjustment_is_checked_per_research_symbol(self):
        metas = [
            {"symbol": "A", "adjust": "qfq", "date_range": ["2018-01-01", "2022-12-31"]},
            {"symbol": "A", "adjust": "raw", "date_range": ["2018-01-01", "2022-12-31"]},
            {"symbol": "B", "adjust": "qfq", "date_range": ["2018-01-01", "2022-12-31"]},
        ]
        result = pit.adjustment_semantics_aspect(
            metas, True, ["A", "B"], ("2018-01-01", "2022-12-31")
        )
        assert result["status"] == "PARTIAL" and result["missing_symbols"] == ["B"]

    def _tmp_repo(self, tmp_path, limitation):
        cache = tmp_path / "cache"
        for sub in ("universe", "fundamentals", "valuation3y", "daily"):
            (cache / sub).mkdir(parents=True)
        (cache / "universe" / "csi500_subset.meta.json").write_text(
            json.dumps({"pit_limitation": limitation, "basis": "b"})
        )
        gen1 = tmp_path / "gen1"
        gen1.mkdir()
        (gen1 / "quant.toml").write_text(
            '[execution]\ncommission_rate = 0.00025\n\n[research]\nresearch_start = "2018-01-01"\nresearch_end = "2022-12-31"\n'
        )
        return cache, gen1

    def test_audit_contaminated_when_membership_backapplied(self, tmp_path):
        cache, gen1 = self._tmp_repo(tmp_path, "current membership applied to all historical dates")
        r = pit.audit(snapshot_path=tmp_path / "missing.json", cache=cache, gen1=gen1)
        assert r["verdict"] == "PIT_CONTAMINATED"
        assert r["aspects"]["membership_historical"]["status"] == "CONTAMINATED"

    def test_audit_partial_when_no_contamination(self, tmp_path):
        cache, gen1 = self._tmp_repo(tmp_path, "")
        r = pit.audit(snapshot_path=tmp_path / "missing.json", cache=cache, gen1=gen1)
        assert r["verdict"] == "PIT_PARTIAL"

    def test_audit_insufficient_evidence_when_nothing_auditable(self, tmp_path):
        cache = tmp_path / "cache"
        cache.mkdir()
        gen1 = tmp_path / "gen1"
        gen1.mkdir()
        (gen1 / "quant.toml").write_text("[research]\nresearch_start = \"2018-01-01\"\n")
        r = pit.audit(snapshot_path=tmp_path / "missing.json", cache=cache, gen1=gen1)
        assert r["verdict"] is None


class TestPitDimension:
    def test_contaminated_maps_to_fail_and_fails_overall(self, tmp_path):
        (tmp_path / "pit_audit_20260903T120000Z.json").write_text(
            json.dumps({"verdict": "PIT_CONTAMINATED", "implication": "历史回测宇宙带幸存者/前视污染"})
        )
        dq = biz.data_quality(make_dq_snapshot(), make_dq_scan(), semantic_dir=tmp_path, now=DQ_NOW)
        assert dq["dimensions"]["pit"]["status"] == "FAIL"
        assert dq["status"] == "FAIL"

    def test_clean_maps_to_pass_and_overall_pass(self, tmp_path):
        (tmp_path / "pit_audit_20260903T120000Z.json").write_text(json.dumps({"verdict": "PIT_CLEAN", "implication": "ok"}))
        (tmp_path / "semantic_proof_20260903T120000Z.json").write_text(
            json.dumps({"status": "PASS", "reason": "ok", "universe_as_of": "2026-09-03T11:42:19+08:00", "sample_size": 1})
        )
        dq = biz.data_quality(make_dq_snapshot(), make_dq_scan(), semantic_dir=tmp_path, now=DQ_NOW)
        assert dq["dimensions"]["pit"]["status"] == "PASS"
        assert dq["dimensions"]["semantic_integrity"]["status"] == "PASS"
        assert dq["status"] == "PASS"


# ---------------------------------------------------------------------------
# P0.4 anti-leakage behavioral check (pure logic; qlib path runs in side env)
# ---------------------------------------------------------------------------

from datetime import date

import pandas as pd
import quant_anti_leakage_check as leak
from quant_core import Intent


def make_panel(dates, symbols, close=10.0, volume=1_000_000.0):
    idx = pd.MultiIndex.from_product([dates, symbols], names=["datetime", "instrument"])
    n = len(dates) * len(symbols)
    return pd.DataFrame(
        {
            "open": [close] * n,
            "close": [close] * n,
            "volume": [volume] * n,
            "prev_close": [close - 0.1] * n,
            "close_5d_ago": [close * 1.05] * n,
            "ma5": [close - 0.05] * n,
            "volume_ma20": [volume * 0.5] * n,
        },
        index=idx,
    )


class TestAntiLeakage:
    def test_identical_replays_change_nothing(self):
        days = [pd.Timestamp("2021-01-04").date(), pd.Timestamp("2021-01-05").date()]
        f = leak.factor_frame(make_panel(days, ["600000"]))
        diffs, compared = leak.compare_factors(f, f.copy(), days)
        assert diffs == [] and compared == 2

    def test_injected_future_leak_is_itemized_not_masked(self):
        days = [pd.Timestamp("2021-01-04").date(), pd.Timestamp("2021-01-05").date()]
        full = leak.factor_frame(make_panel(days, ["600000"]))
        trunc_panel = make_panel(days, ["600000"])
        trunc_panel.iloc[0, trunc_panel.columns.get_loc("close_5d_ago")] = 99.0
        diffs, _ = leak.compare_factors(full, leak.factor_frame(trunc_panel), days)
        assert len(diffs) == 1
        assert diffs[0]["item"] == "factor:pullback_5d"
        assert diffs[0]["full"] != diffs[0]["truncated"]

    def test_membership_diff_reports_symbol_sets(self):
        day = [pd.Timestamp("2021-01-04").date()]
        full = leak.factor_frame(make_panel(day, ["000001", "600000"]))
        trunc = leak.factor_frame(make_panel(day, ["600000"]))
        diffs = leak.compare_membership(full, trunc, day)
        assert len(diffs) == 1 and diffs[0]["only_in_full"] == ["000001"]

    def test_intent_changes_are_reported(self):
        lo, hi = date(2021, 1, 1), date(2021, 12, 31)
        full = [Intent("BUY", "600000", date(2021, 3, 1)), Intent("SELL", "600000", date(2021, 3, 5))]
        trunc = [Intent("BUY", "600000", date(2021, 3, 8)), Intent("SELL", "600000", date(2021, 3, 12))]
        cmp = leak.compare_intents(full, trunc, lo, hi)
        assert cmp["entry_intents"]["changed"] and cmp["entry_intents"]["diff_count"] == 2
        assert cmp["exit_intents"]["changed"]

    def test_timing_passes_with_date_aligned_impl(self, monkeypatch):
        dates = pd.date_range("2021-01-01", periods=60, freq="D").date
        hist = pd.DataFrame({"date": dates, "close": [10 + 0.1 * (i % 3) for i in range(60)], "volume": [1_000_000.0] * 60})
        monkeypatch.setattr(leak, "read_cache", lambda kind, key, cache_dir=None: (hist, {}))
        res = leak.timing_surface_check(["600000"], [str(dates[40])])
        # the date-aligned production function self-truncates to the quote
        # date, so adversarial future rows cannot move the past
        assert res["checked"] == 1
        assert res["status"] == "PASS"

    def test_timing_check_has_teeth_against_frame_relative_impl(self, monkeypatch):
        dates = pd.date_range("2021-01-01", periods=60, freq="D").date
        hist = pd.DataFrame({"date": dates, "close": [10 + 0.1 * (i % 3) for i in range(60)], "volume": [1_000_000.0] * 60})
        monkeypatch.setattr(leak, "read_cache", lambda kind, key, cache_dir=None: (hist, {}))

        def legacy_frame_relative_timing(quote, h):
            # the pre-fix implementation: frame-end-relative, ignores quote date
            h = h.sort_values("date")
            if len(h) < 25:
                return None
            return (
                float(quote["price"]) / float(h["close"].iloc[-6]) - 1,
                float(quote["volume"]) / float(h["volume"].tail(20).mean()),
            )

        monkeypatch.setattr(leak, "timing_from_quote_hist", legacy_frame_relative_timing)
        res = leak.timing_surface_check(["600000"], [str(dates[40])])
        # the experiment must FAIL the implementation that was actually
        # shipped before the review fix — a vacuous test could not
        assert res["status"] == "FAIL" and res["diff_count"] == 1

    def test_scoped_verdict_reducer(self):
        assert leak.scoped_verdict([{"status": "PASS"}], {"status": "PASS"}) == "P0_4_SCOPED_PASS"
        assert leak.scoped_verdict([{"status": "PASS"}], {"status": "FAIL"}) == "P0_4_FAIL"
        assert leak.scoped_verdict([{"status": "LOOKAHEAD_FAIL"}], {"status": "PASS"}) == "P0_4_FAIL"
        assert leak.scoped_verdict([], {"status": "PASS"}) == "P0_4_UNKNOWN"
        assert leak.scoped_verdict([{"status": "UNKNOWN"}], {"status": "PASS"}) == "P0_4_UNKNOWN"

# ---------------------------------------------------------------------------
# NOW projection (now_snapshot): heartbeat != last successful scan,
# session-aware stale, event-matched agent brief, durable attention
# ---------------------------------------------------------------------------


IN_SESSION = datetime(2026, 9, 4, 11, 10, tzinfo=biz.TZ_SHANGHAI)   # Friday
AFTER_CLOSE = datetime(2026, 9, 4, 19, 47, tzinfo=biz.TZ_SHANGHAI)

NOW_STATE = {
    "as_of": "2026-09-04T11:07:42+08:00", "day": "2026-09-04", "status": "ALERTS",
    "symbols_scanned": 50, "data_trust": "PASS", "ready": [], "near": [],
    "exit_alerts": [], "positions": [], "market_no_trade": False, "system_unavailable": False,
}


def write_now_env(env, *, alerts=None, soak=None, state=None):
    env["trading"].mkdir(parents=True, exist_ok=True)
    (env["trading"] / "state.json").write_text(json.dumps(state if state is not None else NOW_STATE), encoding="utf-8")
    for name, rows in (("soak.jsonl", soak), ("alerts.jsonl", alerts)):
        if rows is not None:
            (env["trading"] / name).write_text(
                "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def write_brief(env, decision_id, *, symbol, recorded_at, action="WATCH"):
    env["briefs"].mkdir(parents=True, exist_ok=True)
    (env["briefs"] / f"{decision_id}.json").write_text(json.dumps({
        "decision_id": decision_id, "symbol": symbol, "action": action,
        "recorded_at": recorded_at, "why": "w", "invalidation": "i",
    }), encoding="utf-8")


class TestNowSnapshot:
    def _snap(self, env, now):
        return biz.now_snapshot(
            trading_dir=env["trading"], briefs_dir=env["briefs"],
            active_symbols_path=env["active_symbols"], now=now,
        )

    def test_heartbeat_and_last_scan_split(self, biz_env):
        write_now_env(biz_env, soak=[
            {"ts": "2026-09-04T09:31:00+08:00", "status": "MARKET_CLOSED", "symbols": 0},
            {"ts": "2026-09-04T11:07:00+08:00", "status": "NO_TRADE", "symbols": 50},
        ])
        biz_env["active_symbols"].write_text(json.dumps({"symbols": ["600000", "600001"]}))
        n = self._snap(biz_env, IN_SESSION)
        assert n["heartbeat_at"] == "2026-09-04T11:07:00+08:00"
        assert n["last_scan_at"] == "2026-09-04T11:07:00+08:00"
        assert n["universe_size"] == 2 and n["market"] == "OPEN" and n["data_trust"] == "PASS"
        # a closing-only soak never becomes a fake scan
        write_now_env(biz_env, soak=[
            {"ts": "2026-09-04T19:10:35+08:00", "status": "MARKET_CLOSED", "symbols": 0},
        ], state={**NOW_STATE, "status": "MARKET_CLOSED", "symbols_scanned": 0})
        n2 = self._snap(biz_env, AFTER_CLOSE)
        assert n2["heartbeat_at"] == "2026-09-04T19:10:35+08:00" and n2["last_scan_at"] is None
        assert n2["market"] == "CLOSED" and n2["stale"] is False

    def test_stale_only_when_session_expects_a_live_loop(self, biz_env):
        write_now_env(biz_env, soak=[
            {"ts": "2026-09-04T11:07:00+08:00", "status": "NO_TRADE", "symbols": 50},
        ])
        n = self._snap(biz_env, IN_SESSION)  # heartbeat age 180s in-session
        assert n["stale"] is True and n["runtime"] == "STALE"
        n2 = self._snap(biz_env, AFTER_CLOSE)  # same age after close: not a fault
        assert n2["stale"] is False and n2["runtime"] == "HEALTHY"

    def test_ready_attention_with_event_matched_brief(self, biz_env):
        write_now_env(biz_env, alerts=[
            {"ts": "2026-09-04T11:07:42+08:00", "type": "NEW_READY", "symbol": "601799",
             "price": 76.32, "what": "none -> READY", "why": "frozen entry conditions met"},
        ], state={**NOW_STATE, "ready": ["601799"]})
        # an older judgement must never answer a newer material event
        write_brief(biz_env, "brief-20260903-601799", symbol="601799",
                    recorded_at="2026-09-03T18:28:00+08:00", action="WATCH")
        n = self._snap(biz_env, IN_SESSION)
        item = n["attention"][0]
        assert item["kind"] == "READY" and item["price"] == 76.32 and item["agent"] is None
        write_brief(biz_env, "brief-20260904-601799", symbol="601799",
                    recorded_at="2026-09-04T11:09:00+08:00", action="WATCH")
        n2 = self._snap(biz_env, IN_SESSION)
        assert n2["attention"][0]["agent"]["decision_id"] == "brief-20260904-601799"

    def test_exit_attention_carries_position_and_human_fact(self, biz_env):
        write_now_env(biz_env, alerts=[
            {"ts": "2026-09-04T10:00:00+08:00", "type": "POSITION_OPENED", "symbol": "601799",
             "price": 74.88, "venue": "paper", "note": "entry"},
            {"ts": "2026-09-04T14:17:00+08:00", "type": "POSITION_EXIT_ALERT", "symbol": "601799",
             "what": "HOLD -> EXIT_ALERT", "why": "close_below_ma5"},
        ], state={**NOW_STATE, "exit_alerts": ["601799"], "data_trust": "FAIL",
                  "positions": [{"symbol": "601799", "entry_price": 74.88, "price": 77.2,
                                 "pnl": 232.0, "shares": 100, "venue": "paper", "state": "EXIT_ALERT"}]})
        n = self._snap(biz_env, IN_SESSION)
        kinds = {i["kind"] for i in n["attention"]}
        assert {"EXIT", "DATA_UNTRUSTED"} <= kinds
        exit_item = next(i for i in n["attention"] if i["kind"] == "EXIT")
        assert exit_item["why"] == "close_below_ma5" and exit_item["entry_price"] == 74.88
        assert exit_item["venue"] == "paper"
        assert exit_item["human"]["action"].startswith("HOLD")

    def test_system_unavailable_surfaces_as_attention(self, biz_env):
        write_now_env(biz_env, state={**NOW_STATE, "status": "SYSTEM_UNAVAILABLE",
                                      "system_unavailable": True, "data_trust": "UNKNOWN"})
        n = self._snap(biz_env, IN_SESSION)
        assert any(i["kind"] == "SYSTEM_UNAVAILABLE" for i in n["attention"])

    def test_timeline_lists_only_state_day_events(self, biz_env):
        write_now_env(biz_env, alerts=[
            {"ts": "2026-09-03T14:00:00+08:00", "day": "2026-09-03", "type": "NEW_NEAR", "symbol": "600015", "what": "none -> NEAR"},
            {"ts": "2026-09-04T11:07:42+08:00", "day": "2026-09-04", "type": "NEW_READY", "symbol": "601799", "what": "none -> READY"},
        ])
        rows = biz.load_timeline(biz_env["trading"], day="2026-09-04")
        assert [r["type"] for r in rows] == ["NEW_READY"]

    def test_build_data_embeds_now_and_timeline(self, biz_env):
        write_trading(biz_env, [CLOSED_POINT])
        (biz_env["trading"] / "state.json").write_text(json.dumps({
            "as_of": CLOSED_POINT["ts"], "day": "2026-09-04",
            "status": "MARKET_CLOSED", "data_trust": "UNKNOWN",
        }), encoding="utf-8")
        data = build_with_rt(biz_env)
        assert data["now"]["present"] is True
        assert data["now"]["runtime"] in ("HEALTHY", "STALE", "UNKNOWN")
        assert isinstance(data["timeline"], list)
        html = biz.render_html(data)
        assert 'id="now-card"' in html and "今日事件时间线" in html
        assert "尚未复核" in html  # agent three-state exists even without briefs


class TestAckCommandBuilder:
    def test_buy_builds_canonical_argv(self):
        cmd = serve.ack_command_for("ack-buy", {
            "symbol": "601799", "shares": 100, "price": 76.32, "venue": "paper",
            "executed_at": "2026-09-04T11:07:42+08:00", "note": "n",
        })
        assert "tools/quant_trading_monitor.py" in cmd and "ack-buy" in cmd
        assert cmd[cmd.index("--state-dir") + 1] == "workspace/artifacts/quant/trading"
        assert cmd[cmd.index("--venue") + 1] == "paper"
        assert cmd[cmd.index("--shares") + 1] == "100"
        assert cmd[cmd.index("--note") + 1] == "n"

    def test_skip_needs_no_venue_or_shares(self):
        cmd = serve.ack_command_for("skip", {
            "symbol": "601799", "price": 76.32,
            "executed_at": "2026-09-04T11:07:42+08:00",
        })
        assert "skip" in cmd and "--venue" not in cmd and "--shares" not in cmd

    @pytest.mark.parametrize("kind,payload,match", [
        ("ack-buy", {"shares": 1, "price": 1, "venue": "paper", "executed_at": "t"}, "symbol"),
        ("ack-buy", {"symbol": "X", "price": 1, "venue": "paper", "executed_at": "t"}, "shares"),
        ("ack-buy", {"symbol": "X", "shares": 1, "venue": "paper"}, "executed_at"),
        ("ack-buy", {"symbol": "X", "shares": 1, "venue": "paper", "executed_at": "t"}, "price"),
        ("ack-buy", {"symbol": "X", "shares": 1, "price": 1, "executed_at": "t"}, "venue"),
        ("ack-buy", {"symbol": "X", "shares": 1, "price": 1, "venue": "demo", "executed_at": "t"}, "venue"),
        ("ack-buy", {"symbol": "X", "shares": 1.5, "price": 1, "venue": "paper", "executed_at": "t"}, "shares"),
        ("skip", {"symbol": "X", "executed_at": "t"}, "price"),
        ("nope", {"symbol": "X"}, "unknown ack kind"),
    ])
    def test_missing_or_invalid_fields_rejected(self, kind, payload, match):
        with pytest.raises(ValueError, match=match):
            serve.ack_command_for(kind, payload)

    def test_writes_are_loopback_only(self):
        assert all(serve.writes_enabled_for_host(h) for h in ("127.0.0.1", "localhost", "::1"))
        assert not any(serve.writes_enabled_for_host(h) for h in ("0.0.0.0", "192.168.1.5", "example.com"))


class TestQuantHttpApi:
    import threading
    import urllib.error
    import urllib.request

    def _server(self):
        srv = serve.ThreadingHTTPServer(("127.0.0.1", 0), serve.Handler)
        thread = self.threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        return srv

    def _post(self, port, path, payload):
        req = self.urllib.request.Request(
            f"http://127.0.0.1:{port}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        return self.urllib.request.urlopen(req, timeout=5)

    def test_post_ack_invokes_canonical_command(self, monkeypatch):
        captured = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"] = cmd
            return type("R", (), {"returncode": 0, "stdout": '{"position": "p-0001"}', "stderr": ""})()

        monkeypatch.setattr(serve.subprocess, "run", fake_run)
        srv = self._server()
        try:
            with self._post(srv.server_address[1], "/api/quant/ack-buy", {
                "symbol": "601799", "shares": 100, "price": 76.32,
                "venue": "paper", "executed_at": "2026-09-04T11:07:42+08:00",
            }) as resp:
                body = json.loads(resp.read())
            assert body["position"] == "p-0001"
            assert "ack-buy" in captured["cmd"]
            assert captured["cmd"][captured["cmd"].index("--venue") + 1] == "paper"
        finally:
            srv.shutdown()

    def test_post_canonical_rejection_is_400_verbatim(self, monkeypatch):
        def rejecting_run(cmd, **kwargs):
            return type("R", (), {"returncode": 1, "stdout": "",
                                  "stderr": '{"error": "venue mismatch: position opened as paper"}'})()

        monkeypatch.setattr(serve.subprocess, "run", rejecting_run)
        srv = self._server()
        try:
            with pytest.raises(self.urllib.error.HTTPError) as err:
                self._post(srv.server_address[1], "/api/quant/ack-sell", {
                    "symbol": "601799", "shares": 100, "price": 77.2,
                    "venue": "real", "executed_at": "2026-09-04T14:17:00+08:00",
                })
            assert err.value.code == 400
            assert "venue mismatch" in err.value.read().decode()
        finally:
            srv.shutdown()

    def test_post_validation_error_is_400(self):
        srv = self._server()
        try:
            with pytest.raises(self.urllib.error.HTTPError) as err:
                self._post(srv.server_address[1], "/api/quant/ack-buy",
                           {"symbol": "601799", "shares": 100, "price": 76.32})
            assert err.value.code == 400
        finally:
            srv.shutdown()

    def test_post_disabled_on_non_loopback_host(self):
        srv = self._server()
        serve.Handler.writes_enabled = False
        try:
            with pytest.raises(self.urllib.error.HTTPError) as err:
                self._post(srv.server_address[1], "/api/quant/ack-buy", {
                    "symbol": "601799", "shares": 100, "price": 76.32,
                    "venue": "paper", "executed_at": "t",
                })
            assert err.value.code == 403
        finally:
            srv.shutdown()
            serve.Handler.writes_enabled = True
