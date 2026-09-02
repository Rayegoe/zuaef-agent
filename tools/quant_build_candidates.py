"""Deterministic candidate discovery for the quant business dashboard.

Builds the candidate pool behind docs/quant/business.html (spec pack
"Quant Business Dashboard + Candidate Discovery v1.0", T003/T004):

    CSI300 ∪ CSI500 membership
      → bounded snapshot quotes (Tencent batch)
      → cheap hard exclusions (ST / price / liquidity)
      → deterministic value+liquidity pre-rank → deep-coverage set (≤ --deep-max)
      → per-symbol deep data: Sina financials, cninfo SW industry,
        Tencent daily history, Baidu 3Y valuation history
      → transparent value/quality/tradeability/timing scoring
        (weights + thresholds in benchmarks/quant/gen1/candidates_policy.toml)
      → sector-capped stable ranking (≤ pool_target_max)
      → workspace/artifacts/quant/business/candidate_snapshot.json   (audit)
        data/quant-cache/candidates/active_symbols.json              (handoff)

Deterministic and host-owned: no Agent calls, no LLM anywhere. Every fetch
keeps source/retrieval metadata; source failure degrades with provenance
(cached fallback where valid) and missing essential coverage fails closed
(status DEGRADED / exit 2) — an empty or failed universe is never converted
into a legitimate NO_TRADE market conclusion. Candidate rank is NOT a buy
order or profitability claim; real actions still require the deterministic
live trigger (tools/quant_live_scan.py).

    uv run --group quant python tools/quant_build_candidates.py [--refresh]
        [--policy benchmarks/quant/gen1/candidates_policy.toml] [--deep-max 120]

Exit codes: 0 pool built (possibly DEGRADED); 2 empty candidate pool
(fail closed); 3 empty/unresolvable discovery base.
"""

from __future__ import annotations

import argparse
import json
import math
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from quant_core import (
    CACHE_DIR,
    TZ_SHANGHAI,
    fetch_history,
    load_config,
    read_cache,
    write_cache,
)
from quant_live_scan import (
    ACTIVE_SYMBOLS_PATH,
    LEGACY_WATCHLIST_PATH,
    fetch_batch_quotes,
    timing_from_quote_hist,
)

POLICY_PATH = Path("benchmarks/quant/gen1/candidates_policy.toml")
ACTIVE_STRATEGY_PATH = Path("benchmarks/quant/gen1/active.toml")
BUSINESS_ART_DIR = Path("workspace/artifacts/quant/business")
SNAPSHOT_PATH = BUSINESS_ART_DIR / "candidate_snapshot.json"

VALUATION_REFETCH_DAYS = 7
INDUSTRY_FRESH_DAYS = 365


# ---------------------------------------------------------------------------
# Pure mechanics (unit-tested offline; no network, no akshare at import)
# ---------------------------------------------------------------------------


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


_BASIS_ZH = {"industry": "同业", "pool": "全池"}


def basis_zh(basis: str | None) -> str:
    """Chinese wording for a percentile basis (industry-relative or pool)."""
    return _BASIS_ZH.get(basis or "", "全池")


def percentile_map(values: dict[str, float | None]) -> dict[str, float | None]:
    """Ascending percentile per symbol (0.0 = smallest observed value).

    Tied values share the average of their ranks, so identical fundamentals
    get identical percentiles; the result stays deterministic. Symbols with
    None stay None (missing — never folded into a rank).
    """
    items = sorted(((s, v) for s, v in values.items() if v is not None), key=lambda kv: (kv[1], kv[0]))
    out: dict[str, float | None] = {s: None for s, v in values.items() if v is None}
    if not items:
        return out
    if len(items) == 1:
        out[items[0][0]] = 0.5
        return out
    n = len(items)
    i = 0
    while i < n:
        j = i
        while j < n and items[j][1] == items[i][1]:
            j += 1
        avg_rank = sum(range(i, j)) / (j - i)
        for k in range(i, j):
            out[items[k][0]] = avg_rank / (n - 1)
        i = j
    return out


def group_percentiles(
    values: dict[str, float | None], groups: dict[str, str | None], min_peers: int
) -> tuple[dict[str, float | None], dict[str, str]]:
    """Industry-relative percentiles where the group has >= min_peers valid
    values, pool-relative otherwise. Returns (percentiles, basis per symbol
    with "industry"|"pool"|"missing")."""
    by_group: dict[str, list[str]] = {}
    for symbol, value in values.items():
        if value is None:
            continue
        g = groups.get(symbol) or "POOL"
        by_group.setdefault(g, []).append(symbol)
    out: dict[str, float | None] = {}
    basis: dict[str, str] = {}
    all_syms = list(values)
    group_syms_for = {s: (groups.get(s) or "POOL") for s in all_syms}
    pool_map = percentile_map({s: values[s] for s in all_syms})
    for symbol in all_syms:
        if values[symbol] is None:
            out[symbol] = None
            basis[symbol] = "missing"
            continue
        g = group_syms_for[symbol]
        members = [m for m in by_group.get(g, [])]
        if groups.get(symbol) and len(members) >= min_peers:
            gm = percentile_map({m: values[m] for m in members})
            out[symbol] = gm[symbol]
            basis[symbol] = "industry"
        else:
            out[symbol] = pool_map[symbol]
            basis[symbol] = "pool"
    return out, basis


def band_score(value: float | None, lo: float, hi: float) -> float | None:
    """Linear 0..1 band, clamped. lo may exceed hi (inverted bands fine)."""
    if value is None or hi == lo:
        return None
    return clamp01((value - lo) / (hi - lo))


def log_band(value: float | None, lo: float, hi: float) -> float | None:
    """Log-linear 0..1 band for turnover-style magnitudes."""
    if value is None or value <= 0 or lo <= 0 or hi <= lo:
        return None
    frac = (math.log(value) - math.log(lo)) / (math.log(hi) - math.log(lo))
    return clamp01(frac)


def normalize_block(components: list[tuple[str, float, float | None]]) -> tuple[float, list[str]]:
    """(achieved weight, name) triples -> (score fraction over available
    components, missing component names). Missing components renormalize the
    block instead of silently scoring zero."""
    available = [(n, w, a) for n, w, a in components if a is not None]
    total_w = sum(w for _n, w, _a in available)
    got = sum(a for _n, _w, a in available)
    missing = [n for n, _w, a in components if a is None]
    return (got / total_w if total_w > 0 else 0.0), missing


def sector_model_for(industry: str | None, policy: dict) -> str:
    if not industry:
        return "unsupported"
    names = policy["financial_sector"]["industry_gate_names"]
    if any(marker in industry for marker in names):
        return "financial"
    return "industrial"


def score_value(
    ctx: dict, pcts: dict, pbasis: dict, policy: dict
) -> tuple[float, list[str], list[str], list[str]]:
    """Value block (max 40). Negative PE is missing, never 'very cheap'."""
    vc = policy["value_components"]
    quote = ctx["quote"]
    pe = quote.get("pe_ttm")
    pb = quote.get("pb")
    dy = quote.get("dividend_yield_pct")
    components: list[tuple[str, float, float | None]] = []
    reasons: list[str] = []
    if pe is not None and pe > 0 and pcts.get("pe") is not None:
        frac = 1.0 - float(pcts["pe"])
        components.append(("pe_percentile", vc["pe_percentile"], frac * vc["pe_percentile"]))
        basis = pbasis.get("pe", "pool")
        reasons.append(
            f"PE(TTM) {pe:.1f},低于{basis_zh(basis)} {frac * 100:.0f}% 分位"
        )
    else:
        components.append(("pe_percentile", vc["pe_percentile"], None))
    if pb is not None and pb > 0 and pcts.get("pb") is not None:
        frac = 1.0 - float(pcts["pb"])
        components.append(("pb_percentile", vc["pb_percentile"], frac * vc["pb_percentile"]))
        if frac >= 0.6:
            reasons.append(f"PB {pb:.2f},低于{basis_zh(pbasis.get('pb', 'pool'))} {frac * 100:.0f}% 分位")
    else:
        components.append(("pb_percentile", vc["pb_percentile"], None))
    own = ctx.get("own_pe_pct")
    if own is not None:
        frac = 1.0 - float(own)
        components.append(("own_3y_percentile", vc["own_3y_percentile"], frac * vc["own_3y_percentile"]))
        if frac >= 0.6:
            reasons.append(f"3年 PE 处于自身历史 {own * 100:.0f}% 分位")
    else:
        components.append(("own_3y_percentile", vc["own_3y_percentile"], None))
    dy_full = vc["dividend_yield_full_pct"]
    dy_frac = band_score(dy if (dy is not None and dy > 0) else None, 0.0, dy_full)
    if dy_frac is not None:
        components.append(("dividend_yield", vc["dividend_yield"], dy_frac * vc["dividend_yield"]))
        if dy_frac >= 0.6:
            reasons.append(f"股息率 {dy:.1f}%")
    else:
        components.append(("dividend_yield", vc["dividend_yield"], None))
    fraction, missing = normalize_block(components)
    reasons.sort()
    return fraction, missing, reasons, [n for n, w, a in components]


def score_quality(
    ctx: dict, pcts: dict, pbasis: dict, policy: dict
) -> tuple[float, list[str], list[str], list[str], list[str]]:
    """Quality block (max 35). Financial companies skip industrial CFO /
    leverage rules (sector-aware; never fabricated)."""
    qc = policy["quality_components"]
    rf = policy["red_flags"]
    fin = ctx.get("financials") or {}
    model = ctx["sector_model"]
    components: list[tuple[str, float, float | None]] = []
    flags: list[str] = []
    reasons: list[str] = []
    roe3 = fin.get("roe_3y_avg")
    if roe3 is not None and pcts.get("roe") is not None:
        frac = float(pcts["roe"])
        components.append(("roe", qc["roe"], frac * qc["roe"]))
        if frac >= 0.6:
            reasons.append(f"3年 ROE {roe3:.1f}%,高于{basis_zh(pbasis.get('roe', 'pool'))}")
    else:
        components.append(("roe", qc["roe"], None))
    if model == "financial":
        # sector-appropriate block: ROE + growth only; CFO/leverage weights
        # drop out via renormalization instead of being fabricated
        missing_sector = [
            "cfo_to_net_profit (skipped: financial sector model)",
            "balance_safety (skipped: financial sector model)",
        ]
    else:
        missing_sector = []
        ratios = fin.get("cfo_np_annual") or []
        if ratios:
            latest = ratios[-1][1]
            frac = band_score(latest, qc["cfo_np_zero"], qc["cfo_np_full"])
            components.append(("cfo_to_net_profit", qc["cfo_to_net_profit"], frac * qc["cfo_to_net_profit"] if frac is not None else None))
            if frac is not None and frac >= 0.6:
                reasons.append(f"经营现金流/净利润 {latest:.2f}")
            if (
                len(ratios) >= 2
                and ratios[-1][1] < rf["cfo_np_min"]
                and ratios[-2][1] < rf["cfo_np_min"]
            ):
                flags.append("CFO_BELOW_NET_PROFIT_PERSISTENT")
        else:
            components.append(("cfo_to_net_profit", qc["cfo_to_net_profit"], None))
        debt = fin.get("debt_ratio")
        if debt is not None and pcts.get("debt") is not None:
            frac = 1.0 - float(pcts["debt"])
            components.append(("balance_safety", qc["balance_safety"], frac * qc["balance_safety"]))
            if frac < 0.15:
                flags.append("HIGH_LEVERAGE_REL_SECTOR")
        else:
            components.append(("balance_safety", qc["balance_safety"], None))
    rev_g = fin.get("rev_growth")
    np_g = fin.get("np_growth")
    if rev_g is not None and np_g is not None:
        avg = (rev_g + np_g) / 2.0
        frac = band_score(avg, qc["growth_zero_pct"], qc["growth_full_pct"])
        components.append(("growth", qc["growth"], frac * qc["growth"] if frac is not None else None))
        if np_g < 0:
            flags.append("PROFIT_GROWTH_NEGATIVE")
        if frac is not None and frac >= 0.7:
            reasons.append(f"收入/利润平均增速 {avg:.1f}%")
    else:
        components.append(("growth", qc["growth"], None))
    roe_annual = fin.get("roe_annual") or []
    if len(roe_annual) >= 3:
        prior = [v for _d, v in roe_annual[-3:-1]]
        if prior and roe_annual[-1][1] < rf["roe_decline_frac"] * (sum(prior) / len(prior)):
            flags.append("ROE_DETERIORATION")
    fraction, missing = normalize_block(components)
    if model == "financial":
        missing = sorted(set(missing + missing_sector))
    names = [n for n, w, a in components]
    reasons.sort()
    return fraction, missing, reasons, flags, names


def score_tradeability(ctx: dict, policy: dict) -> tuple[float, list[str], list[str]]:
    """Tradeability (max 15): can a small account realistically enter/exit.
    Not a momentum score."""
    tc = policy["tradeability_components"]
    quote = ctx["quote"]
    components: list[tuple[str, float, float | None]] = []
    reasons: list[str] = []
    liq_frac = log_band(quote.get("turnover_cny"), policy["eligibility"]["min_turnover_cny"], tc["turnover_full_cny"])
    if liq_frac is not None:
        components.append(("turnover", tc["turnover"], liq_frac * tc["turnover"]))
        if liq_frac >= 0.5:
            reasons.append(f"成交额 {quote['turnover_cny'] / 1e8:.1f}亿,小资金可进出")
    else:
        components.append(("turnover", tc["turnover"], None))
    rows = ctx.get("hist_rows")
    full = tc["history_full_rows"]
    if rows is not None and rows >= full:
        components.append(("history", tc["history"], tc["history"]))
    elif rows is not None:
        components.append(("history", tc["history"], tc["history"] * rows / full))
    else:
        components.append(("history", tc["history"], None))
    fraction, missing = normalize_block(components)
    return fraction, missing, reasons


def score_timing(
    timing: tuple[float, float] | None,
    strength: float | None,
    prev_close: float | None,
    active_cfg: dict,
) -> tuple[float, list[str], str, dict]:
    """Timing (max 10) from S3-compatible fields. Ranking/attention only —
    a real trade action still requires the deterministic live trigger."""
    if timing is None or strength is None or not prev_close:
        return 0.0, ["pullback_5d", "volume_ratio_20d", "close_strength"], "WAIT", {}
    pullback, ratio = timing
    entry_max = float(active_cfg["entry_pullback_max"])
    entry_vol = float(active_cfg["entry_volume_ratio_min"])
    t_pull = clamp01((0.0 - pullback) / (0.0 - entry_max)) if entry_max < 0 else 0.0
    t_vol = clamp01((ratio - 1.0) / (entry_vol - 1.0)) if entry_vol > 1.0 else 0.0
    t_str = clamp01(max(strength, 0.0) / (prev_close * 0.03))
    fraction = (t_pull * 4 + t_vol * 4 + t_str * 2) / 10.0
    if pullback <= entry_max and ratio >= entry_vol and strength >= 0:
        state = "TRIGGER"
    elif pullback <= entry_max * 0.5 or ratio >= entry_vol * 0.8:
        state = "NEAR"
    else:
        state = "WAIT"
    detail = {"pullback_5d": round(pullback, 4), "volume_ratio_20d": round(ratio, 3)}
    return fraction, [], state, detail


def build_red_flags(ctx: dict, policy: dict) -> list[str]:
    """Flags that must stay visible as text, never dissolve into the score."""
    flags: list[str] = []
    fin = ctx.get("financials")
    if fin is None or not fin.get("fresh", False):
        flags.append("FINANCIAL_DATA_STALE")
    if ctx["quote"].get("pe_ttm") is not None and ctx["quote"]["pe_ttm"] <= 0:
        flags.append("NEGATIVE_EARNINGS")
    if ctx.get("valuation_stale"):
        flags.append("VALUATION_DATA_STALE")
    if ctx.get("hist_rows") is not None and ctx["hist_rows"] < policy["eligibility"]["min_history_rows"]:
        flags.append("INSUFFICIENT_HISTORY")
    if ctx["quote"].get("turnover_cny") is not None and ctx["quote"]["turnover_cny"] < policy["eligibility"]["min_turnover_cny"]:
        flags.append("LOW_LIQUIDITY")
    if ctx.get("source_degraded"):
        flags.append("SOURCE_DEGRADED")
    return sorted(set(flags))


def evaluate_eligibility(ctx: dict, policy: dict) -> tuple[bool, list[str]]:
    """Hard exclusions (spec 03 §2). Deterministic; reasons reported."""
    reasons: list[str] = []
    name = ctx.get("name") or ""
    if any(pat in name for pat in policy["eligibility"]["exclude_name_patterns"]):
        reasons.append("ST_OR_RISK_WARNING_NAME")
    price = ctx["quote"].get("price")
    if price is None or price <= policy["eligibility"]["min_price"]:
        reasons.append("PRICE_NON_POSITIVE")
    turnover = ctx["quote"].get("turnover_cny")
    if turnover is None or turnover < policy["eligibility"]["min_turnover_cny"]:
        reasons.append("LOW_LIQUIDITY")
    if ctx.get("timing") is None or (ctx.get("hist_rows") or 0) < policy["eligibility"]["min_history_rows"]:
        reasons.append("INSUFFICIENT_HISTORY")
    pe = ctx["quote"].get("pe_ttm")
    if pe is not None and pe <= 0:
        reasons.append("NEGATIVE_EARNINGS")
    fin = ctx.get("financials")
    if fin is None:
        reasons.append("MISSING_FINANCIAL_DATA")
    elif not fin.get("fresh", False):
        reasons.append("FINANCIAL_DATA_STALE")
    return (len(reasons) == 0), reasons


def compute_tier(composite: float, red_flags: list[str], policy: dict) -> str:
    ranking = policy["ranking"]
    if composite >= ranking["tier_a_min"] and not any(f in ranking["critical_red_flags"] for f in red_flags):
        return "A"
    if composite >= ranking["tier_b_min"]:
        return "B"
    if composite >= ranking["tier_c_min"]:
        return "C"
    return "DROP"


def select_pool(ranked: list[dict], policy: dict) -> tuple[list[dict], str]:
    """Stable sector-capped pool selection.

    ranked must be sorted by (-composite_score, symbol). Within the first
    top_n_board selections each known first-level industry keeps at most
    sector_cap names; beyond the board window no cap applies. Unknown
    industries are never counted as fake diversification — if nothing is
    known the concentration status is "unknown".
    """
    cap = int(policy["ranking"]["sector_cap"])
    board_n = int(policy["ranking"]["top_n_board"])
    pool_max = int(policy["universe"]["pool_target_max"])
    selected: list[dict] = []
    counts: dict[str, int] = {}
    for row in ranked:
        if len(selected) >= pool_max:
            break
        industry = row.get("industry") or ""
        known = bool(industry.strip())
        if known and len(selected) < board_n and counts.get(industry, 0) >= cap:
            continue
        selected.append(row)
        if known:
            counts[industry] = counts.get(industry, 0) + 1
    known_any = any((r.get("industry") or "").strip() for r in selected)
    return selected, ("enforced" if known_any else "unknown")


def coverage_status(covered: int, total: int, policy: dict) -> tuple[float, str]:
    """Essential coverage fraction + OK/DEGRADED (fail closed below min)."""
    if total <= 0:
        return 0.0, "DEGRADED"
    frac = covered / total
    return frac, ("OK" if frac >= policy["coverage"]["essential_min"] else "DEGRADED")


# ---------------------------------------------------------------------------
# Fetchers (each with source/retrieval metadata; failure -> provenance)
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(TZ_SHANGHAI).isoformat()


def _days_since(day_str: str, today: date) -> int | None:
    try:
        d = date.fromisoformat(str(day_str)[:10])
    except ValueError:
        return None
    return (today - d).days


def _fetch_csindex(index_code: str, cache_key: str, refresh: bool, cache_dir: Path) -> tuple:
    if not refresh:
        df, meta = read_cache("universe", cache_key, cache_dir)
        if df is not None and meta is not None:
            return df, meta, "cache"
    import akshare as ak

    raw = ak.index_stock_cons_csindex(symbol=index_code)
    if raw is None or raw.empty:
        raise RuntimeError(f"empty constituent list for {index_code}")
    df = raw.rename(
        columns={
            "日期": "effective_date",
            "成分券代码": "constituent_code",
            "成分券名称": "constituent_name",
            "指数代码": "index_code",
            "指数名称": "index_name",
        }
    )
    df["effective_date"] = df["effective_date"].astype(str)
    df["constituent_code"] = df["constituent_code"].astype(str).str.zfill(6)
    meta = {
        "source": "akshare.index_stock_cons_csindex",
        "index": index_code,
        "retrieved_at": _now(),
        "rows": len(df),
        "effective_date": str(df["effective_date"].max()),
    }
    write_cache("universe", cache_key, df, meta, cache_dir)
    return df, meta, "live"


def resolve_membership(refresh: bool, cache_dir: Path) -> dict:
    """CSI300 ∪ CSI500. One index failing falls back to its last valid cached
    membership with freshness marked; never silently faked as fresh."""
    names: dict[str, str] = {}
    sources: dict[str, dict] = {}
    degradations: list[dict] = []
    for index_code, key, label in (("000300", "csi300_cons", "csi300"), ("000905", "csi500_cons", "csi500")):
        try:
            df, meta, mode = _fetch_csindex(index_code, key, refresh, cache_dir)
            got = dict(zip(df["constituent_code"], df["constituent_name"]))
            names.update(got)
            sources[label] = {
                "source": "akshare.index_stock_cons_csindex",
                "index": index_code,
                "mode": mode,
                "retrieved_at": meta.get("retrieved_at"),
                "effective_date": meta.get("effective_date"),
                "count": len(got),
                "fallback_used": False,
            }
        except Exception as exc:  # noqa: BLE001 — degrade with provenance
            df, meta = read_cache("universe", key, cache_dir)
            if df is not None and meta is not None:
                got = dict(zip(df["constituent_code"], df["constituent_name"]))
                names.update(got)
                sources[label] = {
                    "source": meta.get("source", "cached"),
                    "index": index_code,
                    "mode": "cache_fallback",
                    "retrieved_at": meta.get("retrieved_at"),
                    "effective_date": meta.get("effective_date"),
                    "count": len(got),
                    "fallback_used": True,
                }
                degradations.append(
                    {"source": f"membership:{label}", "error": str(exc)[:200], "fallback": "last valid cached membership"}
                )
            else:
                sources[label] = {
                    "source": "akshare.index_stock_cons_csindex",
                    "index": index_code,
                    "mode": "failed",
                    "count": 0,
                    "fallback_used": False,
                }
                degradations.append({"source": f"membership:{label}", "error": str(exc)[:200], "fallback": "none"})
    return {"names": names, "sources": sources, "degradations": degradations}


def get_financials(symbol: str, policy: dict, refresh: bool, cache_dir: Path, today: date) -> dict | None:
    """Sina financial analysis indicator (annual rows), cached with provenance.

    Freshness is the REPORT date budget (annual reporting cycle), not the
    retrieval date: a cached fetch whose report is still fresh keeps the
    pipeline alive when a transport fails (spec T004), while genuinely
    stale reports fail closed (FINANCIAL_DATA_STALE).
    """
    budget = int(policy["eligibility"]["financial_stale_days"])
    if not refresh:
        df, meta = read_cache("fundamentals", symbol, cache_dir)
        if df is not None and meta is not None:
            parsed = parse_financials(df, meta, today, budget)
            if parsed and parsed.get("fresh"):
                return parsed
    import akshare as ak

    try:
        raw = ak.stock_financial_analysis_indicator(symbol=symbol, start_year=str(today.year - 3))
    except Exception as exc:  # noqa: BLE001 — degrade with provenance
        df, meta = read_cache("fundamentals", symbol, cache_dir)
        if df is not None and meta is not None:
            parsed = parse_financials(df, meta, today, budget)
            if parsed:
                parsed["source_degraded"] = True
                parsed["fetch_error"] = str(exc)[:200]
                return parsed
        return None
    if raw is None or raw.empty:
        return None
    df = raw.copy()
    df["日期"] = df["日期"].astype(str)
    meta = {
        "source": "akshare.stock_financial_analysis_indicator (sina)",
        "symbol": symbol,
        "retrieved_at": _now(),
        "rows": len(df),
        "report_date": str(df["日期"].max())[:10],
    }
    write_cache("fundamentals", symbol, df, meta, cache_dir)
    parsed = parse_financials(df, meta, today, budget)
    if parsed is None:
        return None
    if not parsed["fresh"]:
        # report itself older than budget — re-check the fresh live fetch once
        return parsed
    return parsed


def parse_financials(df, meta: dict, today: date, budget_days: int) -> dict | None:
    """Extract deterministic quality fields from the Sina indicator table."""
    try:
        if "日期" not in df.columns:
            return None
        df = df.copy()
        df["日期"] = df["日期"].astype(str)

        def col(*names: str) -> str | None:
            for n in names:
                if n in df.columns:
                    return n
            return None

        roe_col = col("加权净资产收益率(%)", "净资产收益率(%)")
        cfo_col = col("经营现金净流量与净利润的比率(%)")
        debt_col = col("资产负债率(%)")
        rev_col = col("主营业务收入增长率(%)")
        np_col = col("净利润增长率(%)")
        annual = df[df["日期"].str.endswith("12-31")].copy()
        base = annual if len(annual) >= 2 else df
        base = base.sort_values("日期")

        def series(c: str | None, n: int) -> list[tuple[str, float]]:
            if c is None:
                return []
            sub = base[base[c].notna()].tail(n)
            out = []
            for _idx, row in sub.iterrows():
                try:
                    out.append((str(row["日期"])[:10], float(row[c])))
                except (TypeError, ValueError):
                    continue
            return out

        roe_annual = series(roe_col, 3)
        cfo_np = series(cfo_col, 3)

        def latest_of(c: str | None) -> float | None:
            if c is None:
                return None
            sub = base[base[c].notna()]
            if sub.empty:
                return None
            try:
                return float(sub.iloc[-1][c])
            except (TypeError, ValueError):
                return None

        report_date = str(df["日期"].max())[:10]
        age = _days_since(report_date, today)
        roe_3y = round(sum(v for _d, v in roe_annual) / len(roe_annual), 3) if roe_annual else None
        return {
            "source": meta.get("source", "sina"),
            "retrieved_at": meta.get("retrieved_at"),
            "report_date": report_date,
            "age_days": age,
            "fresh": age is not None and age <= budget_days,
            "roe_annual": roe_annual,
            "roe_3y_avg": roe_3y,
            "cfo_np_annual": cfo_np,
            "debt_ratio": latest_of(debt_col),
            "rev_growth": latest_of(rev_col),
            "np_growth": latest_of(np_col),
        }
    except (KeyError, IndexError, TypeError):
        return None


def get_industry(symbol: str, refresh: bool, cache_dir: Path, today: date) -> dict | None:
    """cninfo SW first-level industry (行业门类), cached with provenance."""
    if not refresh:
        df, meta = read_cache("industry", symbol, cache_dir)
        if df is not None and meta is not None:
            age = _days_since(str(meta.get("retrieved_at"))[:10], today)
            if age is not None and age <= INDUSTRY_FRESH_DAYS:
                industry = str(df.iloc[0]["industry"]) if len(df) else None
                return {"industry": industry or None, "source": meta.get("source"), "retrieved_at": meta.get("retrieved_at"), "degraded": False}
    import akshare as ak

    try:
        raw = ak.stock_industry_change_cninfo(symbol=symbol)
    except Exception:  # noqa: BLE001 — industry is optional depth data
        return None
    if raw is None or raw.empty:
        return None
    sw = raw[raw["分类标准"].astype(str).str.contains("申万", na=False)]
    pick = sw if len(sw) else raw
    pick = pick.sort_values("变更日期")
    gate = str(pick.iloc[-1]["行业门类"])
    df = pd_one_col("industry", gate)
    meta = {
        "source": "akshare.stock_industry_change_cninfo (cninfo SW 门类)",
        "symbol": symbol,
        "retrieved_at": _now(),
    }
    write_cache("industry", symbol, df, meta, cache_dir)
    return {"industry": gate, "source": meta["source"], "retrieved_at": meta["retrieved_at"], "degraded": False}


def pd_one_col(col: str, value: str):
    import pandas as pd

    return pd.DataFrame([{col: value}])


def get_valuation_3y(symbol: str, indicator: str, refresh: bool, cache_dir: Path, today: date) -> dict | None:
    """Baidu own-3Y valuation history (PE-TTM / PB), cached with provenance.
    Staleness is judged by the series' last date (market data budget)."""
    tag = "pe" if "市盈率" in indicator else "pb"
    key = f"{symbol}_{tag}"
    budget = VALUATION_REFETCH_DAYS
    if not refresh:
        df, meta = read_cache("valuation3y", key, cache_dir)
        if df is not None and meta is not None:
            last = str(meta.get("series_last_date", ""))[:10]
            age = _days_since(last, today) if last else None
            if age is not None and age <= budget:
                return {"df": df, "last_date": last, "source": meta.get("source"), "retrieved_at": meta.get("retrieved_at"), "stale": False}
    import akshare as ak

    try:
        raw = ak.stock_zh_valuation_baidu(symbol=symbol, indicator=indicator, period="近三年")
    except Exception as exc:  # noqa: BLE001 — degrade with provenance
        df, meta = read_cache("valuation3y", key, cache_dir)
        if df is not None and meta is not None:
            last = str(meta.get("series_last_date", ""))[:10]
            age = _days_since(last, today) if last else None
            return {
                "df": df,
                "last_date": last,
                "source": meta.get("source"),
                "retrieved_at": meta.get("retrieved_at"),
                "stale": age is None or age > int(budget * 2),
                "fetch_error": str(exc)[:200],
            }
        return None
    if raw is None or raw.empty:
        return None
    df = raw.copy()
    df["date"] = df["date"].astype(str)
    last = str(df["date"].max())[:10]
    meta = {
        "source": "akshare.stock_zh_valuation_baidu",
        "symbol": symbol,
        "indicator": indicator,
        "retrieved_at": _now(),
        "rows": len(df),
        "series_last_date": last,
    }
    write_cache("valuation3y", key, df, meta, cache_dir)
    age = _days_since(last, today)
    return {
        "df": df,
        "last_date": last,
        "source": meta["source"],
        "retrieved_at": meta["retrieved_at"],
        "stale": age is None or age > policy_valuation_stale_default(),
    }


def policy_valuation_stale_default() -> int:
    return 14


def own_history_percentile(series_df, current: float | None) -> float | None:
    """Percentile of the current value within its own 3Y history (fraction of
    the series strictly below current). Deterministic; None when unusable."""
    if series_df is None or current is None:
        return None
    values = []
    try:
        for raw in series_df["value"].tolist():
            try:
                f = float(raw)
            except (TypeError, ValueError):
                continue
            if not math.isnan(f):
                values.append(f)
    except (KeyError, TypeError):
        return None
    if not values:
        return None
    below = sum(1 for v in values if v < current)
    return below / len(values)


def preselect_deep(
    survivors: dict[str, dict], deep_max: int, min_turnover: float, turnover_full: float, legacy: list[str]
) -> tuple[list[str], str]:
    """Bounded deep-coverage selection, fully deterministic and documented.

    Proxy score (snapshot-stage fields only): value proxy (PE 15 / PB 10 /
    dividend 5 pool percentiles, negative PE missing) + liquidity (10, log
    band). The proxy is a coverage-bounding device, not the final rank.
    """
    pe = {s: (c["quote"].get("pe_ttm") if (c["quote"].get("pe_ttm") or 0) > 0 else None) for s, c in survivors.items()}
    pb = {s: (c["quote"].get("pb") if (c["quote"].get("pb") or 0) > 0 else None) for s, c in survivors.items()}
    dy = {s: c["quote"].get("dividend_yield_pct") for s, c in survivors.items()}
    pe_pct = percentile_map(pe)
    pb_pct = percentile_map(pb)
    proxy: dict[str, float] = {}
    for s, c in survivors.items():
        value = 0.0
        if pe_pct.get(s) is not None:
            value += 15 * (1 - pe_pct[s])
        if pb_pct.get(s) is not None:
            value += 10 * (1 - pb_pct[s])
        dy_frac = band_score(dy.get(s) if (dy.get(s) or 0) > 0 else None, 0.0, 4.0)
        if dy_frac is not None:
            value += 5 * dy_frac
        liq = log_band(c["quote"].get("turnover_cny"), min_turnover, turnover_full)
        score = value + 10 * (liq or 0.0)
        proxy[s] = score
    ranked = sorted(proxy, key=lambda s: (-proxy[s], s))
    top = ranked[:deep_max]
    for s in legacy:
        if s in survivors and s not in top:
            top.append(s)
    basis = (
        f"top {deep_max} of {len(ranked)} snapshot survivors by deterministic "
        "pre-score (PE/PB/DY pool percentiles 30 + turnover log-band 10); "
        "legacy watchlist always deep-covered"
    )
    return top, basis


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def build_snapshot(
    policy: dict,
    active_cfg: dict,
    membership: dict,
    quotes: dict[str, dict],
    deep_symbols: list[str],
    deep_coverage_basis: str,
    financials_by: dict[str, dict | None],
    industry_by: dict[str, dict | None],
    history_rows_by: dict[str, int],
    valuation_by: dict[str, dict | None],
    legacy_symbols: list[str],
    today: date,
) -> dict:
    """Pure assembly from fetched inputs: eligibility, percentiles, scores,
    red flags, ranking, sector cap, legacy diagnosis, snapshot dict."""
    names = membership["names"]

    def mk_ctx(symbol: str) -> dict:
        quote = quotes.get(symbol) or {"price": None}
        industry = (industry_by.get(symbol) or {}).get("industry")
        ctx = {
            "symbol": symbol,
            "name": quote.get("name") or names.get(symbol, ""),
            "industry": industry,
            "sector_model": sector_model_for(industry, policy),
            "quote": quote,
            "financials": financials_by.get(symbol),
            "hist_rows": history_rows_by.get(symbol),
            "own_pe_pct": None,
            "valuation_stale": False,
            "source_degraded": False,
        }
        val = valuation_by.get(symbol)
        if val is not None:
            pe = quote.get("pe_ttm")
            ctx["own_pe_pct"] = own_history_percentile(val.get("df"), pe if (pe or 0) > 0 else None)
            ctx["valuation_stale"] = bool(val.get("stale"))
            if val.get("fetch_error") or val.get("source_degraded"):
                ctx["source_degraded"] = True
        fin = financials_by.get(symbol)
        if fin is not None and (fin.get("source_degraded") or fin.get("fetch_error")):
            ctx["source_degraded"] = True
        if industry_by.get(symbol) is not None and industry_by[symbol].get("degraded"):
            ctx["source_degraded"] = True
        return ctx

    pool_survivors: dict[str, dict] = {}
    legacy_syms = [s for s in legacy_symbols if s in quotes]
    for symbol, quote in quotes.items():
        if symbol not in deep_symbols and symbol not in legacy_syms:
            continue
        pool_survivors[symbol] = mk_ctx(symbol)
    # timing inputs for every deep/legacy symbol with cached history; the
    # cache is authoritative for row counts so a transient in-run fetch
    # failure cannot fake INSUFFICIENT_HISTORY while valid local data exists
    for symbol, ctx in pool_survivors.items():
        hist, _meta = read_cache("daily", f"{symbol}_qfq", CACHE_DIR)
        if hist is not None:
            ctx["hist_rows"] = len(hist)
            quote = ctx["quote"]
            if quote.get("price") and quote["price"] > 0:
                ctx["timing"] = timing_from_quote_hist(quote, hist)

    # snapshot-stage exclusions define who even reaches scoring
    for ctx in pool_survivors.values():
        eligible, exclusions = evaluate_eligibility(ctx, policy)
        ctx["eligible"] = eligible
        ctx["exclusions"] = exclusions

    scored_pool = {s: c for s, c in pool_survivors.items() if c["eligible"]}

    # percentile maps over the scorable pool + per-industry groups
    def gather(getter):
        return {s: getter(c) for s, c in scored_pool.items()}

    pe_vals = gather(lambda c: c["quote"].get("pe_ttm") if (c["quote"].get("pe_ttm") or 0) > 0 else None)
    pb_vals = gather(lambda c: c["quote"].get("pb") if (c["quote"].get("pb") or 0) > 0 else None)
    roe_vals = gather(lambda c: (c["financials"] or {}).get("roe_3y_avg"))
    debt_vals = gather(lambda c: (c["financials"] or {}).get("debt_ratio"))
    industry_of = {s: c["industry"] for s, c in scored_pool.items()}
    min_peers = int(policy["ranking"]["min_industry_peers"])
    pe_pct, pe_basis = group_percentiles(pe_vals, industry_of, min_peers)
    pb_pct, pb_basis = group_percentiles(pb_vals, industry_of, min_peers)
    roe_groups = {s: ("FIN" if c["sector_model"] == "financial" else (c["industry"] or "POOL")) for s, c in scored_pool.items()}
    roe_pct, roe_basis = group_percentiles(roe_vals, roe_groups, min_peers)
    debt_pct, _debt_basis = group_percentiles(debt_vals, industry_of, min_peers)

    rows: list[dict] = []
    for symbol in sorted(scored_pool):
        ctx = scored_pool[symbol]
        pcts = {"pe": pe_pct.get(symbol), "pb": pb_pct.get(symbol), "roe": roe_pct.get(symbol), "debt": debt_pct.get(symbol)}
        pbasis = {"pe": pe_basis.get(symbol, "missing"), "pb": pb_basis.get(symbol, "missing"), "roe": roe_basis.get(symbol, "missing")}
        v_frac, v_missing, v_reasons, _v_names = score_value(ctx, pcts, pbasis, policy)
        q_frac, q_missing, q_reasons, q_flags, _q_names = score_quality(ctx, pcts, pbasis, policy)
        t_frac, t_missing, t_reasons = score_tradeability(ctx, policy)
        strength = None
        prev_close = ctx["quote"].get("prev_close")
        if ctx["quote"].get("price") is not None and prev_close:
            strength = ctx["quote"]["price"] - prev_close
        tim_frac, tim_missing, tim_state, tim_detail = score_timing(ctx.get("timing"), strength, prev_close, active_cfg)
        red_flags = sorted(set(build_red_flags(ctx, policy) + q_flags))
        composite = round(
            v_frac * policy["score_weights"]["value"]
            + q_frac * policy["score_weights"]["quality"]
            + t_frac * policy["score_weights"]["tradeability"]
            + tim_frac * policy["score_weights"]["timing"],
            1,
        )
        reasons = sorted(v_reasons + q_reasons + t_reasons, reverse=True)[:2]
        fin = ctx.get("financials") or {}
        val = valuation_by.get(symbol)
        rows.append(
            {
                "symbol": symbol,
                "name": ctx["name"],
                "industry": ctx["industry"],
                "sector_model": ctx["sector_model"],
                "tier": compute_tier(composite, red_flags, policy),
                "composite_score": composite,
                "value_score": round(v_frac * policy["score_weights"]["value"], 1),
                "quality_score": round(q_frac * policy["score_weights"]["quality"], 1),
                "tradeability_score": round(t_frac * policy["score_weights"]["tradeability"], 1),
                "timing_score": round(tim_frac * policy["score_weights"]["timing"], 1),
                "timing_state": tim_state,
                "timing": tim_detail,
                "metrics": {
                    "pe_ttm": ctx["quote"].get("pe_ttm"),
                    "pb": ctx["quote"].get("pb"),
                    "dividend_yield_pct": ctx["quote"].get("dividend_yield_pct"),
                    "roe_3y_pct": fin.get("roe_3y_avg"),
                    "cfo_to_net_profit": (fin.get("cfo_np_annual") or [[None, None]])[-1][1] if fin.get("cfo_np_annual") else None,
                    "debt_ratio_pct": fin.get("debt_ratio"),
                    "np_growth_pct": fin.get("np_growth"),
                    "rev_growth_pct": fin.get("rev_growth"),
                    "turnover_cny": ctx["quote"].get("turnover_cny"),
                    "valuation_percentile_3y": ctx.get("own_pe_pct"),
                    "price": ctx["quote"].get("price"),
                },
                "percentile_basis": {"pe": pbasis.get("pe"), "pb": pbasis.get("pb"), "roe": pbasis.get("roe")},
                "missing_fields": sorted(set(v_missing + q_missing + t_missing + tim_missing)),
                "reasons": reasons,
                "red_flags": red_flags,
                "data_freshness": {
                    "financial_date": fin.get("report_date"),
                    "valuation_at": (val or {}).get("last_date"),
                    "quote_time": f"{ctx['quote'].get('date', '')} {ctx['quote'].get('time', '')}".strip(),
                },
                "source_degraded": bool(ctx.get("source_degraded")),
            }
        )

    ranked = sorted(rows, key=lambda r: (-r["composite_score"], r["symbol"]))
    pool, concentration = select_pool(ranked, policy)
    pool_symbols = [r["symbol"] for r in pool]

    # legacy diagnosis: same scoring, judged against the actual pool cut
    legacy_rows = []
    for symbol in legacy_syms:
        ctx = pool_survivors.get(symbol)
        if ctx is None:
            legacy_rows.append({"symbol": symbol, "name": names.get(symbol, ""), "in_snapshot": False, "legacy_status": "LEGACY_ONLY"})
            continue
        match = next((r for r in ranked if r["symbol"] == symbol), None)
        if match is None:
            legacy_rows.append(
                {
                    "symbol": symbol,
                    "name": ctx["name"],
                    "industry": ctx["industry"],
                    "price": ctx["quote"].get("price"),
                    "eligible": False,
                    "exclusions": ctx.get("exclusions", []),
                    "red_flags": build_red_flags(ctx, policy),
                    "legacy_status": "LEGACY_ONLY",
                }
            )
            continue
        qualifies = symbol in pool_symbols
        legacy_rows.append({**match, "eligible": True, "qualifies_for_pool": qualifies, "legacy_status": "POOL_QUALIFIED" if qualifies else "LEGACY_ONLY"})

    covered = sum(1 for s in deep_symbols if (financials_by.get(s) or {}).get("fresh"))
    frac, status = coverage_status(covered, len(deep_symbols), policy)

    return {
        "as_of": _now(),
        "status": status,
        "base_universe": policy["universe"]["base"],
        "base_count": len(names),
        "quoted_count": len(quotes),
        "deep_count": len(deep_symbols),
        "eligible_count": len(scored_pool),
        "candidate_count": len(pool),
        "pool_target": {
            "min": policy["universe"]["pool_target_min"],
            "max": policy["universe"]["pool_target_max"],
            "met": policy["universe"]["pool_target_min"] <= len(pool) <= policy["universe"]["pool_target_max"],
        },
        "coverage": round(frac, 4),
        "coverage_definition": "deep-set symbols with fresh essential financial data / deep-set size",
        "concentration": concentration,
        "deep_coverage_basis": deep_coverage_basis,
        "policy_ref": "benchmarks/quant/gen1/candidates_policy.toml",
        "rank_is_not_a_buy_recommendation": "candidate rank is a research-attention order only; actions require the deterministic live trigger; profitability remains unproven",
        "sources": {
            "membership": membership["sources"],
            "quotes": {"source": "qt.gtimg.cn batch quote (Tencent)", "retrieved_at": _now(), "count": len(quotes), "fallback_used": False},
            "financial": _source_summary(financials_by, "akshare.stock_financial_analysis_indicator (sina)"),
            "industry": _source_summary(industry_by, "akshare.stock_industry_change_cninfo"),
            "valuation_history": _source_summary(valuation_by, "akshare.stock_zh_valuation_baidu"),
        },
        "source_degradations": membership["degradations"]
        + [
            {"source": f"financial:{s}", "error": (financials_by.get(s) or {}).get("fetch_error", "missing")}
            for s in deep_symbols
            if (financials_by.get(s) or {}).get("fetch_error")
        ],
        "candidates": pool,
        "legacy_diagnosis": legacy_rows,
    }


def _source_summary(by_symbol: dict, default_source: str) -> dict:
    got = [v for v in by_symbol.values() if v is not None]
    if not got:
        return {"source": default_source, "covered": 0, "fallback_used": False, "coverage_note": "unavailable — affected scores renormalized and flagged"}
    degraded = sum(1 for v in got if v.get("degraded") or v.get("source_degraded") or v.get("fetch_error"))
    return {
        "source": got[0].get("source", default_source),
        "covered": len(got),
        "degraded_count": degraded,
        "retrieved_at": got[0].get("retrieved_at"),
        "fallback_used": degraded > 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=POLICY_PATH)
    parser.add_argument("--refresh", action="store_true", help="ignore caches and refetch")
    parser.add_argument("--deep-max", type=int, default=None, help="deep-coverage bound override")
    parser.add_argument("--workers", type=int, default=6, help="bounded parallel fetch workers for the deep pass")
    args = parser.parse_args()

    policy = load_config(args.policy)
    active_cfg = load_config(ACTIVE_STRATEGY_PATH)
    today = datetime.now(TZ_SHANGHAI).date()
    started = time.perf_counter()
    # some upstream fetchers issue requests without an explicit timeout; a
    # 30s socket cap turns a hung connection into a bounded, degradable error
    socket.setdefaulttimeout(30)

    if args.deep_max is not None:
        policy["coverage"]["deep_max_symbols"] = int(args.deep_max)

    membership = resolve_membership(args.refresh, CACHE_DIR)
    if not membership["names"]:
        print("FATAL: discovery base empty (both index sources failed without cache)", file=sys.stderr)
        return 3
    legacy_symbols = [str(s).strip() for s in load_config(LEGACY_WATCHLIST_PATH)["symbols"]]

    base_symbols = sorted(membership["names"])
    quote_symbols = sorted(set(base_symbols) | set(legacy_symbols))
    print(f"[1/5] membership: {len(base_symbols)} base + {len(legacy_symbols)} legacy; fetching quotes…", flush=True)
    quotes = fetch_batch_quotes(quote_symbols)
    print(f"      quotes ok: {len(quotes)}/{len(quote_symbols)}", flush=True)

    # cheap snapshot-stage survivors (hard exclusions that need no deep data)
    survivors: dict[str, dict] = {}
    for symbol in quote_symbols:
        quote = quotes.get(symbol)
        if not quote or (quote.get("price") or 0) <= 0:
            continue
        name = quote.get("name") or ""
        if any(pat in name for pat in policy["eligibility"]["exclude_name_patterns"]):
            continue
        if (quote.get("turnover_cny") or 0) < policy["eligibility"]["min_turnover_cny"]:
            continue
        survivors[symbol] = {"symbol": symbol, "name": name, "quote": quote}
    deep_symbols, deep_basis = preselect_deep(
        survivors,
        int(policy["coverage"]["deep_max_symbols"]),
        policy["eligibility"]["min_turnover_cny"],
        policy["tradeability_components"]["turnover_full_cny"],
        legacy_symbols,
    )
    print(f"[2/5] snapshot survivors: {len(survivors)}; deep set: {len(deep_symbols)}", flush=True)

    financials_by: dict[str, dict | None] = {}
    industry_by: dict[str, dict | None] = {}
    history_rows_by: dict[str, int] = {}
    valuation_by: dict[str, dict | None] = {}

    def _deep_work(symbol: str) -> tuple[dict | None, dict | None, int]:
        try:
            fin = get_financials(symbol, policy, args.refresh, CACHE_DIR, today)
        except Exception:  # noqa: BLE001 — bounded per-symbol degradation
            fin = None
        ind = get_industry(symbol, args.refresh, CACHE_DIR, today)
        try:
            hist, _meta = fetch_history(symbol, "qfq", refresh=args.refresh, cache_dir=CACHE_DIR)
            rows = len(hist)
        except Exception:  # noqa: BLE001 — history optional for scoring, required for eligibility
            rows = 0
        return fin, ind, rows

    # per-symbol fetches are independent; a small bounded pool keeps a first
    # refresh inside an off-hours window (results are dict-keyed, so
    # downstream ordering stays deterministic)
    workers = max(1, int(args.workers))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, (symbol, (fin, ind, rows)) in enumerate(zip(deep_symbols, pool.map(_deep_work, deep_symbols)), 1):
            financials_by[symbol] = fin
            industry_by[symbol] = ind
            history_rows_by[symbol] = rows
            if i % 20 == 0 or i == len(deep_symbols):
                print(f"      deep {i}/{len(deep_symbols)} ({time.perf_counter() - started:.0f}s)", flush=True)

    # second pass: eligibility needs fresh financials + history; then valuation.
    # Like build_snapshot, cached history counts override a transient in-run
    # fetch failure so the valuation gate cannot silently shrink coverage.
    for symbol in deep_symbols:
        quote = quotes.get(symbol)
        if not quote or (quote.get("price") or 0) <= 0:
            continue
        name = quote.get("name") or ""
        if any(pat in name for pat in policy["eligibility"]["exclude_name_patterns"]):
            continue
        hist_rows = history_rows_by.get(symbol, 0)
        if hist_rows < int(policy["eligibility"]["min_history_rows"]):
            hist, _meta = read_cache("daily", f"{symbol}_qfq", CACHE_DIR)
            if hist is not None:
                hist_rows = len(hist)
        ctx = {
            "symbol": symbol,
            "name": name,
            "quote": quote,
            "financials": financials_by.get(symbol),
            "hist_rows": hist_rows,
            "timing": (1.0, 1.0),  # history-sufficiency already encoded in hist_rows
        }
        eligible, _reasons = evaluate_eligibility(ctx, policy)
        if eligible:
            val = get_valuation_3y(symbol, "市盈率(TTM)", args.refresh, CACHE_DIR, today)
            valuation_by[symbol] = val
    print(f"[3/5] deep data done: financials {sum(1 for v in financials_by.values() if v)}/{len(deep_symbols)}, valuation {len(valuation_by)}", flush=True)

    print("[4/5] scoring + ranking…", flush=True)
    snapshot = build_snapshot(
        policy,
        active_cfg,
        membership,
        quotes,
        deep_symbols,
        deep_basis,
        financials_by,
        industry_by,
        history_rows_by,
        valuation_by,
        legacy_symbols,
        today,
    )
    snapshot["sources"]["quotes"]["retrieved_at"] = snapshot["as_of"]

    BUSINESS_ART_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    ACTIVE_SYMBOLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if snapshot["candidate_count"] > 0:
        ACTIVE_SYMBOLS_PATH.write_text(
            json.dumps(
                {
                    "as_of": snapshot["as_of"],
                    "source": "candidate_snapshot",
                    "symbols": [c["symbol"] for c in snapshot["candidates"]],
                    "count": snapshot["candidate_count"],
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    elif ACTIVE_SYMBOLS_PATH.exists():
        ACTIVE_SYMBOLS_PATH.unlink()  # fail closed: stale handoff must not linger

    print(
        f"[5/5] snapshot: status={snapshot['status']} base={snapshot['base_count']} "
        f"deep={snapshot['deep_count']} eligible={snapshot['eligible_count']} "
        f"candidates={snapshot['candidate_count']} coverage={snapshot['coverage']} "
        f"concentration={snapshot['concentration']} elapsed={time.perf_counter() - started:.0f}s",
        flush=True,
    )
    print(f"OK -> {SNAPSHOT_PATH}", flush=True)
    print(f"OK -> {ACTIVE_SYMBOLS_PATH} ({snapshot['candidate_count']} symbols)" if snapshot["candidate_count"] else "EMPTY CANDIDATE POOL — active handoff removed (fail closed)", flush=True)
    return 0 if snapshot["candidate_count"] > 0 else 2


if __name__ == "__main__":
    sys.exit(main())
