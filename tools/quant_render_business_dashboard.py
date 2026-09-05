#!/usr/bin/env python3
"""render_business_dashboard.py — ZUAEF quant business dashboard (read-only).

Renders docs/quant/business.html from existing artifacts: the M1 trading-loop
truth (workspace/artifacts/quant/trading/ — soak.jsonl / alerts.jsonl /
forward.json / state.json), the candidate snapshot
(tools/quant_build_candidates.py), last live-scan snapshot, Decision Briefs,
the observation log (history only), the frozen active strategy and
baseline/S1/S2/S3 evidence. Answers market questions — today's decision, top
value/quality alternatives, live triggers, why each candidate ranks, red
flags, data freshness, real-run evidence trend, and why the strategy is
still unproven. Engineering proof chain (U0–P5.5) stays on /engineering.

Current M1 trading truth comes only from workspace/artifacts/quant/trading/.
The old workspace/quant/outcomes.jsonl is no longer read.

Stdlib only: runs with plain python3, no quant dependency group needed.

    python3 tools/quant_render_business_dashboard.py [--out docs/quant/business.html]

Read-only: touches no artifact inputs. Candidate rank is NOT a buy
recommendation; profitability remains unproven; real actions still require
the deterministic live trigger.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from datetime import time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ_SHANGHAI = ZoneInfo("Asia/Shanghai")
REPO_ROOT = Path(__file__).resolve().parent.parent
GEN1 = REPO_ROOT / "benchmarks" / "quant" / "gen1"
ART = REPO_ROOT / "workspace" / "artifacts" / "quant"
BUSINESS_ART = ART / "business"
SNAPSHOT_PATH = BUSINESS_ART / "candidate_snapshot.json"
LAST_SCAN_PATH = BUSINESS_ART / "last_scan.json"
BRIEFS_DIR = ART / "briefs"
OBS_LOG_PATH = GEN1 / "OBSERVATION_LOG.md"
STATUS_PATH = GEN1 / "STATUS.md"
ACTIVE_PATH = GEN1 / "active.toml"
LEGACY_PATH = GEN1 / "legacy_watchlist.toml"
SEMANTIC_DIR = ART / "semantic"
TRADING_DIR = ART / "trading"
TRADING_DIAGNOSTIC_DIR = ART / "trading-diagnostic"
DAILY_CACHE_DIR = REPO_ROOT / "data" / "quant-cache" / "daily"
V31_ART = ART / "v31"
ACTIVE_SYMBOLS_PATH = REPO_ROOT / "data" / "quant-cache" / "candidates" / "active_symbols.json"
DEFAULT_OUT = REPO_ROOT / "docs" / "quant" / "business.html"

STRATEGY_WARNING = "历史 S3 证据薄弱;盈利能力仍未证明 (NOT YET)。"
NOT_A_BUY_NOTE = (
    "候选排名只是研究关注度的排序,不是买入建议;实际动作仍需确定性实时触发"
    "加人工决策。盈利能力仍未证明。"
)


# --------------------------------------------------------------------------
# tolerant readers (missing input -> honest empty state, never fabricated)
# --------------------------------------------------------------------------


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_json(p: Path):
    if p is None:
        return None
    try:
        return json.loads(read_text(p))
    except (ValueError, TypeError):
        return None


def read_jsonl(p: Path) -> list[dict]:
    rows = []
    for line in read_text(p).splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def load_legacy_symbols(path: Path) -> list[str]:
    text = read_text(path)
    m = re.search(r"symbols\s*=\s*\[([^\]]*)\]", text, re.DOTALL)
    if not m:
        return []
    return re.findall(r'"([^"]+)"', m.group(1))


def parse_obs_log(path: Path) -> list[dict]:
    rows = []
    for line in read_text(path).splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if (
            len(cells) < 5
            or cells[0] == "日期"
            or not re.match(r"\d{4}-\d{2}-\d{2}", cells[0])
        ):
            continue
        rows.append(
            {
                "date": cells[0],
                "time": cells[1] if len(cells) > 1 else "",
                "scanned": cells[2] if len(cells) > 2 else "",
                "triggers": cells[3] if len(cells) > 3 else "",
                "action": cells[4] if len(cells) > 4 else "",
                "note": cells[7] if len(cells) > 7 else "",
            }
        )
    return rows


def parse_proof_rows(path: Path) -> list[dict]:
    rows = []
    for line in read_text(path).splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [
            c.strip().replace("**", "").strip()
            for c in line.strip().strip("|").split("|")
        ]
        if (
            len(cells) >= 3
            and cells[0] not in ("", "Proof")
            and not set(cells[0]) <= {"-"}
        ):
            rows.append({"name": cells[0], "state": cells[1]})
    return rows


def strategy_evidence_state(proofs: list[dict]) -> str:
    for p in proofs:
        if "Profitability" in p["name"]:
            return "UNPROVEN" if "NOT YET" in p["state"].upper() else p["state"].upper()
    return "UNPROVEN"


def harvest_strategy_results() -> list[dict]:
    """Baseline + S1/S2/S3 replay results from evidence.json artifacts."""
    rows: list[dict] = []

    def row_from(ev: dict, label: str, verdict: str) -> dict:
        rp = ev.get("independent_replay", {}) or {}
        return {
            "label": label,
            "name": ev.get("strategy", {}).get("name", ""),
            "annualized_pct": rp.get("annualized_return_pct"),
            "trades": rp.get("trade_count"),
            "max_drawdown_pct": rp.get("max_drawdown_pct"),
            "verdict": verdict,
        }

    base_ev = read_json(ART / "gen1" / "evidence.json")
    if base_ev:
        rows.append(row_from(base_ev, "基线", "基线 (持有 5 天)"))
    children = ART / "children"
    verdicts = {
        "s1_softer_pullback": "改善,被后续轮次继承",
        "s2_tighter_volume": "被证据否决",
        "s3_longer_hold": "已冻结为 DEMO_ACTIVE_STRATEGY",
    }
    found: dict[str, dict] = {}
    if children.is_dir():
        for d in sorted(children.iterdir()):
            if not d.is_dir():
                continue
            ev = read_json(d / "evidence.json")
            if not ev:
                continue
            name = ev.get("strategy", {}).get("name", d.name)
            if name in found:
                continue
            found[name] = row_from(ev, name, verdicts.get(name, ""))
    for name in ("s1_softer_pullback", "s2_tighter_volume", "s3_longer_hold"):
        if name in found:
            rows.append(found[name])
    return rows


def best_strategy_row(rows: list[dict]) -> dict | None:
    frozen = [r for r in rows if r["name"] == "s3_longer_hold"]
    if frozen:
        return frozen[0]
    return max(rows, key=lambda r: r.get("annualized_pct") or 0) if rows else None


def load_briefs(briefs_dir: Path) -> list[dict]:
    out = []
    if briefs_dir.is_dir():
        for p in sorted(briefs_dir.glob("brief-*.json")):
            b = read_json(p)
            if b:
                out.append(b)
    out.sort(key=lambda b: str(b.get("recorded_at", "")))
    return out


def shanghai_day(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.astimezone(TZ_SHANGHAI).strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def today_decision(briefs: list[dict]) -> dict:
    today = datetime.now(TZ_SHANGHAI).strftime("%Y-%m-%d")
    if not briefs:
        return {"state": "NOT_RUN_TODAY", "action": None, "brief": None}
    latest = briefs[-1]
    ran_today = shanghai_day(str(latest.get("recorded_at", ""))) == today
    return {
        "state": str(latest.get("action", "UNKNOWN")) if ran_today else "NOT_RUN_TODAY",
        "action": latest.get("action"),
        "last_run_day": shanghai_day(str(latest.get("recorded_at", ""))),
        "brief": latest,
    }


# --------------------------------------------------------------------------
# M1 real-run evidence (workspace/artifacts/quant/trading/ is the only
# current trading truth; missing data stays missing, never coerced to 0)
# --------------------------------------------------------------------------


# soak statuses that prove an in-session pass actually scanned the universe
SOAK_IN_SESSION_STATUSES = {"NO_TRADE", "ALERTS", "SCANNED"}

DIAGNOSTIC_EVENT_KINDS = {"NEW_NEAR": "NEAR", "NEW_READY": "READY"}


def _d1_from_daily(daily_dir: Path, symbol: str, ref_price: float, day: str) -> dict:
    """Diagnostic D+1 from the first cached daily close strictly after `day`.

    Real cached bars only. No future bar -> stays pending (no key), never a
    fabricated 0.
    """
    lines = read_text(Path(daily_dir) / f"{symbol}_qfq.csv").splitlines()
    for line in lines[1:]:  # skip header; ISO dates sort lexicographically
        cells = line.split(",")
        # columns: date,symbol,open,high,low,close,...
        if len(cells) < 6 or cells[0] <= day:
            continue
        try:
            close = float(cells[5])
        except ValueError:
            continue
        if ref_price <= 0:
            return {}
        return {"d1_day": cells[0], "d1": round(close / ref_price - 1, 6)}
    return {}


def load_diagnostic_evidence(
    diagnostic_dir: Path = TRADING_DIAGNOSTIC_DIR, daily_dir: Path = DAILY_CACHE_DIR
) -> list[dict]:
    """9/3-style isolated diagnostic NEAR/READY records + their D+1 outcome.

    These are `diagnostic forward evidence` from a `--state-dir` isolated run:
    never formal forward observations, never strategy return/win-rate.
    """
    rows = []
    for a in read_jsonl(Path(diagnostic_dir) / "alerts.jsonl"):
        kind = DIAGNOSTIC_EVENT_KINDS.get(str(a.get("type", "")))
        if kind is None:
            continue
        symbol, ref, day = a.get("symbol"), a.get("price"), str(a.get("day") or "")
        conditions = a.get("conditions") or {}
        row = {
            "kind": "diagnostic",
            "symbol": symbol,
            "day": day,
            "state": kind,
            "ref_price": ref,
            "pullback_5d": conditions.get("pullback_5d"),
            "volume_ratio_20d": conditions.get("volume_ratio_20d"),
            "source": "trading-diagnostic/alerts.jsonl",
        }
        if isinstance(ref, (int, float)) and day:
            row.update(_d1_from_daily(daily_dir, str(symbol), float(ref), day))
        rows.append(row)
    return rows


def load_real_trend(
    trading_dir: Path = TRADING_DIR,
    *,
    diagnostic_dir: Path = TRADING_DIAGNOSTIC_DIR,
    daily_dir: Path = DAILY_CACHE_DIR,
    active_symbols_path: Path = ACTIVE_SYMBOLS_PATH,
    semantic_dir: Path = SEMANTIC_DIR,
    v31_dir: Path = V31_ART,
) -> dict:
    """Real trading-loop records -> real_trend for the business page.

    Points come verbatim from soak.jsonl (MARKET_CLOSED / SYSTEM_UNAVAILABLE
    stay what they are; symbols=0 while closed is a real recorded zero, and a
    genuinely missing field stays missing). No interpolation, no backfill,
    duplicate real records counted once.
    """
    soak = read_jsonl(Path(trading_dir) / "soak.jsonl")
    alerts_by_ts: dict[str, int] = {}
    for a in read_jsonl(Path(trading_dir) / "alerts.jsonl"):
        ts = str(a.get("ts"))
        alerts_by_ts[ts] = alerts_by_ts.get(ts, 0) + 1
    universe = read_json(active_symbols_path) or {}
    universe_size = len(universe.get("symbols") or []) or None

    points: list[dict] = []
    seen: set = set()
    for row in soak:
        ts = str(row.get("ts") or "")
        key = (ts, str(row.get("status")), row.get("events"), row.get("symbols"))
        if not ts or key in seen:  # same real record never counts twice
            continue
        seen.add(key)
        points.append(
            {
                "ts": ts,
                "status": row.get("status"),
                "symbols_scanned": row.get("symbols"),
                "universe_size": universe_size,
                # alerts.jsonl refines the per-cycle count when it has the ts
                "events": alerts_by_ts.get(ts, row.get("events")),
                "source": "trading/soak.jsonl",
            }
        )
    points.sort(key=lambda p: p["ts"])

    forward = read_json(Path(trading_dir) / "forward.json") or {}
    observations = forward.get("observations") or []

    replay = load_latest_v31_replay(v31_dir)
    settled = sum(1 for o in observations if o.get("d8") is not None)

    proof = load_latest_semantic_proof(semantic_dir)
    in_session = [
        p
        for p in points
        if p["status"] in SOAK_IN_SESSION_STATUSES and (p["symbols_scanned"] or 0) > 0
    ]
    if proof:
        market_ok = proof.get("status") == "PASS" and str(
            (proof.get("same_date_cross_check") or {}).get("status")
        ) == "PASS"
        market_detail = f"最新 semantic proof {proof.get('as_of', '')} · {proof.get('reason', '')}"
    else:
        market_ok = False
        market_detail = "尚无 semantic proof"
    sample = proof.get("sample_size") or 0 if proof else 0
    single_ok = sample > 0
    single_detail = (
        f"单次全宇宙报价核验 {sample}/{sample} ({proof.get('as_of', '')}) — 单次验证, 不是连续监控"
        if single_ok
        else "尚无单次全宇宙有效数据通过记录"
    )
    cont_detail = (
        f"soak 真实记录 {len(points)} 条, 其中盘中有效扫描 {len(in_session)} 条"
        + ("" if in_session else " — 连续实时监控未证明")
    )
    m1 = {
        "market_data_valid": {"ok": market_ok, "detail": market_detail},
        "single_scan_valid": {"ok": single_ok, "detail": single_detail},
        "continuous_monitoring": {"ok": bool(in_session), "detail": cont_detail},
        "formal_forward_count": len(observations),
        "formal_forward_settled": settled,
    }
    oks = [market_ok, single_ok, bool(in_session)]
    m1["verdict"] = (
        "PASS" if all(oks) and len(observations) > 0
        else "PARTIAL" if any(oks) or len(observations)
        else "NO_REAL_EVIDENCE"
    )
    return {
        "points": points,
        "record_count": len(points),
        "universe_size": universe_size,
        "forward": {"present": bool(forward), "count": len(observations), "settled": settled},
        "m1_evidence": m1,
        "diagnostic_rows": load_diagnostic_evidence(diagnostic_dir, daily_dir),
        "v31_replay": replay,
    }


def load_latest_v31_replay(v31_dir: Path = V31_ART) -> dict | None:
    """Latest v3.1 replay report; never relabel it as live-forward evidence."""
    reports = sorted((Path(v31_dir) / "replay").glob("*/report.json"))
    if not reports:
        return None
    report = read_json(reports[-1])
    if not report or report.get("namespace") != "replay":
        return None
    payload = report.get("payload") or {}
    days = payload.get("days") or []
    reasons = sorted({r for day in days for r in day.get("blocked_reasons") or []})
    return {
        "run_id": reports[-1].parent.name,
        "as_of": report.get("as_of"),
        "status": payload.get("status"),
        "day_count": len(days),
        "blocked_day_count": sum(1 for day in days if day.get("status") == "blocked"),
        "observation_count": sum(day.get("observation_count") or 0 for day in days),
        "live_forward_increment": payload.get("live_forward_increment"),
        "intraday_equivalence": payload.get("intraday_equivalence"),
        "reasons": reasons,
    }


# --------------------------------------------------------------------------
# data assembly
# --------------------------------------------------------------------------


def join_trigger_rows(
    scan: dict | None, snapshot: dict | None, briefs: list[dict]
) -> list[dict]:
    triggers = (scan or {}).get("triggers") or []
    by_symbol = {c.get("symbol"): c for c in ((snapshot or {}).get("candidates") or [])}
    latest_brief_by_symbol: dict[str, dict] = {}
    for b in briefs:
        sym = str(b.get("symbol", ""))
        if sym and sym != "NONE":
            latest_brief_by_symbol[sym] = b
    rows = []
    for t in triggers:
        cand = by_symbol.get(t.get("symbol")) or {}
        brief = latest_brief_by_symbol.get(t.get("symbol"))
        rows.append(
            {
                "symbol": t.get("symbol"),
                "name": t.get("name") or cand.get("name", ""),
                "industry": cand.get("industry") or "—",
                "price": t.get("price"),
                "value_score": cand.get("value_score"),
                "quality_score": cand.get("quality_score"),
                "composite_score": cand.get("composite_score"),
                "pullback_5d": t.get("pullback_5d"),
                "volume_ratio_20d": t.get("volume_ratio_20d"),
                "trigger_time": t.get("quote_time", ""),
                "agent_action": brief.get("action") if brief else None,
                "red_flags": cand.get("red_flags") or [],
            }
        )
    return rows


def board_rows(snapshot: dict | None, limit: int = 30) -> list[dict]:
    candidates = (snapshot or {}).get("candidates") or []
    rows = []
    for i, c in enumerate(candidates[:limit], 1):
        m = c.get("metrics") or {}
        rows.append(
            {
                "rank": i,
                "symbol": c.get("symbol"),
                "name": c.get("name", ""),
                "industry": c.get("industry") or "未知",
                "sector_model": c.get("sector_model", ""),
                "tier": c.get("tier", ""),
                "composite_score": c.get("composite_score"),
                "value_score": c.get("value_score"),
                "quality_score": c.get("quality_score"),
                "tradeability_score": c.get("tradeability_score"),
                "pe_ttm": m.get("pe_ttm"),
                "pb": m.get("pb"),
                "dividend_yield_pct": m.get("dividend_yield_pct"),
                "roe_3y_pct": m.get("roe_3y_pct"),
                "valuation_percentile_3y": m.get("valuation_percentile_3y"),
                "timing_state": c.get("timing_state", "WAIT"),
                "reasons": c.get("reasons") or [],
                "red_flags": c.get("red_flags") or [],
            }
        )
    return rows


def legacy_rows(snapshot: dict | None, legacy_symbols: list[str]) -> list[dict]:
    diagnosed = {
        r.get("symbol"): r for r in ((snapshot or {}).get("legacy_diagnosis") or [])
    }
    rows = []
    for symbol in legacy_symbols:
        r = dict(diagnosed.get(symbol) or {"symbol": symbol, "in_snapshot": False})
        metrics = r.get("metrics") or {}
        r.setdefault("price", metrics.get("price"))
        r.setdefault("quote_time", (r.get("data_freshness") or {}).get("quote_time"))
        r.setdefault(
            "legacy_status",
            "LEGACY_ONLY" if not r.get("qualifies_for_pool") else "POOL_QUALIFIED",
        )
        rows.append(r)
    return rows


DIMENSION_RANK = {"FAIL": 0, "MISSING": 0, "WARN": 1, "UNKNOWN": 2, "PASS": 3}


def _worst(statuses: list[str]) -> str:
    return min(statuses, key=lambda s: DIMENSION_RANK.get(s, 2))


def load_latest_semantic_proof(semantic_dir: Path = SEMANTIC_DIR) -> dict | None:
    """Latest P0.1 volume-semantic proof, or None (absent/unreadable -> UNKNOWN)."""
    proofs = sorted(Path(semantic_dir).glob("semantic_proof_*.json"))
    if not proofs:
        return None
    try:
        return json.loads(proofs[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


PIT_DIM_STATUS = {"PIT_CLEAN": "PASS", "PIT_PARTIAL": "WARN", "PIT_CONTAMINATED": "FAIL"}


def load_latest_pit_audit(semantic_dir: Path = SEMANTIC_DIR) -> dict | None:
    """Latest P0.3 PIT audit, or None (absent/unreadable -> UNKNOWN)."""
    audits = sorted(Path(semantic_dir).glob("pit_audit_*.json"))
    if not audits:
        return None
    try:
        return json.loads(audits[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_latest_anti_leakage(semantic_dir: Path = SEMANTIC_DIR) -> dict | None:
    """Latest P0.4 anti-leakage check, or None (absent/unreadable -> UNKNOWN)."""
    checks = sorted(Path(semantic_dir).glob("anti_leakage_check_*.json"))
    if not checks:
        return None
    try:
        return json.loads(checks[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _pit_dimension(pit_audit: dict | None) -> dict:
    """PIT badge (spec P0.2/P0.3): the audit's spec-mandated verdict, verbatim."""
    if pit_audit is None:
        return {"status": "UNKNOWN", "detail": "尚未运行 tools/quant_pit_audit.py"}
    status = PIT_DIM_STATUS.get(str(pit_audit.get("verdict", "")))
    if status is None:
        return {"status": "UNKNOWN", "detail": "pit audit 判定不可读"}
    return {"status": status, "detail": str(pit_audit.get("implication", ""))}


def _semantic_dimension(proof: dict | None, snapshot: dict | None) -> dict:
    """Semantic integrity (spec P0.2): proof verdict + staleness vs the pool.

    A PASS proof only counts as PASS while it describes the candidate pool
    the page is showing (same as_of, full sample). A pool rebuild without a
    fresh validator run demotes to WARN — the open P0.1 rule.
    """
    if proof is None:
        return {"status": "UNKNOWN", "detail": "尚未运行 tools/quant_validate_semantics.py"}
    status = str(proof.get("status", "UNKNOWN"))
    if status != "PASS":
        mapped = status if status in ("FAIL", "WARN") else "UNKNOWN"
        return {"status": mapped, "detail": str(proof.get("reason", ""))}
    if proof.get("universe_as_of") != (snapshot or {}).get("as_of"):
        return {
            "status": "WARN",
            "detail": (
                f"semantic proof ({proof.get('universe_as_of')}) 落后于当前候选池 "
                f"({(snapshot or {}).get('as_of')}) — 池重建后必须重跑 validator"
            ),
        }
    if (proof.get("sample_size") or 0) < ((snapshot or {}).get("candidate_count") or 0):
        return {"status": "WARN", "detail": "semantic proof 样本小于当前候选池"}
    return {"status": "PASS", "detail": str(proof.get("reason", ""))}


def _freshness_dimension(snapshot: dict | None, scan: dict | None, now: datetime) -> dict:
    """Freshness (spec P0.2): quotes from today + no stale financial/valuation flags."""
    parts: list[str] = []
    lqt = (scan or {}).get("latest_quote_time")
    if not lqt:
        quote_status = "UNKNOWN"
        parts.append("无实时扫描")
    else:
        today = now.astimezone(TZ_SHANGHAI).strftime("%Y%m%d")
        quote_day = str(lqt)[:8]
        quote_status = "PASS" if quote_day == today else "WARN"
        if quote_status != "PASS":
            parts.append(f"行情非今日 ({quote_day})")
    cands = (snapshot or {}).get("candidates") or []
    stale = [
        c.get("symbol")
        for c in cands
        if {"FINANCIAL_DATA_STALE", "VALUATION_DATA_STALE"} & set(c.get("red_flags") or [])
    ]
    if stale:
        fin_status = "WARN"
        parts.append(f"{len(stale)} 只候选财报/估值数据过期")
    else:
        fin_status = "PASS"
    status = _worst([quote_status, fin_status])
    return {"status": status, "detail": "；".join(parts) or "行情与财报/估值均为最新"}


def data_quality(
    snapshot: dict | None,
    scan: dict | None,
    semantic_dir: Path = SEMANTIC_DIR,
    now: datetime | None = None,
) -> dict:
    if not snapshot:
        return {
            "status": "MISSING",
            "coverage": None,
            "degraded": True,
            "dimensions": {},
            "banner": "候选快照缺失 — 请先运行: uv run --group quant python tools/quant_build_candidates.py",
        }
    now = now or datetime.now(TZ_SHANGHAI)
    sources = snapshot.get("sources") or {}
    degradations = snapshot.get("source_degradations") or []
    degraded = snapshot.get("status") == "DEGRADED" or bool(degradations)
    financial_dates = [
        (c.get("data_freshness") or {}).get("financial_date")
        for c in snapshot.get("candidates") or []
        if (c.get("data_freshness") or {}).get("financial_date")
    ]
    coverage = snapshot.get("coverage")
    dimensions = {
        "coverage": {
            "status": "PASS" if coverage is not None and coverage >= 0.8 else "WARN",
            "detail": "必要字段覆盖率 " + (f"{coverage:.0%}" if coverage is not None else "缺失"),
        },
        "freshness": _freshness_dimension(snapshot, scan, now),
        "semantic_integrity": _semantic_dimension(load_latest_semantic_proof(semantic_dir), snapshot),
        # snapshot DEGRADED is the builder's bounded fail-open state: essential
        # coverage held but named sources failed — visible degradation, WARN
        "source_degradation": {
            "status": "WARN" if degraded else "PASS",
            "detail": "; ".join(sorted({d.get("source", "?") for d in degradations})) or ("快照 DEGRADED" if degraded else "无来源失败"),
        },
        # P0.3 audit verdict — CLEAN/PARTIAL/CONTAMINATED, never assumed green
        "pit": _pit_dimension(load_latest_pit_audit(semantic_dir)),
    }
    overall = _worst([d["status"] for d in dimensions.values()])
    failing = [k for k, d in dimensions.items() if d["status"] != "PASS"]
    banner = (
        "DATA DEGRADED — coverage below threshold or source failures; A-tier completeness is NOT claimed. Cached candidates are shown with their timestamps."
        if degraded
        else ""
    )
    if failing:
        prefix = "; ".join(f"{k}={dimensions[k]['status']}" for k in failing)
        banner = (banner + " " if banner else "") + f"数据质量分维未全绿: {prefix}"
    return {
        "status": overall,
        "coverage": coverage,
        "degraded": degraded or overall != "PASS",
        "dimensions": dimensions,
        "snapshot_as_of": snapshot.get("as_of"),
        "quote_as_of": (scan or {}).get("as_of"),
        "financial_source": (sources.get("financial") or {}).get("source"),
        "financial_retrieved_at": (sources.get("financial") or {}).get("retrieved_at"),
        "financial_latest_report": max(financial_dates) if financial_dates else None,
        "valuation_source": (sources.get("valuation_history") or {}).get("source"),
        "quotes_source": (sources.get("quotes") or {}).get("source"),
        "concentration": snapshot.get("concentration"),
        "degradations": degradations,
        "banner": banner,
    }


def load_trading_state(trading_dir: Path = TRADING_DIR) -> dict:
    """M1 trading-loop artifacts for the attention area (spec M1 §15).

    Reads only what the monitor wrote — the page never recomputes business
    state. Absent artifacts mean the monitor has not run yet.
    """
    state = read_json(trading_dir / "state.json")
    positions = read_json(trading_dir / "positions.json") or {}
    alerts: list[dict] = []
    alerts_path = trading_dir / "alerts.jsonl"
    if alerts_path.exists():
        try:
            lines = alerts_path.read_text(encoding="utf-8").splitlines()
            for line in lines[-8:]:
                try:
                    alerts.append(json.loads(line))
                except ValueError:
                    continue
            alerts.reverse()
        except OSError:
            pass
    return {
        "present": bool(state),
        "state": state or {},
        "open_positions": positions.get("open") or [],
        "alerts": alerts,
    }


# --------------------------------------------------------------------------
# NOW: bounded projection of durable trading facts (single implementation,
# shared by the static page and GET /api/quant/now via quant_serve)
# --------------------------------------------------------------------------

SESSION_AM = (dtime(9, 30), dtime(11, 30))
SESSION_PM = (dtime(13, 0), dtime(15, 0))
NOW_STALE_AFTER_S = 90  # only enforced while the session clock expects a live loop
NOW_ALERT_TAIL = 200
NOW_SOAK_TAIL = 200
NOW_ATTENTION_CAP = 12
NOW_RECENT_ALERTS = 10
NOW_MATERIAL_EVENTS = {"NEW_READY", "POSITION_EXIT_ALERT", "LIVE_CONNECTION_LOST", "DATA_UNTRUSTED"}
NOW_HUMAN_EVENTS = {"POSITION_OPENED", "POSITION_CLOSED", "HUMAN_SKIP"}


def in_trading_session(now: datetime) -> bool:
    """A-share session clock. A stdlib mirror of the monitor's rule: the
    stdlib-only renderer/server must not import the pandas-loading monitor."""
    if now.weekday() >= 5:
        return False
    t = now.time()
    return SESSION_AM[0] <= t <= SESSION_AM[1] or SESSION_PM[0] <= t <= SESSION_PM[1]


def _parse_ts(value) -> datetime | None:
    try:
        dt = datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=TZ_SHANGHAI)


def _latest_events(alerts: list[dict], types: set[str]) -> dict:
    """{(type, symbol): alert} keeping the newest ts per key (durable stream)."""
    out: dict = {}
    for a in alerts:
        if str(a.get("type")) not in types:
            continue
        key = (str(a.get("type")), str(a.get("symbol")))
        ts = _parse_ts(a.get("ts"))
        prev = out.get(key)
        if prev is None or (ts and _parse_ts(prev.get("ts")) is None) or (
            ts and _parse_ts(prev.get("ts")) and ts >= _parse_ts(prev.get("ts"))
        ):
            out[key] = a
    return out


def _human_action(symbol: str, human_events: dict) -> dict | None:
    for etype, label in (
        ("POSITION_OPENED", "HOLD(ack-buy)"),
        ("POSITION_CLOSED", "CLOSED(ack-sell)"),
        ("HUMAN_SKIP", "SKIP"),
    ):
        a = human_events.get((etype, symbol))
        if a:
            return {
                "action": label,
                "ts": a.get("ts"),
                "venue": a.get("venue"),
                "note": a.get("note"),
            }
    return None


def _agent_action(symbol: str, event_ts: str, briefs: list[dict]) -> dict | None:
    """Event-matched brief: only a brief recorded at/after the material event
    may answer it — an older judgement is never projected onto a newer fact."""
    ev_dt = _parse_ts(event_ts)
    if ev_dt is None:
        return None
    best = None
    for b in briefs:
        if str(b.get("symbol")) != symbol:
            continue
        b_dt = _parse_ts(b.get("recorded_at"))
        if b_dt is None or b_dt < ev_dt:
            continue
        if best is None or _parse_ts(best.get("recorded_at")) < b_dt:
            best = b
    if best is None:
        return None
    return {
        "action": best.get("action"),
        "decision_id": best.get("decision_id"),
        "recorded_at": best.get("recorded_at"),
        "why": best.get("why"),
        "invalidation": best.get("invalidation"),
    }


def now_snapshot(
    trading_dir: Path = TRADING_DIR,
    briefs_dir: Path = BRIEFS_DIR,
    active_symbols_path: Path = ACTIVE_SYMBOLS_PATH,
    now: datetime | None = None,
) -> dict:
    """NOW view (spec workbench §3.1/§21 + amendments): heartbeat comes from
    the soak tail, last_scan_at only from records that really scanned
    (symbols > 0), STALE only while the session clock expects a live loop,
    and material events come from the durable alert stream, not the
    last-cycle state.json.events."""
    now = now or datetime.now(TZ_SHANGHAI)
    state = read_json(Path(trading_dir) / "state.json") or {}
    soak = read_jsonl(Path(trading_dir) / "soak.jsonl")[-NOW_SOAK_TAIL:]
    alerts = read_jsonl(Path(trading_dir) / "alerts.jsonl")[-NOW_ALERT_TAIL:]
    universe = read_json(active_symbols_path) or {}
    universe_size = len(universe.get("symbols") or []) or None

    heartbeat_at = soak[-1].get("ts") if soak else None
    last_scan_at = next((r.get("ts") for r in reversed(soak) if (r.get("symbols") or 0) > 0), None)
    hb_dt, scan_dt = _parse_ts(heartbeat_at), _parse_ts(last_scan_at)
    now_dt = _parse_ts(now.isoformat()) or now
    hb_age = int((now_dt - hb_dt).total_seconds()) if hb_dt else None
    scan_age = int((now_dt - scan_dt).total_seconds()) if scan_dt else None
    expected_live = in_trading_session(now_dt)
    stale = bool(expected_live and hb_age is not None and hb_age > NOW_STALE_AFTER_S)
    if not state:
        runtime = "UNKNOWN"
    elif stale:
        runtime = "STALE"
    else:
        runtime = "HEALTHY"

    briefs = load_briefs(briefs_dir)
    material = _latest_events(alerts, NOW_MATERIAL_EVENTS)
    human_events = _latest_events(alerts, NOW_HUMAN_EVENTS)

    def agent_for(symbol: str, ts) -> dict | None:
        return _agent_action(symbol, ts, briefs)

    def human_for(symbol: str) -> dict | None:
        return _human_action(symbol, human_events)

    attention: list[dict] = []
    for sym in state.get("ready") or []:
        ev = material.get(("NEW_READY", sym)) or {}
        ts = ev.get("ts") or state.get("as_of")
        attention.append({
            "kind": "READY", "symbol": sym, "ts": ts, "price": ev.get("price"),
            "conditions": ev.get("conditions"),
            "agent": agent_for(sym, ts), "human": human_for(sym),
        })
    for sym in state.get("exit_alerts") or []:
        ev = material.get(("POSITION_EXIT_ALERT", sym)) or {}
        ts = ev.get("ts") or state.get("as_of")
        pos = next((p for p in state.get("positions") or [] if p.get("symbol") == sym), {})
        attention.append({
            "kind": "EXIT", "symbol": sym, "ts": ts, "price": pos.get("price") or ev.get("price"),
            "why": ev.get("why"), "entry_price": pos.get("entry_price"),
            "pnl": pos.get("pnl"), "venue": pos.get("venue"),
            "agent": agent_for(sym, ts), "human": human_for(sym),
        })
    if state.get("system_unavailable"):
        ev = material.get(("LIVE_CONNECTION_LOST", "None")) or {}
        attention.append({
            "kind": "SYSTEM_UNAVAILABLE", "symbol": None,
            "ts": ev.get("ts") or state.get("as_of"), "why": ev.get("why"),
            "price": None, "conditions": None,
            "agent": None, "human": None,
        })
    if state.get("data_trust") == "FAIL":
        ev = material.get(("DATA_UNTRUSTED", "None")) or {}
        attention.append({
            "kind": "DATA_UNTRUSTED", "symbol": None,
            "ts": ev.get("ts") or state.get("as_of"), "why": ev.get("why"),
            "price": None, "conditions": None,
            "agent": None, "human": None,
        })

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "present": bool(state),
        "as_of": state.get("as_of"),
        "day": state.get("day"),
        "status": state.get("status"),
        "market": "OPEN" if expected_live else "CLOSED",
        "expected_live": expected_live,
        "runtime": runtime,
        "stale": stale,
        "heartbeat_at": heartbeat_at,
        "heartbeat_age_seconds": hb_age,
        "last_scan_at": last_scan_at,
        "scan_age_seconds": scan_age,
        "symbols_scanned": state.get("symbols_scanned"),
        "universe_size": universe_size,
        "data_trust": state.get("data_trust") or "UNKNOWN",
        "ready": state.get("ready") or [],
        "near": state.get("near") or [],
        "exit_alerts": state.get("exit_alerts") or [],
        "positions": state.get("positions") or [],
        "attention": attention[:NOW_ATTENTION_CAP],
        "recent_alerts": alerts[-NOW_RECENT_ALERTS:],
    }


def load_timeline(trading_dir: Path = TRADING_DIR, day: str | None = None, limit: int = 100) -> list[dict]:
    """今日事件时间线: the durable alert stream in time order (one day when
    known). Only real persisted events — no inferred MARKET_CLOSE/START rows."""
    rows = []
    for a in read_jsonl(Path(trading_dir) / "alerts.jsonl"):
        if day and str(a.get("day") or "") != day:
            continue
        rows.append({
            "ts": a.get("ts"), "type": a.get("type"), "symbol": a.get("symbol"),
            "what": a.get("what"), "why": a.get("why"), "price": a.get("price"),
            "venue": a.get("venue"),
        })
    rows.sort(key=lambda r: str(r.get("ts")))
    return rows[-limit:]


def build_data(
    snapshot_path: Path = SNAPSHOT_PATH,
    scan_path: Path = LAST_SCAN_PATH,
    briefs_dir: Path = BRIEFS_DIR,
    obs_path: Path = OBS_LOG_PATH,
    status_path: Path = STATUS_PATH,
    active_path: Path = ACTIVE_PATH,
    legacy_path: Path = LEGACY_PATH,
    trading_dir: Path = TRADING_DIR,
    diagnostic_dir: Path = TRADING_DIAGNOSTIC_DIR,
    daily_dir: Path = DAILY_CACHE_DIR,
    active_symbols_path: Path = ACTIVE_SYMBOLS_PATH,
    semantic_dir: Path = SEMANTIC_DIR,
    v31_dir: Path = V31_ART,
) -> dict:
    snapshot = read_json(snapshot_path)
    scan = read_json(scan_path)
    briefs = load_briefs(briefs_dir)
    obs = parse_obs_log(obs_path)
    proofs = parse_proof_rows(status_path)
    legacy_symbols = load_legacy_symbols(legacy_path)
    real_trend = load_real_trend(
        trading_dir,
        diagnostic_dir=diagnostic_dir,
        daily_dir=daily_dir,
        active_symbols_path=active_symbols_path,
        semantic_dir=semantic_dir,
        v31_dir=v31_dir,
    )
    now = now_snapshot(
        trading_dir=trading_dir,
        briefs_dir=briefs_dir,
        active_symbols_path=active_symbols_path,
    )
    settled = real_trend["forward"]["settled"]
    results = harvest_strategy_results()
    best = best_strategy_row(results)
    decision = today_decision(briefs)
    dq = data_quality(snapshot, scan)
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "warning": STRATEGY_WARNING,
        "not_a_buy_note": NOT_A_BUY_NOTE,
        "trading": load_trading_state(trading_dir),
        "now": now,
        "timeline": load_timeline(trading_dir, day=now.get("day")),
        "real_trend": real_trend,
        "kpi": {
            "today_decision": decision["state"],
            "live_triggers": len((scan or {}).get("triggers") or []),
            "active_candidates": (snapshot or {}).get("candidate_count"),
            "forward_settled_trades": settled,
            "strategy_evidence": strategy_evidence_state(proofs),
        },
        "decision": decision,
        "trigger_rows": join_trigger_rows(scan, snapshot, briefs),
        "scan_meta": {
            "as_of": (scan or {}).get("as_of"),
            "universe": (scan or {}).get("universe"),
            "universe_size": (scan or {}).get("universe_size"),
            "present": scan is not None,
        },
        "board_rows": board_rows(snapshot),
        "snapshot_meta": {
            "as_of": (snapshot or {}).get("as_of"),
            "base_count": (snapshot or {}).get("base_count"),
            "eligible_count": (snapshot or {}).get("eligible_count"),
            "candidate_count": (snapshot or {}).get("candidate_count"),
            "coverage": (snapshot or {}).get("coverage"),
            "pool_target": (snapshot or {}).get("pool_target"),
            "deep_coverage_basis": (snapshot or {}).get("deep_coverage_basis"),
        },
        "legacy_rows": legacy_rows(snapshot, legacy_symbols),
        "legacy_question": "如果不考虑已经持有,这只股票今天能进入候选池吗?",
        "strategy": {
            "status": strategy_evidence_state(proofs),
            "best_annualized_pct": (best or {}).get("annualized_pct"),
            "best_trades": (best or {}).get("trades"),
            "pit_bias": True,
            "forward_observations": real_trend["forward"]["count"],
            "forward_settled": settled,
            "forward_hit_rate": "—" if settled < 10 else None,
            "results": results,
        },
        "obs_rows": obs,
        "data_quality": dq,
        "v31": load_v31_summary(v31_dir),
        "anti_leakage": {"verdict": (load_latest_anti_leakage() or {}).get("verdict")},
        "active_params": _parse_active(active_path),
    }


def _parse_active(path: Path) -> dict:
    out = {}
    for line in read_text(path).splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, _, v = s.partition("=")
        out[k.strip()] = v.strip().strip('"')
    return out


def load_v31_summary(v31_dir: Path = V31_ART) -> dict:
    """Build the v3.1 governance projection with strict namespace honesty."""
    replay = load_latest_v31_replay(v31_dir)
    shadow_report = read_json(_latest_v31_file(v31_dir, "shadow"))
    s0_report = read_json(_latest_v31_file(v31_dir, "research/s0-*"))
    experiment_dir = _latest_v31_experiment(v31_dir)
    proposal = read_json(experiment_dir / "proposal.json") if experiment_dir else None
    decision = read_json(experiment_dir / "decision.json") if experiment_dir else None
    return {
        "available": bool(replay or shadow_report or proposal),
        "replay": replay,
        "regime_shadow": (shadow_report or {}).get("payload"),
        "s0": s0_report,
        "experiment": proposal,
        "promotion": decision,
        "promotion_state": (decision or {}).get("state", "NOT_APPLICABLE"),
    }


def _latest_v31_file(v31_dir: Path, pattern: str) -> Path | None:
    files = sorted((Path(v31_dir) / pattern).glob("report.json"))
    return files[-1] if files else None


def _latest_v31_experiment(v31_dir: Path) -> Path | None:
    dirs = sorted(
        (p for p in (Path(v31_dir) / "research").iterdir() if p.is_dir() and (p / "decision.json").exists()),
        key=lambda p: p.name,
    )
    return dirs[-1] if dirs else None


GLOSSARY = {
    # metric key -> {t: 标题, h: 面板一行摘要, d: 定义, c: 口径/计算, u: 怎么用, l: 局限, s: 数据来源}
    "composite_score": {
        "t": "综合分",
        "h": "价值+质量+可交易+时机四维加权, 池内相对研究优先级",
        "d": "候选在池内的相对研究优先级得分 (0–100), 分数越高只代表越值得先看, 不代表预期收益。",
        "c": "价值 40 + 质量 35 + 可交易 15 + 时机 10 (权重见 candidates_policy.toml [score_weights])。",
        "u": "排序与筛选用; 排名不是买入建议。",
        "l": "池内相对分, 跨快照/跨池不可比; 策略边际优势尚未证明。",
        "s": "tools/quant_build_candidates.py 确定性计算",
    },
    "tier": {
        "t": "分级",
        "h": "A/B/C 研究关注等级, 命中关键红旗不得评 A",
        "d": "把综合分换算成三档关注等级。",
        "c": "A ≥ 75, B ≥ 60, C ≥ 50; 命中关键红旗(现金流持续弱于净利/数据过期/杠杆显著高于同业)时无论分数不得评 A。",
        "u": "一眼区分关注强度: A 级是池内最值得读财报与个股基本面的对象。",
        "l": "是关注等级, 不是买入等级。",
        "s": "确定性计算 (政策 [ranking])",
    },
    "value_score": {
        "t": "价值分",
        "h": "估值便宜度: PE/PB 行业相对位 + 自身3年分位 + 股息率",
        "d": "衡量相对同类便宜多少。",
        "c": "PE(TTM) 行业百分位 15 + PB 行业百分位 10 + 自身 3 年估值分位 10 + 股息率 5。",
        "u": "找到相对便宜的标的进入候选。",
        "l": "便宜 ≠ 安全, 价值陷阱(基本面恶化)只有有限红旗提示。",
        "s": "腾讯实时行情 + 百度 3 年估值历史",
    },
    "quality_score": {
        "t": "质量分",
        "h": "盈利质量: ROE/现金流/增长/负债率, 金融行业用专门模型",
        "d": "衡量赚钱的真实性与可持续性。",
        "c": "ROE 3 年均值行业百分位 10 + 经营现金流/净利润 10 + 收入利润增长 10 + 资产负债率(越低越好) 5; 金融行业跳过现金流与杠杆项并重新归一化。",
        "u": "筛选真赚钱、现金流健康、杠杆可控的公司。",
        "l": "财务数据为年/季报披露口径, 存在披露滞后(新鲜度预算 400 天)。",
        "s": "新浪财务指标 (akshare, 每只年度+季度)",
    },
    "tradeability_score": {
        "t": "可交易分",
        "h": "小资金能否进出: 成交额 + 日线历史充足度",
        "d": "回答小资金能不能顺畅进出, 不是动量分。",
        "c": "当日成交额对数线性(5000 万 → 5 亿满分) 10 + 日线历史充足度(≥250 根满分) 5。",
        "u": "避开流动性陷阱与历史过短的标的。",
        "l": "只测流动性, 不测涨跌方向。",
        "s": "腾讯实时行情 + 日线缓存",
    },
    "timing_state": {
        "t": "时序",
        "h": "距 S3 确定性入场规则的距离分级: 触发 / 接近 / 等待",
        "d": "当前价格距离确定性入场规则(S3: 5日回撤 ≤ −5% 且 20日量比 ≥ 1.8 且收盘走强)有多近。",
        "c": "TRIGGER = 三条件全中; NEAR = 回撤 ≤ −2.5% 或量比 ≥ 1.44; WAIT = 其余。只占综合分 10/100。",
        "u": "排序提示, 提示哪些候选正在靠近可交易区。",
        "l": "触发 ≠ 成交: 真实动作仍需实时扫描触发 + Agent 裁决; 盘中量比按累积量计算会低估。",
        "s": "builder 用实时行情 + 缓存历史计算",
    },
    "TRIGGER": {
        "t": "触发 (TRIGGER)",
        "h": "三条件全中 = 确定性买入候选信号, 仍需 Agent 裁决",
        "d": "当前报价同时满足: 5日回撤 ≤ −5%、20日量比 ≥ 1.8、当日收盘走强。",
        "c": "与实时扫描的入场规则同口径 (active.toml)。",
        "u": "出现 TRIGGER 时由 Agent 按证据裁决交易/观察/不交易。",
        "l": "放量回调抢反弹形态也常是主力出货场景; 触发不是订单, 止损纪律(3%)与仓位(单仓≤10%)仍由你执行。",
        "s": "实时扫描 (quant_live_scan.py)",
    },
    "NEAR": {
        "t": "接近触发 (NEAR)",
        "h": "差一步: 回撤到位但量未到, 或量爆了但价未跌到位",
        "d": "距离触发还差一半条件。",
        "c": "回撤 ≤ −2.5%(−5% 的一半) 或量比 ≥ 1.44(1.8 的 80%)。",
        "u": "提示候选正在靠近可交易区, 值得盯盘。",
        "l": "只代表距离, 不构成信号; 爆量接近(如量比 70+)也可能是出货躁动。",
        "s": "实时扫描",
    },
    "WAIT": {
        "t": "等待时机 (WAIT)",
        "h": "离触发还远, 无事可做",
        "d": "回撤与量比都不接近入场条件。",
        "u": "保持等待, 不创造交易。",
        "l": "多数时间池内大部分是等待状态, 这是正常密度, 不是故障。",
        "s": "实时扫描",
    },
    "pe_ttm": {
        "t": "PE(TTM)",
        "h": "市盈率(滚动12个月), 仅正盈利计入",
        "d": "股价 / 滚动 12 个月每股收益。",
        "c": "腾讯实时行情字段; 候选池内按行业算百分位(行业内有效样本 <8 只时回退全池并标注)。",
        "u": "行业相对便宜度(与同行比)。",
        "l": "负盈利按缺失处理, 不是很便宜; PE 低不代表会涨。",
        "s": "腾讯实时行情 (qt.gtimg.cn)",
    },
    "pb": {
        "t": "PB",
        "h": "市净率, 行业百分位口径",
        "d": "股价 / 每股净资产。",
        "c": "腾讯行情字段, 行业相对百分位。",
        "u": "辅助价值判断(尤其周期/重资产行业)。",
        "l": "轻资产/高无形资产行业参考性弱。",
        "s": "腾讯实时行情 (qt.gtimg.cn)",
    },
    "dividend_yield_pct": {
        "t": "股息率%",
        "h": "TTM 股息率, 0/缺失按缺失处理",
        "d": "现金分红 / 股价的年化比例。",
        "c": "腾讯行情字段, 线性 0 → 4% 记满分。",
        "u": "价值分里给高股息加分。",
        "l": "股息可持续性未验证; 0 或缺失不扣分也不加分。",
        "s": "腾讯实时行情 (qt.gtimg.cn)",
    },
    "roe_3y_pct": {
        "t": "ROE 3Y%",
        "h": "近三年平均净资产收益率, 行业相对",
        "d": "净利润 / 净资产的三年均值, 衡量赚钱效率。",
        "c": "新浪财务指标计算 3 年均值, 行业内百分位; 金融行业用金融组比较。",
        "u": "质量分的核心成分之一。",
        "l": "报告期滞后; 个别公司 ROE 恶化会被记红旗。",
        "s": "新浪财务指标 (akshare)",
    },
    "cfo_to_net_profit": {
        "t": "现金流/净利润",
        "h": "经营现金流与净利润之比, 金融行业跳过",
        "d": "赚到的利润有多少变成真实现金。",
        "c": "线性 0.4 → 1.0 记分; 最近两个报告期均 < 0.6 触发红旗(现金流持续弱于净利润)。",
        "u": "识别纸面利润风险。",
        "l": "金融行业现金流口径不同, 跳过该项。",
        "s": "新浪财务指标",
    },
    "debt_ratio": {
        "t": "负债率/杠杆",
        "h": "资产负债率, 行业内比低者优; 金融跳过",
        "d": "总负债 / 总资产。",
        "c": "行业百分位(越低越好); 高于行业中位数 +15pp 触发高杠杆红旗。",
        "u": "规避高杠杆经营风险。",
        "l": "银行/保险天然高负债率, 故金融行业跳过该项。",
        "s": "新浪财务指标",
    },
    "growth": {
        "t": "增长",
        "h": "收入+利润增长稳定性 (线性 −10%..+10%)",
        "d": "收入与利润增长的稳定性评分。",
        "c": "政策 [quality_components].growth 口径, 线性 0..1。",
        "u": "质量分成分之一。",
        "l": "部分银行无该数据, 如实标记缺失并重新归一化, 不猜值。",
        "s": "新浪财务指标",
    },
    "turnover_cny": {
        "t": "成交额",
        "h": "当日成交额(元), 硬门槛 5000 万",
        "d": "当日累计成交金额, 流动性硬指标。",
        "c": "腾讯行情字段(万元转元); 低于 5000 万直接硬排除。",
        "u": "保证小资金可进出。",
        "l": "盘中为累积值, 收盘前会变化。",
        "s": "腾讯实时行情 (qt.gtimg.cn)",
    },
    "valuation_percentile_3y": {
        "t": "3年估值分位",
        "h": "当前 PE 在自身 3 年 PE 分布中的位置 (0=三年最便宜)",
        "d": "相对自己历史便宜多少。",
        "c": "百度 3 年市盈率(TTM)序列, 当前值在历史分布中的百分位。",
        "u": "区分行业便宜(价值分)与自己历史便宜(本指标)。",
        "l": "覆盖 115/123; 估值史过期 >14 天记红旗, 缺失时该项重新归一化。",
        "s": "百度估值历史 (akshare)",
    },
    "pullback_5d": {
        "t": "5日回撤",
        "h": "现价相对 5 日前收盘的涨跌幅 (负=下跌)",
        "d": "入场规则的第一条件: 5 日回撤 ≤ −5%。",
        "c": "现价 / 5 日前收盘价 − 1, 用实时价 + 缓存日线。",
        "u": "识别短期超跌。",
        "l": "盘中按最新价计算, 尾盘才定型; 超跌可继续跌(下跌趋势无底)。",
        "s": "腾讯行情 + 日线缓存",
    },
    "volume_ratio_20d": {
        "t": "20日量比",
        "h": "当日量 / 20 日均量; 盘中按累积量会低估",
        "d": "放量程度, 入场规则第二条件 (≥ 1.8)。",
        "c": "当日成交量 / 20 日均量。",
        "u": "确认下跌伴随放量(流动性出逃或主力动作)。",
        "l": "盘中为累积量对比全日均量 → 低估; 极端爆量(如 70+)更可能是情绪/出货信号而非买入理由。",
        "s": "腾讯行情 + 日线缓存",
    },
    "coverage": {
        "t": "覆盖率",
        "h": "深度集里新鲜必需财务数据的占比; <80% 即降级",
        "d": "数据完整性指标。",
        "c": "深度集中拥有新鲜必需财务数据的股票数 / 深度集大小; 低于 80% 快照状态为降级, 页面禁止作 A 级完整性声明。",
        "u": "判断这份候选名单可信到几成。",
        "l": "只说数据完整性, 不说策略有效性。",
        "s": "候选构建统计",
    },
    "missing_fields": {
        "t": "缺失字段",
        "h": "缺失的评分成分; 缺失部分重新归一化, 从不猜值",
        "d": "该候选缺少哪些打分输入。",
        "c": "缺失成分在归一化时按零权重处理并在本字段如实列出。",
        "u": "阅读时留意缺失项, 缺失项多的候选分数参考性下降。",
        "l": "宁缺毋假: 系统从不编造缺失的事实。",
        "s": "builder 统计",
    },
    "red_flags": {
        "t": "红旗",
        "h": "风险标签: 现金流弱/高杠杆/ROE 恶化/数据过期等",
        "d": "确定性规则生成的风险警示标签。",
        "c": "含现金流持续弱于净利、杠杆高于同业+15pp、ROE 恶化、估值/财务数据过期等; 命中关键红旗不得评 A。",
        "u": "先读红旗再读分数; 红旗多 = 低优先级。",
        "l": "规则有限, 不能替代个股尽调。",
        "s": "builder 确定性规则",
    },
    "candidates": {
        "t": "候选池",
        "h": "当前活跃扫描宇宙 (50 只), 研究关注序, 非买入清单",
        "d": "实时扫描与每日决策实际覆盖的股票名单。",
        "c": "800 基础池(CSI300∪CSI500 当前成分) → 硬排除 → 打分 → 行业上限(前30名内每行业≤4) → 前 50。",
        "u": "缩小盯盘范围; 排除后不被扫描的股票不在观察范围。",
        "l": "重跑 builder 才更新(盘后/手动); 排名非买入建议; 成分含 PIT 局限。",
        "s": "tools/quant_build_candidates.py",
    },
    "eligible": {
        "t": "合格 / 硬排除",
        "h": "硬排除: ST/退、价≤0、成交额<5000万、历史<120根、负盈利、财务缺失/过期",
        "d": "进入打分前的一票否决条件。",
        "c": "名称含 ST/退; 最新价 ≤ 0; 成交额 < 5000万; 日线 < 120 根; PE(TTM) ≤ 0(负盈利); 财务缺失或超 400 天。",
        "u": "理解为什么某些标的(如持仓中的中国宝安)被排除。",
        "l": "排除是保守的: 被排除 ≠ 会跌, 只是系统对它的判断依据不足或风险哨兵拉起。",
        "s": "candidates_policy.toml [eligibility]",
    },
}


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------


def render_html(data: dict) -> str:
    blob = (
        json.dumps(data, ensure_ascii=False, indent=1)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    js = JS.replace("__GLOSSARY__", json.dumps(GLOSSARY, ensure_ascii=False))
    html = TEMPLATE.replace("__DATA_JSON__", blob)
    return html.replace("__CSS__", CSS).replace("__JS__", js)


TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZUAEF 量化决策看板</title>
<style>__CSS__</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>ZUAEF 量化决策看板
      <a class="badge b-eng" href="/engineering" style="margin-left:auto">工程 / 审计详情 → /engineering</a>
    </h1>
    <div class="sub">市场机会 · 候选证据 · 实时时序 · 前向结果 · 生成于 <span id="gen-time"></span> · 再生成: <code>python3 tools/quant_render_business_dashboard.py</code></div>
  </header>

  <div class="banner-warn" id="strategy-warning"></div>
  <div class="banner-degraded" id="dq-banner" style="display:none"></div>

  <div class="card" id="now-card">
    <h2>NOW <span class="scope live">LIVE</span> <span class="cnt" id="now-meta"></span></h2>
    <div class="nowgrid" id="now-grid"></div>
    <div id="now-stale" class="banner-degraded" style="display:none;margin-top:10px"></div>
  </div>

  <div class="card" id="attention-card">
    <h2>现在需要我做什么？ <span class="scope live">LIVE</span> <span class="cnt" id="att-meta">交易盯盘 · 30s 自动刷新</span></h2>
    <div id="att-status" style="font-weight:700;font-size:14px;margin-bottom:8px"></div>
    <div id="att-actions"></div>
    <div id="att-items" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px"></div>
    <div style="display:flex;gap:24px;flex-wrap:wrap">
      <div style="flex:1;min-width:260px">
        <div class="mut" style="font-weight:600;margin-bottom:4px">次级 Watch（NEAR — 未到行动级）</div>
        <div id="att-watch" class="mut"></div>
      </div>
    </div>
    <div id="att-alerts" style="margin-top:8px;font-size:12px"></div>
  </div>

  <div class="card" id="positions-card">
    <h2>Open Positions <span class="scope live">LIVE</span> <span class="cnt">持仓生命周期独立于候选池 · 只由 ack 建立/关闭</span></h2>
    <div id="att-positions-box"></div>
  </div>

  <div class="card" id="timeline-card">
    <h2>今日事件时间线 <span class="scope live">LIVE</span> <span class="cnt" id="tl-meta">durable alerts · 只列真实持久化事件</span></h2>
    <ul class="tl" id="tl-list"></ul>
  </div>

  <div class="card" id="real-trend-card">
    <h2>真实运行数据趋势 <span class="scope live">LIVE · HISTORICAL</span> <span class="cnt" id="rt-meta">M1 trading artifacts · 缺失保持缺失, 不补曲线</span></h2>
    <dl class="kv" id="m1-evidence" style="margin-bottom:10px"></dl>
    <div id="rt-chart"></div>
    <div id="rt-forward" style="margin-top:10px;font-size:13px"></div>
    <div id="rt-diagnostic" style="margin-top:12px"></div>
    <div class="mut" style="font-weight:600;margin:12px 0 4px;font-size:12px">真实 monitor 记录（trading/soak.jsonl · 一行 = 一次真实周期, 不去失真）</div>
    <div style="overflow-x:auto"><table>
      <thead><tr><th>时间</th><th>状态</th><th class="num-h">扫描数量</th><th class="num-h">universe size</th><th class="num-h">告警/事件数</th><th>来源</th></tr></thead>
      <tbody id="rt-rows"></tbody>
    </table></div>
  </div>

  <div class="kpi">
    <div class="k"><div class="v" id="kpi-decision">—</div><div class="l">今日决策</div></div>
    <div class="k"><div class="v" id="kpi-triggers">—</div><div class="l">实时触发</div></div>
    <div class="k"><div class="v" id="kpi-candidates">—</div><div class="l">活跃候选</div></div>
    <div class="k"><div class="v" id="kpi-settled">—</div><div class="l">前向已结算交易（正式）</div></div>
    <div class="k"><div class="v" id="kpi-evidence">—</div><div class="l">策略证据</div></div>
  </div>

  <div class="card" id="v31-governance-card">
    <h2>v3.1 证据与影子治理 <span class="scope research">V3.1 · SHADOW ONLY</span> <span class="cnt">research / replay / shadow 严格分离，不计入 live-forward</span></h2>
    <div id="v31-summary"></div>
  </div>

  <div class="card">
    <h2>今日动作候选 <span class="scope today">TODAY · LIVE</span> <span class="cnt" id="scan-meta"></span></h2>
    <div id="trigger-box"></div>
  </div>

  <div class="layout-board">
  <div class="card">
    <h2>价值 · 质量机会板 <span class="scope today">TODAY</span> <span class="cnt" id="board-meta"></span>
      <button class="btn glossary-toggle" id="glossary-open" type="button" aria-expanded="false" aria-controls="glossary-drawer">查看指标备注</button>
    </h2>
    <div style="overflow-x:auto"><table id="board">
      <thead><tr id="board-head"></tr></thead>
      <tbody id="board-rows"></tbody>
    </table></div>
    <div class="mut" style="font-size:11.5px;margin-top:8px" id="not-a-buy"></div>
  </div>
  </div>

  <div class="drawer-backdrop" id="glossary-backdrop" hidden></div>
  <aside class="drawer" id="glossary-drawer" hidden aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="glossary-title">
    <div class="drawer-head">
      <h2 id="glossary-title">指标备注 <span class="cnt">点击任一指标 / 单元格弹出详细说明</span></h2>
      <button class="modal-x" id="glossary-close" type="button" title="关闭" aria-label="关闭指标备注">×</button>
    </div>
    <div class="drawer-body">
      <div class="g-list" id="glossary-list"></div>
    </div>
  </aside>

  <div class="card">
    <h2>历史持仓 · 套牢仓位 <span class="scope hist">HISTORICAL</span> <span class="cnt" id="legacy-count">自选/持仓名单 — 诊断位, 不是机会宇宙</span></h2>
    <div class="mut question" id="legacy-question"></div>
    <div style="overflow-x:auto"><table>
      <thead><tr><th>代码</th><th>名称</th><th>现价</th><th>综合分</th><th>价值</th><th>质量</th><th>Timing</th>
        <th>能独立入选候选池?</th><th>状态</th><th>主要弱点 / 红旗</th></tr></thead>
      <tbody id="legacy-rows"></tbody>
    </table></div>
  </div>

  <div class="grid two">
    <div class="card">
      <h2>策略证据 <span class="scope research">RESEARCH · frozen S3</span></h2>
      <div id="strategy-box"></div>
      <details style="margin-top:12px">
        <summary>策略实验历史 (基线 / S1 / S2 / S3)</summary>
        <div class="body"><div style="overflow-x:auto"><table>
          <thead><tr><th>轮次</th><th style="text-align:right">年化 (重放)</th><th style="text-align:right">笔数</th><th style="text-align:right">最大回撤</th><th>结论</th></tr></thead>
          <tbody id="results-rows"></tbody>
        </table></div></div>
      </details>
    </div>
    <div class="card">
      <h2>前向证据 <span class="scope research">RESEARCH · FORMAL</span> <span class="cnt">正式 = trading/forward.json · 无合成占位</span></h2>
      <div id="formal-forward" style="font-size:13px;margin-bottom:10px"></div>
      <div class="mut" style="font-weight:600;font-size:12px;margin-bottom:4px">历史每日扫描日志（旧每日链路口径 — 仅历史兼容, 非当前 M1 truth）</div>
      <div style="overflow-x:auto"><table>
        <thead><tr><th>日期</th><th>时间</th><th style="text-align:right">扫描只数</th><th style="text-align:right">触发数</th><th>决策</th><th>备注</th></tr></thead>
        <tbody id="obs-rows"></tbody>
      </table></div>
      <div class="mut" style="font-size:11.5px;margin-top:8px">入场 / D+1 / D+3 / D+5 / D+8 价格路径与最大有利·不利偏移 (MFE/MAE) 在正式 forward observation 产生后展示；诊断性记录只出现在「真实运行数据趋势」卡并明确标记 diagnostic。</div>
    </div>
  </div>

  <div class="card">
    <h2>数据质量 <span class="scope today">TODAY</span></h2>
    <div id="dq-box"></div>
  </div>

  <footer>
    本页是业务决策面: 候选排名只是研究注意力排序, <b>不是买入建议</b>; 实际动作仍需确定性实时触发 + 人工决策。
    <br>历史回放数字受 PIT/成分偏差约束且在噪声内 (<b>盈利能力仍未证明</b>)。工程证据链 (重放 / 数据溯源 / 证明状态) 见
    <a href="/engineering">工程 / 审计 → /engineering</a>。
  </footer>
</div>
<div class="modal" id="trade-modal" hidden>
  <div class="modal-box" style="max-width:480px">
    <div class="modal-head"><h3 id="tm-title"></h3><button class="modal-x" id="tm-close" title="关闭">×</button></div>
    <div class="modal-body">
      <div class="form-row"><label>symbol</label><input id="tm-symbol" readonly></div>
      <div class="form-row"><label>shares</label><input id="tm-shares" type="number" min="1" step="1"></div>
      <div class="form-row"><label>price</label><input id="tm-price" type="number" min="0.0001" step="0.0001"></div>
      <div class="form-row"><label>venue</label><select id="tm-venue"><option value="paper">paper</option><option value="real">real</option></select></div>
      <div class="form-row"><label>executed_at</label><input id="tm-time"></div>
      <div class="form-row"><label>note</label><input id="tm-note" placeholder="可选备注"></div>
      <div class="form-msg" id="tm-msg"></div>
      <div class="btnrow"><button class="btn primary" id="tm-submit">确认记录</button></div>
    </div>
  </div>
</div>
<div class="modal" id="metric-modal" hidden>
  <div class="modal-box">
    <div class="modal-head"><h3 id="mm-title"></h3><button class="modal-x" id="mm-close" title="关闭">×</button></div>
    <div class="modal-body" id="mm-body"></div>
  </div>
</div>
<script>
window.DASH = __DATA_JSON__;
__JS__
</script>
</body>
</html>
"""

CSS = """\
:root{
  --bg:#0b0e14; --panel:#12161f; --panel2:#0f1420; --line:#1f2733; --line2:#27303f;
  --tx:#d7dde8; --mut:#8b96a8; --dim:#5c6678;
  --acc:#4cc2ff; --green:#3fb950; --amber:#d29922; --red:#f85149;
}
*{box-sizing:border-box;margin:0;padding:0}
body{overflow-x:hidden}
body{background:var(--bg);color:var(--tx);font:14px/1.55 -apple-system,"PingFang SC","Microsoft YaHei","Noto Sans SC",system-ui,sans-serif;padding:24px 20px 60px}
.wrap{max-width:1280px;margin:0 auto}
a{color:var(--acc);text-decoration:none} a:hover{text-decoration:underline}
code{font:12.5px "SFMono-Regular",Consolas,monospace;background:var(--panel2);border:1px solid var(--line);border-radius:5px;padding:1px 6px;color:#9ecbff}
h1{font-size:22px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.sub{color:var(--mut);font-size:13px;margin-top:6px}
.badge{font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;letter-spacing:.4px;border:1px solid}
.b-eng{color:#062a3d;background:var(--acc);border-color:var(--acc)}
.banner-warn{margin-top:16px;border:1px solid #5c4a1e;background:#1b170c;color:var(--amber);border-radius:10px;padding:10px 14px;font-size:13px;font-weight:600}
.banner-degraded{margin-top:10px;border:1px solid #6b2020;background:#1d0f0f;color:var(--red);border-radius:10px;padding:10px 14px;font-size:13px;font-weight:600}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-top:14px}
.kpi .k{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .v{font-size:20px;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .l{font-size:11.5px;color:var(--mut);margin-top:2px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-top:16px}
.card h2{font-size:14px;letter-spacing:.3px;color:#b7c2d4;margin-bottom:12px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.card h2 .cnt{font-size:11px;color:var(--dim);font-weight:400}
.grid.two{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:16px}
@media(max-width:960px){.grid.two{grid-template-columns:minmax(0,1fr)}}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--mut);font-weight:600;text-align:left;font-size:12px;padding:6px 8px;border-bottom:1px solid var(--line2);white-space:nowrap;cursor:pointer}
th.num-h{text-align:right}
td{padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
.num{font-variant-numeric:tabular-nums;text-align:right}
.mut{color:var(--mut)} .dim{color:var(--dim)}
.chip{display:inline-block;font-size:11px;font-weight:600;padding:1px 8px;border-radius:12px;white-space:nowrap}
.chip.A{color:#163a22;background:var(--green)}
.chip.B{color:#062a3d;background:var(--acc)}
.chip.C{color:#3a2c0d;background:var(--amber)}
.chip.DROP{color:var(--mut);background:var(--panel2);border:1px solid var(--line2)}
.chip.TRIGGER{color:#3b1110;background:var(--red)}
.chip.NEAR{color:#3a2c0d;background:var(--amber)}
.chip.WAIT{color:var(--mut);background:var(--panel2);border:1px solid var(--line2)}
.chip.ok{color:#163a22;background:var(--pass,#3fb950)}
.chip.bad{color:#3b1110;background:var(--red)}
.chip.gray{color:var(--mut);background:var(--panel2);border:1px solid var(--line2)}
.rf{color:var(--red);font-size:11.5px}
.reason{color:var(--mut);font-size:12px}
.empty{border:1px dashed var(--line2);border-radius:10px;padding:22px;text-align:center}
.empty .t{font-size:16px;font-weight:700;color:var(--tx);letter-spacing:.5px}
.empty .s{font-size:12.5px;color:var(--mut);margin-top:6px}
.question{border-left:3px solid var(--acc);padding:6px 12px;margin-bottom:12px;font-size:13px;color:#b7c2d4}
.scope{font-size:10px;font-weight:700;letter-spacing:.6px;padding:1px 8px;border-radius:10px;border:1px solid var(--line2);color:var(--dim)}
.scope.live{color:var(--green);border-color:var(--green)}
.scope.today{color:var(--acc);border-color:var(--acc)}
.scope.hist{color:var(--amber);border-color:var(--amber)}
.scope.research{color:var(--mut)}
.nowgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}
.nowgrid .n{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px 10px}
.nowgrid .n .k{font-size:10.5px;color:var(--dim);letter-spacing:.4px}
.nowgrid .n .v{font-size:15px;font-weight:700;font-variant-numeric:tabular-nums;margin-top:2px}
.action-card{border:1px solid var(--line2);border-radius:10px;padding:12px 14px;margin-bottom:10px;background:var(--panel2)}
.action-card .ac-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.action-card .ac-kind{font-size:11px;font-weight:700;letter-spacing:.5px;padding:2px 9px;border-radius:12px}
.ac-kind.READY{color:#163a22;background:var(--green)}
.ac-kind.EXIT{color:#3b1110;background:var(--red)}
.ac-kind.SYSTEM_UNAVAILABLE,.ac-kind.DATA_UNTRUSTED{color:#3b1110;background:var(--red)}
.ac-kind.NEAR{color:#3a2c0d;background:var(--amber)}
.threestate{display:grid;grid-template-columns:auto 1fr;gap:2px 12px;font-size:12.5px;margin:8px 0}
.threestate .st-k{color:var(--dim);letter-spacing:.4px;font-size:11px;padding-top:1px}
.btnrow{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.btn{font-size:12px;font-weight:600;padding:4px 12px;border-radius:8px;border:1px solid var(--line2);background:var(--panel);color:var(--tx);cursor:pointer}
.btn:hover{border-color:var(--acc);color:var(--acc)}
.btn.primary{background:var(--acc);border-color:var(--acc);color:#062a3d}
.btn.danger{border-color:var(--red);color:var(--red)}
.tl{list-style:none;font-size:12.5px}
.tl li{display:flex;gap:10px;padding:3px 0;border-bottom:1px dashed var(--line)}
.tl li:last-child{border-bottom:none}
.tl .ts{color:var(--dim);font-variant-numeric:tabular-nums;white-space:nowrap}
.form-row{display:flex;gap:10px;margin-bottom:8px;align-items:center}
.form-row label{font-size:12px;color:var(--mut);min-width:90px}
.form-row input,.form-row select{background:var(--panel2);border:1px solid var(--line2);border-radius:6px;color:var(--tx);padding:5px 8px;font-size:13px;flex:1}
.form-msg{font-size:12.5px;margin-top:6px;min-height:16px}
.layout-board{display:block;margin-top:16px}
.layout-board .card{margin-top:0}
.glossary-toggle{margin-left:auto;white-space:nowrap}
.drawer-backdrop{position:fixed;inset:0;background:rgba(3,6,10,.66);z-index:60;opacity:0;transition:opacity .2s ease}
.drawer-backdrop[hidden]{display:none}
.drawer-backdrop.is-open{opacity:1}
.drawer{position:fixed;top:0;right:0;width:min(420px,100vw);max-width:100%;height:100vh;height:100dvh;overflow-y:auto;background:var(--panel);border-left:1px solid var(--line2);box-shadow:-18px 0 60px rgba(0,0,0,.45);z-index:61;transform:translateX(100%);transition:transform .2s ease;padding:18px}
.drawer[hidden]{display:none}
.drawer.is-open{transform:translateX(0)}
.drawer-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;border-bottom:1px solid var(--line);padding-bottom:12px}
.drawer-head h2{font-size:14px;letter-spacing:.3px;color:#b7c2d4;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.drawer-head .cnt{font-size:11px;color:var(--dim);font-weight:400}
.drawer-body{padding-top:14px}
@media(max-width:480px){.drawer{width:100vw;padding:14px}}
@media(prefers-reduced-motion:reduce){.drawer,.drawer-backdrop{transition:none}}
.g-list{display:flex;flex-direction:column;gap:6px}
.g-item{display:flex;align-items:baseline;gap:8px;width:100%;padding:7px 10px;border:1px solid var(--line);border-radius:8px;font:inherit;font-size:12.5px;text-align:left;color:var(--tx);background:var(--panel2);cursor:pointer}
.g-item:hover{border-color:var(--acc)}
.g-item .gk{font-weight:700;color:var(--acc);white-space:nowrap}
.g-item .g1{min-width:0;color:var(--mut);font-size:11.5px;line-height:1.45;overflow-wrap:anywhere}
[data-m]{cursor:help}
.modal{position:fixed;inset:0;background:rgba(3,6,10,.66);display:flex;align-items:flex-start;justify-content:center;padding:6vh 16px;z-index:70;backdrop-filter:blur(2px)}
.modal[hidden]{display:none}
.modal-box{background:var(--panel);border:1px solid var(--line2);border-radius:14px;max-width:640px;width:100%;max-height:82vh;overflow:auto;box-shadow:0 18px 60px rgba(0,0,0,.5)}
.modal-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel)}
.modal-head h3{font-size:15px;color:var(--acc)}
.modal-x{background:none;border:none;color:var(--dim);font-size:22px;cursor:pointer;line-height:1;padding:0 4px}
.modal-x:hover{color:var(--tx)}
.modal-body{padding:14px 18px 20px;font-size:13px;line-height:1.7}
.mm-row{margin-bottom:10px}
.mm-row .mmk{font-size:11px;color:var(--dim);letter-spacing:.5px;font-weight:600}
.mm-row .mmv{color:var(--tx)}
details{background:var(--panel2);border:1px solid var(--line);border-radius:10px;overflow:hidden}
summary{cursor:pointer;padding:10px 14px;font-size:13px;font-weight:600;color:#b7c2d4;list-style:none}
summary::before{content:"▸";color:var(--dim);margin-right:6px}
details[open] summary::before{content:"▾"}
details .body{padding:0 14px 12px}
dl.kv{display:grid;grid-template-columns:auto 1fr;gap:4px 14px;font-size:13px}
dl.kv dt{color:var(--dim)}
footer{margin-top:26px;color:var(--dim);font-size:12px;border-top:1px solid var(--line);padding-top:14px;line-height:1.8}
"""

JS = r"""
const D = window.DASH;
const $ = (id) => document.getElementById(id);
const fmt = (v, d=2) => v==null||v==='' ? '—' : (typeof v==='number' ? v.toFixed(d) : v);
const esc = (s) => String(s??'').replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const pct = (v) => v==null ? '—' : (v*100).toFixed(0) + '%';

/* 展示层中文映射: 工件/简报中的规范代码保持英文, 页面一律中文 */
const ACTION_ZH = {NO_TRADE:'不交易', WATCH:'观察', ENTER_CANDIDATE:'入选候选', HOLD:'持有', REDUCE:'减仓', EXIT:'退出', NOT_RUN_TODAY:'今日未运行'};
const TIMING_ZH = {WAIT:'等待时机', NEAR:'接近触发', TRIGGER:'触发'};
const EV_ZH = {UNPROVEN:'尚未证明', WEAK:'证据薄弱', FORWARD_BUILDING:'前向积累中'};
const FLAG_ZH = {
  NEGATIVE_EARNINGS:'负盈利', CFO_BELOW_NET_PROFIT_PERSISTENT:'现金流持续弱于净利润',
  HIGH_LEVERAGE_REL_SECTOR:'杠杆显著高于同业', ROE_DETERIORATION:'ROE 恶化',
  PROFIT_GROWTH_NEGATIVE:'利润负增长', VALUATION_DATA_STALE:'估值数据过期',
  FINANCIAL_DATA_STALE:'财务数据过期', INSUFFICIENT_HISTORY:'日线历史不足',
  LOW_LIQUIDITY:'流动性不足', SOURCE_DEGRADED:'数据源降级',
  ST_OR_RISK_WARNING_NAME:'ST/风险警示', PRICE_NON_POSITIVE:'价格异常',
  MISSING_FINANCIAL_DATA:'缺少财务数据',
};
const zh = (map, code) => map[code] || code;
const zhFlags = (codes) => (codes||[]).map(c=>zh(FLAG_ZH,c)).join(', ');

/* ---- 指标备注: 点击任意指标/单元格弹出详细说明 ---- */
const GLOSSARY = __GLOSSARY__;
function openMetric(key){
  const g = GLOSSARY[key];
  if(!g) return;
  $('mm-title').textContent = g.t;
  $('mm-body').innerHTML = [['定义',g.d],['口径 / 计算',g.c],['怎么用',g.u],['局限',g.l],['数据来源',g.s]]
    .filter(r=>r[1]).map(([k,v])=>`<div class="mm-row"><div class="mmk">${esc(k)}</div><div class="mmv">${esc(v)}</div></div>`).join('');
  $('metric-modal').hidden = false;
}
function closeMetric(){
  $('metric-modal').hidden = true;
}
function renderGlossary(){
  $('glossary-list').innerHTML = Object.entries(GLOSSARY).map(([k,g])=>`<button type="button" class="g-item" data-m="${esc(k)}" title="点击查看 ${esc(g.t)} 的详细说明"><span class="gk">${esc(g.t)}</span><span class="g1">${esc(g.h||'')}</span></button>`).join('');
}
function setGlossaryOpen(open){
  const trigger = $('glossary-open');
  const drawer = $('glossary-drawer');
  const backdrop = $('glossary-backdrop');
  if(!trigger || !drawer || !backdrop) return;
  trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
  drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
  if(open){
    drawer.hidden = false;
    backdrop.hidden = false;
    drawer.classList.add('is-open');
    backdrop.classList.add('is-open');
    $('glossary-close').focus();
  } else {
    drawer.classList.remove('is-open');
    backdrop.classList.remove('is-open');
    drawer.hidden = true;
    backdrop.hidden = true;
    trigger.focus();
  }
}
function openGlossary(){ setGlossaryOpen(true); }
function closeGlossary(){ setGlossaryOpen(false); }
document.addEventListener('click', (e)=>{
  const el = e.target.closest('[data-m]');
  if(el){ openMetric(el.dataset.m); return; }
  if(e.target.id === 'glossary-open'){ openGlossary(); return; }
  if(e.target.id === 'glossary-close' || e.target.id === 'glossary-backdrop'){ closeGlossary(); return; }
  if(e.target.id === 'mm-close'){ closeMetric(); return; }
  if(e.target.closest('#metric-modal') && !e.target.closest('.modal-box')){ closeMetric(); }
});
document.addEventListener('keydown', (e)=>{
  if(e.key !== 'Escape') return;
  if(!$('metric-modal').hidden){ closeMetric(); return; }
  if(!$('glossary-drawer').hidden){ closeGlossary(); return; }
});

function kpiColor(v){ return v==null ? 'var(--dim)' : 'var(--tx)'; }

function drawTriggers(trs, live){
  const box = $('trigger-box');
  if (!trs.length){
    box.innerHTML = `<div class="empty"><div class="t">无今日动作候选</div>
      <div class="s">当前没有符合条件的股票满足确定性时序规则。</div></div>`;
    return;
  }
  const tag = live ? '<span class="chip NEAR">实时</span> ' : '';
  box.innerHTML = `${tag}<div style="overflow-x:auto"><table>
    <thead><tr><th>代码</th><th>名称</th><th>行业</th><th class="num-h">价格</th>
    <th class="num-h">价值分</th><th class="num-h">质量分</th><th class="num-h">综合分</th>
    <th class="num-h">5日回撤</th><th class="num-h">20日量比</th><th>触发时间</th><th>Agent 决策</th><th>失效条件 · 主要风险</th></tr></thead>
    <tbody>${trs.map(t=>`<tr>
      <td><code>${esc(t.symbol)}</code></td><td>${esc(t.name)}</td><td>${esc(t.industry)}</td>
      <td class="num">${fmt(t.price)}</td>
      <td class="num" data-m="value_score">${fmt(t.value_score,1)}</td><td class="num" data-m="quality_score">${fmt(t.quality_score,1)}</td>
      <td class="num" style="font-weight:700" data-m="composite_score">${fmt(t.composite_score,1)}</td>
      <td class="num" data-m="pullback_5d">${fmt(t.pullback_5d!=null?t.pullback_5d*100:null,2)}%</td>
      <td class="num" data-m="volume_ratio_20d">${fmt(t.volume_ratio_20d)}</td>
      <td class="mut">${esc(t.trigger_time)}</td>
      <td>${t.agent_action?`<span class="chip B" title="${esc(t.agent_action)}">${esc(zh(ACTION_ZH,t.agent_action))}</span>`:'<span class="dim">待决策</span>'}</td>
      <td class="rf">${(t.red_flags&&t.red_flags.length)?esc(zhFlags(t.red_flags)):'无候选红旗记录'}</td></tr>`).join('')}</tbody></table></div>`;
}

/* ---- NOW / Action Queue / Positions: single fact = /api/quant/now ---- */
const fmtAge = (s) => s==null ? '—' : (s < 90 ? s+'s' : Math.floor(s/60)+'m'+(s%60)+'s');
const nowTs = (v) => v ? String(v).slice(11,19) : '—';
let lastNow = null;

function renderNow(n){
  lastNow = n || lastNow;
  n = n || {};
  const grid = $('now-grid'), st = $('now-stale');
  $('now-meta').textContent = n.present
    ? `as_of ${nowTs(n.as_of)} · generated ${nowTs(n.generated_at)}`
    : 'monitor 尚未运行 — 无 NOW 事实';
  if(!n.present){
    grid.innerHTML = '<div class="n"><div class="k">Runtime</div><div class="v" style="color:var(--amber)">UNKNOWN</div></div>' +
      '<div class="n"><div class="k">说明</div><div class="v" style="font-size:12px">启动: python tools/quant_trading_monitor.py session</div></div>';
    st.style.display = 'none';
    renderAttention(n);
    return;
  }
  const cov = (n.symbols_scanned!=null && n.universe_size) ? `${n.symbols_scanned}/${n.universe_size}`
            : (n.universe_size ? `—/${n.universe_size}` : '—');
  const cells = [
    ['市场', n.market, n.market==='OPEN'?'var(--green)':'var(--mut)'],
    ['Runtime', n.runtime, n.runtime==='HEALTHY'?'var(--green)':(n.runtime==='STALE'?'var(--red)':'var(--amber)')],
    ['交易时段', n.expected_live?'ACTIVE':'CLOSED', n.expected_live?'var(--green)':'var(--mut)'],
    ['最后心跳', `${nowTs(n.heartbeat_at)} · age ${fmtAge(n.heartbeat_age_seconds)}`],
    ['最后成功扫描', n.last_scan_at ? `${nowTs(n.last_scan_at)} · age ${fmtAge(n.scan_age_seconds)}` : '无真实扫描记录'],
    ['扫描覆盖', cov],
    ['Data trust', n.data_trust, n.data_trust==='PASS'?'var(--green)':(n.data_trust==='FAIL'?'var(--red)':'var(--amber)')],
    ['READY', (n.ready||[]).length, (n.ready||[]).length?'var(--green)':null],
    ['NEAR', (n.near||[]).length, null],
    ['EXIT', (n.exit_alerts||[]).length, (n.exit_alerts||[]).length?'var(--red)':null],
    ['Open positions', (n.positions||[]).length, null],
  ];
  grid.innerHTML = cells.map(([k,v,c])=>
    `<div class="n"><div class="k">${esc(k)}</div><div class="v"${c?` style="color:${c}"`:''}>${esc(String(v??'—'))}</div></div>`).join('');
  // STALE fires only while the session clock expects a live loop (server-side rule)
  if(n.stale){
    st.className = 'banner-degraded'; st.style.display = 'block';
    st.textContent = `RUNTIME STALE — 交易时段内心跳超龄 (>90s) · Last success ${nowTs(n.heartbeat_at)} · Age ${fmtAge(n.heartbeat_age_seconds)}`;
  } else if(!n.expected_live){
    st.className = ''; st.style.display = 'block';
    st.style.cssText = 'display:block;margin-top:10px;color:var(--dim);font-size:12px';
    st.textContent = '非交易时段 — 显示最后心跳 / 最后成功扫描，不按心跳 age 报故障';
  } else {
    st.style.display = 'none';
  }
  renderAttention(n);
}

function renderAttention(n){
  const statusEl = $('att-status');
  const state = n || {};
  if(!state.present){
    statusEl.textContent = '盯盘监控未运行 — 启动: python tools/quant_trading_monitor.py session';
    statusEl.style.color = 'var(--amber)';
  } else if(state.status === 'SYSTEM_UNAVAILABLE'){
    statusEl.textContent = 'SYSTEM_UNAVAILABLE — 系统不可用/数据不可信（这不是 NO_TRADE）';
    statusEl.style.color = 'var(--red)';
  } else if(state.data_trust === 'FAIL'){
    statusEl.textContent = 'DATA_UNTRUSTED — semantic gate fail-closed，触发条件被抑制（这与系统失联是两回事）';
    statusEl.style.color = 'var(--red)';
  } else if((state.ready||[]).length || (state.exit_alerts||[]).length){
    statusEl.textContent = `需要行动 — READY ${(state.ready||[]).length} · EXIT ${(state.exit_alerts||[]).length}`;
    statusEl.style.color = 'var(--amber)';
  } else if(state.status === 'MARKET_CLOSED'){
    statusEl.textContent = '已收盘 — 监控待下一交易时段（无合成活动）';
    statusEl.style.color = 'var(--mut)';
  } else {
    statusEl.textContent = '有效扫描 · 无机会 — 市场已扫描，当前无 READY/EXIT';
    statusEl.style.color = 'var(--acc)';
  }
  const items = state.attention || [];
  $('att-actions').innerHTML = items.length ? items.map(actionCardHTML).join('')
    : '<div class="mut" style="font-size:12.5px;margin-bottom:8px">当前无需要行动的事项（无 READY / EXIT / 系统事件）</div>';
  const near = state.near || [];
  $('att-watch').textContent = near.length ? near.join(', ') : '当前无 NEAR';
  const alerts = state.recent_alerts || [];
  $('att-alerts').innerHTML = alerts.length ? alerts.slice().reverse().slice(0,5).map(a=>
    `<div>· <b>${esc(a.type||'')}</b> ${a.symbol?esc(a.symbol)+' — ':''}${esc(a.what||'')}${a.why?` · ${esc(a.why)}`:''}</div>`).join('') : '';
}

const agentState = (a) => a
  ? `<span class="chip B">${esc(a.action||'?')}</span> <span class="dim">${esc(a.decision_id||'')}</span>${a.why?`<div class="mut" style="font-size:12px">为什么: ${esc(a.why)}</div>`:''}${a.invalidation?`<div class="mut" style="font-size:12px">失效: ${esc(a.invalidation)}</div>`:''}`
  : '<span class="chip gray">尚未复核</span> <span class="dim">没有晚于本事件的 Agent brief</span>';
const humanState = (h) => h
  ? `<span class="chip NEAR">${esc(h.action||'?')}</span>${h.venue?` <span class="dim">venue ${esc(h.venue)}</span>`:''}${h.note?` <span class="dim">· ${esc(h.note)}</span>`:''} <span class="dim">${nowTs(h.ts)}</span>`
  : '<span class="dim">NO ACTION YET</span>';

function actionCardHTML(it){
  const head = `<div class="ac-head">
    <span class="ac-kind ${esc(it.kind)}">${esc(it.kind)}</span>
    ${it.symbol?`<code>${esc(it.symbol)}</code>`:''}
    ${it.price!=null?`<span class="num">${fmt(it.price)}</span>`:''}
    <span class="dim">${nowTs(it.ts)}</span>
    ${it.entry_price!=null?`<span class="dim">entry ${fmt(it.entry_price)}</span>`:''}
    ${it.pnl!=null?`<span class="num">P&L ${fmt(it.pnl)}</span>`:''}
    ${it.venue?`<span class="chip gray">${esc(it.venue)}</span>`:''}
  </div>`;
  let runtime = '', btns = '';
  if(it.kind === 'READY'){
    const c = it.conditions || {};
    runtime = `<div class="mut" style="font-size:12.5px">Deterministic: pullback ${fmt(c.pullback_5d!=null?c.pullback_5d*100:null,2)}% · 量比 ${fmt(c.volume_ratio_20d)} · 1d strength ${fmt(c.strength_1d)} — 冻结入场条件全部成立</div>`;
    btns = [['ack-buy','Paper Buy','paper','primary'],['ack-buy','Record Real Buy','real','danger'],['skip','Skip',null,''],
            ['ask','Ask Agent',null,''],['keep','Keep Watching',null,'']];
  } else if(it.kind === 'EXIT'){
    runtime = `<div class="mut" style="font-size:12.5px">触发: ${esc(it.why||'冻结退出规则')}</div>`;
    btns = [['ack-sell','Paper Sell','paper','primary'],['ack-sell','Record Real Sell','real','danger'],['ask','Ask Agent',null,'']];
  } else {
    runtime = `<div class="mut" style="font-size:12.5px">${esc(it.why||'系统级事件 — 需要人知晓')}</div>`;
  }
  const btnHTML = btns.map(([k,label,venue,cls]) =>
    `<button class="btn ${cls}" data-act="${k}" data-symbol="${esc(it.symbol||'')}" ${venue?`data-venue="${venue}"`:''}
      data-shares="${esc((lastNow&&((lastNow.positions||[]).find(p=>p.symbol===it.symbol))||{}).shares??'')}"
      data-price="${esc(it.price??'')}">${esc(label)}</button>`).join('');
  return `<div class="action-card" data-kind="${esc(it.kind)}" data-symbol="${esc(it.symbol||'')}">${head}
    ${runtime}
    <div class="threestate">
      <span class="st-k">RUNTIME</span><span>${esc(it.kind)}</span>
      <span class="st-k">AGENT</span><span>${agentState(it.agent)}</span>
      <span class="st-k">HUMAN</span><span>${humanState(it.human)}</span>
    </div>
    <div class="btnrow">${btnHTML}</div>
  </div>`;
}

/* ---- Open Positions ---- */
function renderPositions(positions){
  const box = $('att-positions-box');
  if(!positions || !positions.length){
    box.innerHTML = '<div class="mut" style="font-size:12.5px">无持仓记录 — Position 只由用户 ack-buy 建立</div>';
    return;
  }
  box.innerHTML = positions.map(p=>{
    const days = p.entry_date ? Math.max(0, Math.floor((Date.now() - Date.parse(p.entry_date)) / 86400000)) : null;
    return `<div class="action-card"><div class="ac-head">
      <code>${esc(p.symbol)}</code><span class="chip gray">${esc(p.venue||'paper')}</span>
      <span class="num">${fmt(p.shares,0)}股</span>
      <span class="dim">entry ${fmt(p.entry_price)}</span>
      ${p.price!=null?`<span class="num">现价 ${fmt(p.price)}</span>`:''}
      ${p.pnl!=null?`<span class="num" style="color:${p.pnl>=0?'var(--green)':'var(--red)'}">P&L ${fmt(p.pnl)}</span>`:''}
      ${days!=null?`<span class="dim">Holding D+${days}</span>`:''}
      <span class="chip ${p.state==='EXIT_ALERT'?'EXIT':'gray'}">${esc(p.state||'?')}</span>
    </div>
    ${p.exit_reason?`<div class="rf">exit_rule: ${esc(p.exit_reason)}</div>`:''}
    <div class="btnrow">
      <button class="btn primary" data-act="ack-sell" data-symbol="${esc(p.symbol)}" data-venue="${esc(p.venue||'paper')}" data-shares="${esc(p.shares)}" data-price="${esc(p.price??'')}">Paper Sell</button>
      <button class="btn danger" data-act="ack-sell" data-symbol="${esc(p.symbol)}" data-venue="real" data-shares="${esc(p.shares)}" data-price="${esc(p.price??'')}">Record Real Sell</button>
      <button class="btn" data-act="ask" data-symbol="${esc(p.symbol)}">Ask Agent</button>
    </div></div>`;
  }).join('');
}

/* ---- trade modal (canonical ack POST; the server never invents fields) ---- */
let tmKind = 'ack-buy';
function openTrade(kind, symbol, venue, shares, price){
  tmKind = kind;
  $('tm-title').textContent = kind === 'skip' ? '记录 SKIP 决定' : (kind === 'ack-buy' ? `记录买入 — ${symbol||''}` : `记录卖出（全仓平仓）— ${symbol||''}`);
  $('tm-symbol').value = symbol || '';
  $('tm-shares').value = shares || '';
  $('tm-shares').parentElement.style.display = kind === 'skip' ? 'none' : '';
  $('tm-price').value = price || '';
  if(venue) $('tm-venue').value = venue;
  $('tm-venue').parentElement.style.display = kind === 'skip' ? 'none' : '';
  $('tm-time').value = new Date().toISOString();
  $('tm-note').value = '';
  $('tm-msg').textContent = '';
  $('tm-msg').style.color = '';
  $('trade-modal').hidden = false;
}
async function submitTrade(){
  const payload = {
    symbol: $('tm-symbol').value.trim(),
    executed_at: $('tm-time').value.trim(),
    note: $('tm-note').value.trim(),
  };
  if(tmKind === 'skip'){
    payload.price = parseFloat($('tm-price').value);
  } else {
    payload.shares = parseInt($('tm-shares').value, 10);
    payload.price = parseFloat($('tm-price').value);
    payload.venue = $('tm-venue').value;
  }
  const msg = $('tm-msg');
  msg.textContent = '记录中…'; msg.style.color = 'var(--mut)';
  try{
    const r = await fetch('/api/quant/' + tmKind, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    const j = await r.json().catch(()=>({}));
    if(r.ok){
      msg.style.color = 'var(--green)';
      msg.textContent = '已记录到 canonical trading state: ' + JSON.stringify(j);
      pollNow();
    } else {
      msg.style.color = 'var(--red)';
      msg.textContent = '拒绝: ' + (j.error || ('http ' + r.status)) + '（canonical host 规则原样返回，未被 API 覆盖）';
    }
  }catch(e){
    msg.style.color = 'var(--red)';
    msg.textContent = '无法连接 quant_serve — 记录交易需运行: python3 tools/quant_serve.py（静态文件模式不产生任何写入）';
  }
}

/* ---- 今日事件时间线: durable alerts only ---- */
function renderTimeline(rows){
  rows = rows || [];
  $('tl-meta').textContent = `durable alerts · ${rows.length} 条真实持久化事件`;
  $('tl-list').innerHTML = rows.length ? rows.map(r=>
    `<li><span class="ts">${esc(String(r.ts||'').slice(5,19))}</span><span><b>${esc(r.type||'')}</b>` +
    (r.symbol?` <code>${esc(r.symbol)}</code>`:'') + ` ${esc(r.what||'')}` +
    (r.price!=null?` · @${esc(r.price)}`:'') + (r.venue?` · ${esc(r.venue)}`:'') +
    (r.why?` <span class="mut">— ${esc(r.why)}</span>`:'') + '</span></li>').join('')
    : '<li class="mut">当日无持久化事件 — 无事件只是没有 material change，不是无活动</li>';
}

async function pollNow(){
  try{
    const r = await fetch('/api/quant/now', {cache:'no-store'});
    const j = await r.json();
    renderNow(j);
    renderPositions(j.positions || []);
    $('now-meta').textContent += ' · 实时已连接';
  }catch(e){
    /* keep the embedded render-time snapshot; degrade visually, never fake live */
    renderNow(D.now || {});
    renderPositions((D.now||{}).positions || []);
    $('now-meta').textContent += ' · server 未连接 — 显示生成时快照';
  }
}

/* button wiring: action cards + position cards share data-act buttons */
document.addEventListener('click', (e)=>{
  const btn = e.target.closest('[data-act]');
  if(!btn) return;
  const act = btn.dataset.act;
  if(act === 'ask'){
    const sym = btn.dataset.symbol || '当前标的';
    const promptText = `分析${sym}：先调用 get_trading_context 读取 canonical trading 事实，再解释当前 deterministic 状态（触发条件、风险、失效条件），区分 Runtime/Agent/Human 三态；不要宣称盈利能力，不要把 SYSTEM_UNAVAILABLE 说成 NO_TRADE。`;
    (navigator.clipboard?.writeText(promptText) || Promise.reject()).then(
      ()=>{ btn.textContent = '已复制提示词'; setTimeout(()=>{btn.textContent='Ask Agent';}, 1500); },
      ()=>{ window.prompt('复制以下提示词发给 Agent:', promptText); });
    return;
  }
  if(act === 'keep'){
    const card = btn.closest('.action-card');
    if(card){ card.style.opacity = '.45'; btn.disabled = true; btn.textContent = 'Watching'; }
    return;
  }
  openTrade(act, btn.dataset.symbol, btn.dataset.venue,
            btn.dataset.shares || '', btn.dataset.price || '');
});
document.addEventListener('click', (e)=>{
  if(e.target.id === 'tm-close'){ $('trade-modal').hidden = true; return; }
  if(e.target.id === 'tm-submit'){ submitTrade(); return; }
  if(e.target.closest('#trade-modal') && !e.target.closest('.modal-box')){ $('trade-modal').hidden = true; }
});
document.addEventListener('keydown', (e)=>{ if(e.key === 'Escape') $('trade-modal').hidden = true; });
setInterval(pollNow, 30000);

/* ---- 真实运行数据趋势: trading artifacts 的忠实投影, 不补曲线不填 0 ---- */
const RT_STATUS_ZH = {
  SCANNED: '已扫描', NO_TRADE: '有效扫描 · 无机会', ALERTS: '需要行动',
  MARKET_CLOSED: '已收盘（无扫描）', SYSTEM_UNAVAILABLE: '系统不可用（≠ NO_TRADE）',
};
const RT_STATUS_COLOR = {
  SCANNED: 'var(--green)', NO_TRADE: 'var(--acc)', ALERTS: 'var(--amber)',
  MARKET_CLOSED: '#8b96a8', SYSTEM_UNAVAILABLE: 'var(--red)',
};
const rtChip = (st) => `<span class="chip" style="color:${RT_STATUS_COLOR[st] || 'var(--mut)'};background:var(--panel2);border:1px solid var(--line2)" title="${esc(st)}">${esc(RT_STATUS_ZH[st] || st || '—')}</span>`;

function renderM1Evidence(m1){
  const box = $('m1-evidence');
  const line = (label, ok, detail, forceText) => {
    const v = forceText ?? (ok ? '有' : '未证明');
    const color = forceText ? 'var(--amber)' : (ok ? 'var(--green)' : 'var(--amber)');
    return `<dt style="min-width:150px">${esc(label)}</dt><dd style="color:${color};font-weight:700">${esc(v)}<span class="dim" style="font-weight:400"> — ${esc(detail||'')}</span></dd>`;
  };
  const fwd = m1.formal_forward_count ?? 0;
  box.innerHTML = [
    line('有效市场数据', !!(m1.market_data_valid||{}).ok, (m1.market_data_valid||{}).detail),
    line('有效单次扫描', !!(m1.single_scan_valid||{}).ok, (m1.single_scan_valid||{}).detail),
    line('连续实时监控', !!(m1.continuous_monitoring||{}).ok, (m1.continuous_monitoring||{}).detail),
    line('正式 forward evidence', null, '正式 forward observation 计数 (trading/forward.json)', String(fwd)),
    `<dt style="min-width:150px">M1 production evidence</dt><dd style="color:var(--amber);font-weight:700">${esc(m1.verdict || 'NO_REAL_EVIDENCE')} <span class="dim" style="font-weight:400">— 按 artifacts 真实状态投影, 不包装成 M1 PASS</span></dd>`,
  ].join('');
}

function renderRealTrendChart(pts){
  const box = $('rt-chart');
  if (!pts.length){
    box.innerHTML = '<div class="empty"><div class="t">无真实运行记录</div><div class="s">trading/soak.jsonl 尚不存在 — monitor 从未运行, 不画任何合成曲线</div></div>';
    return;
  }
  const W=1000, H=210, L=46, R=16, T=14, B=30;
  const X = (i) => pts.length === 1 ? (L + (W-L-R)/2) : L + i*(W-L-R)/(pts.length-1);
  const Y = (v) => T + (1-v)*(H-T-B);           // v = scanned/universe, 0..1
  let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block">`;
  for (let g=0; g<=2; g++){                     // 0% / 50% / 100% grid
    const v=g/2, y=Y(v);
    svg += `<line x1="${L}" y1="${y}" x2="${W-R}" y2="${y}" stroke="#1f2733" stroke-width="1"/>`+
           `<text x="${L-6}" y="${y+4}" fill="#5c6678" font-size="10.5" text-anchor="end">${v*100}%</text>`;
  }
  const scanRatio = (p) => (p.symbols_scanned==null || !p.universe_size) ? null : p.symbols_scanned/p.universe_size;
  // connect only consecutive points where a real scan happened on both sides;
  // MARKET_CLOSED / SYSTEM_UNAVAILABLE gaps stay visually separate, no interpolation
  for (let i=0; i+1<pts.length; i++){
    const a=scanRatio(pts[i]), b=scanRatio(pts[i+1]);
    if (a==null || b==null || pts[i].symbols_scanned<=0 || pts[i+1].symbols_scanned<=0) continue;
    svg += `<line x1="${X(i)}" y1="${Y(a)}" x2="${X(i+1)}" y2="${Y(b)}" stroke="#4cc2ff" stroke-width="1.6" opacity=".85"/>`;
  }
  pts.forEach((p,i)=>{
    const r = scanRatio(p);
    const color = RT_STATUS_COLOR[p.status] || 'var(--mut)';
    const tip = `${p.ts} · ${p.status}\n扫描 ${p.symbols_scanned ?? '缺失'}/${p.universe_size ?? '缺失'} · 事件 ${p.events ?? '缺失'}\n${p.source}`;
    if (r == null){ return; }                   // missing stays missing: no fabricated point
    svg += `<circle cx="${X(i)}" cy="${Y(r)}" r="${(p.events>0)?6:4.5}" fill="${color}" ${p.events>0?`stroke="var(--amber)" stroke-width="2" fill-opacity=".55"`:''}><title>${esc(tip)}</title></circle>`;
    svg += `<text x="${X(i)}" y="${H-10}" fill="#5c6678" font-size="10" text-anchor="middle">${esc(String(p.ts).slice(5,16))}</text>`;
  });
  svg += '</svg>';
  box.innerHTML = `<div class="chart-box">${svg}
    <div class="legend" style="display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:12px;color:var(--mut)">
      ${Object.keys(RT_STATUS_ZH).filter(s=>pts.some(p=>p.status===s)).map(s=>`<span style="display:flex;align-items:center;gap:6px"><i style="width:10px;height:10px;border-radius:50%;display:inline-block;background:${RT_STATUS_COLOR[s]}"></i>${esc(RT_STATUS_ZH[s])}</span>`).join('')}
      <span class="dim">折线只连接相邻两个真实扫描点；MARKET_CLOSED = 收盘无扫描, 不是扫描失败</span>
    </div></div>`;
}

function renderRealTrend(){
  const rt = D.real_trend || {};
  const pts = rt.points || [];
  $('rt-meta').textContent = `真实记录 ${rt.record_count ?? pts.length} 条 · universe ${rt.universe_size ?? '—'} 只 · M1 trading artifacts`;
  renderM1Evidence(rt.m1_evidence || {});
  renderRealTrendChart(pts);
  const fwd = rt.forward || {};
  $('rt-forward').innerHTML = fwd.count
    ? `<b style="color:var(--green)">正式 forward observation：${fwd.count}</b>（已结算 ${fwd.settled ?? 0}）<span class="dim"> — trading/forward.json</span>`
    : `<b style="color:var(--amber)">尚无正式 forward evidence</b><span class="dim"> — 正式 forward observation 0 条 (trading/forward.json)；不显示 0% 胜率, 不以诊断记录代替</span>`;
  const diag = rt.diagnostic_rows || [];
  $('rt-diagnostic').innerHTML = diag.length ? `
    <div class="question" style="margin-bottom:6px;border-left-color:var(--amber)">以下为 <b>diagnostic forward evidence</b> — 来自隔离诊断运行（--state-dir 隔离, trading-diagnostic/），不是正式 forward observation, 不计入策略收益、胜率或已成交记录。</div>
    <div style="overflow-x:auto"><table><thead><tr><th>日期</th><th>代码</th><th>事件</th><th class="num-h">参考价</th><th class="num-h">5日回撤</th><th class="num-h">20日量比</th><th class="num-h">D+1（诊断）</th><th>标记</th></tr></thead><tbody>
    ${diag.map(r=>`<tr>
      <td class="num">${esc(r.day)}</td><td><code>${esc(r.symbol)}</code></td><td><span class="chip gray">${esc(r.state)}</span></td>
      <td class="num">${fmt(r.ref_price)}</td>
      <td class="num">${fmt(r.pullback_5d!=null?r.pullback_5d*100:null,2)}%</td>
      <td class="num">${fmt(r.volume_ratio_20d)}</td>
      <td class="num" style="color:var(--acc)">${r.d1!=null?`${r.d1>=0?'+':''}${(r.d1*100).toFixed(4)}% <span class="dim">(${esc(r.d1_day||'')})</span>`:'<span class="dim">待结算 — 缓存尚无后续日线</span>'}</td>
      <td><span class="chip NEAR">diagnostic</span></td></tr>`).join('')}
    </tbody></table></div>` : '';
  $('rt-rows').innerHTML = pts.length ? pts.map(p=>`<tr>
    <td class="num">${esc(p.ts)}</td><td>${rtChip(p.status)}</td>
    <td class="num">${p.symbols_scanned ?? '—'}</td><td class="num">${p.universe_size ?? '—'}</td>
    <td class="num">${p.events ?? '—'}</td><td class="mut"><code>${esc(p.source||'')}</code></td></tr>`).join('')
    : '<tr><td colspan="6" class="mut">无真实记录 — 运行 python tools/quant_trading_monitor.py session 开始积累</td></tr>';
}


function renderStatic(){
  renderNow(D.now || {});
  renderPositions((D.now||{}).positions || []);
  renderTimeline(D.timeline || []);
  pollNow();
  renderRealTrend();
  $('gen-time').textContent = D.generated_at;
  $('strategy-warning').textContent = '⚠ ' + D.warning;
  $('not-a-buy').textContent = D.not_a_buy_note;
  $('legacy-question').textContent = '“' + D.legacy_question + '”';
  $('legacy-count').textContent = `自选/持仓 ${ (D.legacy_rows||[]).length } 只 — 诊断位, 不是机会宇宙`;
  const k = D.kpi;
  const dec = $('kpi-decision');
  dec.textContent = zh(ACTION_ZH, k.today_decision);
  dec.style.color = k.today_decision==='NOT_RUN_TODAY' ? 'var(--amber)' : 'var(--acc)';
  $('kpi-triggers').textContent = k.live_triggers ?? '—';
  $('kpi-candidates').textContent = k.active_candidates ?? '—';
  $('kpi-settled').textContent = k.forward_settled_trades ?? 0;
  const ev = $('kpi-evidence');
  ev.textContent = zh(EV_ZH, k.strategy_evidence);
  ev.style.color = 'var(--amber)';

  // v3.1 evidence governance
  const v31 = D.v31 || {};
  const rp = (v31.replay || {});
  const shadow = ((v31.regime_shadow || {}).regime || {});
  const s0 = ((v31.s0 || {}).payload || {});
  const skip = s0.skip_analysis || {};
  const position = s0.position_audit || {};
  const regimeColor = {NORMAL:'var(--green)', SELECTIVE:'var(--amber)', DO_NOT_PARTICIPATE:'var(--red)'}[shadow.regime] || 'var(--dim)';
  const stateColor = {BLOCKED:'var(--red)', REJECTED:'var(--red)'}[v31.promotion_state] || 'var(--amber)';
  const replayReasons = (rp.reasons||[]).length ? (rp.reasons||[]).map(x=>`<span class="rf">${esc(x)}</span>`).join(' ') : '—';
  $('v31-summary').innerHTML = `<dl class="kv">
    <dt>严格 PIT 回放</dt><dd>
      <b>${esc(rp.status || 'UNAVAILABLE')}</b> · ${esc(rp.day_count ?? 0)} 天，其中 ${esc(rp.blocked_day_count ?? 0)} 天 blocked ·
      观察 ${esc(rp.observation_count ?? 0)} · live-forward 增量 ${esc(rp.live_forward_increment ?? 0)} ·
      盘中等价 ${rp.intraday_equivalence === true ? '已证明' : '未证明'}
      <div class="dim" style="margin-top:5px">${replayReasons}</div>
    </dd>
    <dt>Market Regime</dt><dd>
      <b style="color:${regimeColor}">${esc(shadow.regime || 'BLOCKED')}</b>
      · participation=${esc(shadow.participation_permission || '—')} · rule=${esc(shadow.regime_rule_version || '—')}
      · as_of=${esc(shadow.regime_as_of || '—')}
      <div class="dim" style="margin-top:5px">${esc((shadow.regime_reason_codes||[]).join('; ') || '缺失所有 PIT 市场特征')}</div>
    </dd>
    <dt>S0 / SKIP 研究</dt><dd>
      positions=${esc(position.positions ?? 0)} (${esc(position.conclusion || 'INSUFFICIENT_EVIDENCE')}) ·
      human observations=${esc(skip.total ?? 0)} · synthetic fills=${esc(skip.synthetic_fills ?? 0)} ·
      conclusion=${esc(skip.conclusion || 'INSUFFICIENT_EVIDENCE')}
    </dd>
    <dt>Experiment</dt><dd>
      id=${esc((v31.experiment||{}).experiment_id || '—')} · variable=${esc(Object.keys((v31.experiment||{}).variable_changes||{})[0] || '—')} ·
      promotion=<b style="color:${stateColor}">${esc(v31.promotion_state)}</b> · production config 不变
      <div class="dim" style="margin-top:5px">${esc(((v31.promotion||{}).reasons||[]).join('; ') || '尚无 promotion decision')}</div>
    </dd>
    <dt>证据边界</dt><dd>replay/shadow/experiment 全部隔离于 production；本卡不显示也不计入 live-forward 收益。</dd>
  </dl>`;
  if (D.data_quality.status !== 'PASS' && D.data_quality.banner){
    $('dq-banner').textContent = 'DATA DEGRADED / 交易可信度受限 — ' + D.data_quality.banner;
    $('dq-banner').style.display = 'block';
  }
  // triggers section
  drawTriggers(D.trigger_rows || [], false);
  $('scan-meta').textContent = D.scan_meta.present
    ? `扫描快照 ${D.scan_meta.as_of||''} · 宇宙 ${D.scan_meta.universe||''} (${D.scan_meta.universe_size??'—'} 只) · 经 /api/scan 实时刷新`
    : '无扫描快照 — 运行 bash tools/quant_daily.sh 或启动 quant_serve.py';

  // opportunity board
  const cols = [
    ['rank','#'], ['symbol','代码'], ['name','名称'], ['industry','行业'], ['tier','分级'],
    ['composite_score','综合'], ['value_score','价值'], ['quality_score','质量'], ['tradeability_score','可交易'],
    ['pe_ttm','PE(TTM)'], ['pb','PB'], ['dividend_yield_pct','股息率%'], ['roe_3y_pct','ROE 3Y%'],
    ['valuation_percentile_3y','3年估值分位'], ['timing_state','时序'], ['reasons','理由'], ['red_flags','红旗'],
  ];
  const numCols = new Set(['rank','composite_score','value_score','quality_score','tradeability_score','pe_ttm','pb','dividend_yield_pct','roe_3y_pct']);
  $('board-head').innerHTML = cols.map(([k,label]) =>
    `<th data-k="${k}" class="${numCols.has(k)?'num-h':''}">${label}</th>`).join('');
  const drawBoard = (rows) => {
    $('board-rows').innerHTML = rows.length ? rows.map(r=>`<tr>
      <td class="num">${r.rank}</td>
      <td><code>${esc(r.symbol)}</code></td><td>${esc(r.name)}</td>
      <td class="mut">${esc(r.industry)}${r.sector_model==='financial'?' <span class="chip gray">金融</span>':''}</td>
      <td><span class="chip ${esc(r.tier)}" data-m="tier">${esc(r.tier)}</span></td>
      <td class="num" style="font-weight:700" data-m="composite_score">${fmt(r.composite_score,1)}</td>
      <td class="num" data-m="value_score">${fmt(r.value_score,1)}</td><td class="num" data-m="quality_score">${fmt(r.quality_score,1)}</td>
      <td class="num" data-m="tradeability_score">${fmt(r.tradeability_score,1)}</td>
      <td class="num" data-m="pe_ttm">${fmt(r.pe_ttm,1)}</td><td class="num" data-m="pb">${fmt(r.pb,2)}</td>
      <td class="num" data-m="dividend_yield_pct">${fmt(r.dividend_yield_pct,2)}</td><td class="num" data-m="roe_3y_pct">${fmt(r.roe_3y_pct,1)}</td>
      <td class="num" data-m="valuation_percentile_3y">${pct(r.valuation_percentile_3y)}</td>
      <td><span class="chip ${esc(r.timing_state)}" data-m="${esc(r.timing_state)}" title="${esc(r.timing_state)}">${esc(zh(TIMING_ZH,r.timing_state))}</span></td>
      <td class="reason">${esc((r.reasons||[]).join('; '))}</td>
      <td class="rf">${esc(zhFlags(r.red_flags))||'—'}</td>
    </tr>`).join('') : '<tr><td colspan="17" class="mut">候选池为空 — 这是数据/覆盖失败状态, 不是"没有机会"的市场结论。运行 uv run --group quant python tools/quant_build_candidates.py</td></tr>';
  };
  let view = (D.board_rows||[]).slice();
  drawBoard(view);
  $('board-meta').textContent = D.snapshot_meta.as_of
    ? `快照 ${D.snapshot_meta.as_of} · 基础池 ${D.snapshot_meta.base_count??'—'} → 合格 ${D.snapshot_meta.eligible_count??'—'} → 候选池 ${D.snapshot_meta.candidate_count??'—'} · 覆盖率 ${pct(D.snapshot_meta.coverage)}`
    : '候选快照缺失 — 先运行 tools/quant_build_candidates.py';
  $('board-head').addEventListener('click', (e)=>{
    const th = e.target.closest('th'); if(!th) return;
    const key = th.dataset.k; if(!key) return;
    const dir = th.dataset.dir === 'asc' ? -1 : 1;
    th.dataset.dir = dir === 1 ? 'asc' : 'desc';
    view.sort((a,b)=>{
      const va=a[key], vb=b[key];
      if (va==null) return 1; if (vb==null) return -1;
      if (typeof va==='number' && typeof vb==='number') return (va-vb)*dir;
      return String(va).localeCompare(String(vb))*dir;
    });
    drawBoard(view);
  });

  // legacy
  $('legacy-rows').innerHTML = (D.legacy_rows||[]).map(r=>{
    const q = r.qualifies_for_pool === true;
    const verdict = q ? '<span class="chip ok">能 — 具备候选资格</span>'
      : '<span class="chip gray">仅存量持仓</span>';
    const weakness = (r.red_flags&&r.red_flags.length) ? zhFlags(r.red_flags)
      : ((r.exclusions&&r.exclusions.length) ? zhFlags(r.exclusions) : '—');
    const qtm = String(r.quote_time||'').match(/^(\d{4})(\d{2})(\d{2})\s?(\d{2})(\d{2})/);
    const qtShort = qtm ? `${qtm[2]}-${qtm[3]} ${qtm[4]}:${qtm[5]}` : '';
    return `<tr>
      <td><code>${esc(r.symbol)}</code></td><td>${esc(r.name||'')}</td>
      <td class="num" id="lp-${esc(r.symbol)}">${fmt(r.price)}${qtShort?`<div class="dim" style="font-size:10.5px">行情 ${qtShort}</div>`:''}</td>
      <td class="num">${fmt(r.composite_score,1)}</td>
      <td class="num">${fmt(r.value_score,1)}</td><td class="num">${fmt(r.quality_score,1)}</td>
      <td>${r.timing_state?`<span class="chip ${esc(r.timing_state)}" title="${esc(r.timing_state)}">${esc(zh(TIMING_ZH,r.timing_state))}</span>`:'—'}</td>
      <td>${verdict}</td>
      <td class="mut">${r.legacy_status==='POOL_QUALIFIED'?'可独立入选':'仅存量持仓'}</td>
      <td class="rf">${esc(weakness)}</td></tr>`;
  }).join('') || '<tr><td colspan="10" class="mut">legacy_watchlist.toml 缺失或为空</td></tr>';

  // strategy evidence
  const s = D.strategy;
  $('strategy-box').innerHTML = `<dl class="kv">
    <dt>状态</dt><dd style="color:var(--amber);font-weight:700">${esc(zh(EV_ZH,s.status))}</dd>
    <dt>历史最佳年化</dt><dd>${fmt(s.best_annualized_pct,2)}% <span class="dim">(重放, 噪声内, 非已证明优势)</span></dd>
    <dt>历史交易笔数</dt><dd>${fmt(s.best_trades,0)}</dd>
    <dt>PIT / 成分偏差</dt><dd>存在 <span class="dim">(今日成员回看历史; 任何盈利声明的前置门)</span></dd>
    <dt>前向观察（正式）</dt><dd>${fmt(s.forward_observations,0)} <span class="dim">(trading/forward.json)</span></dd>
    <dt>前向已结算交易（正式）</dt><dd>${fmt(s.forward_settled,0)}</dd>
    <dt>前向胜率</dt><dd>${s.forward_hit_rate ? '积累足够结算笔数后再计算' : fmt(s.forward_hit_rate,3)}</dd>
  </dl>`;
  $('results-rows').innerHTML = (s.results||[]).map(r=>`<tr>
    <td>${esc(r.label)}</td><td class="num">${fmt(r.annualized_pct,3)}%</td>
    <td class="num">${fmt(r.trades,0)}</td><td class="num">${fmt(r.max_drawdown_pct,2)}%</td>
    <td class="mut">${esc(r.verdict)}</td></tr>`).join('') || '<tr><td colspan="5" class="mut">无评估工件</td></tr>';

  // forward evidence: formal observations (trading/forward.json) + history log
  const f = (D.real_trend||{}).forward || {};
  $('formal-forward').innerHTML = f.count
    ? `<b style="color:var(--green)">正式 forward observation：${f.count}</b>（已结算 ${f.settled??0}）— 明细随正式记录产生后在此展开`
    : `<b style="color:var(--amber)">尚无正式 forward observation</b>（trading/forward.json 为 0 条）— 不显示 0% 胜率, 不以历史日志或诊断记录代替`;  $('obs-rows').innerHTML = (D.obs_rows||[]).length ? D.obs_rows.slice().reverse().map(r=>`<tr>
    <td class="num">${esc(r.date)}</td><td class="num">${esc(r.time)}</td>
    <td class="num">${esc(r.scanned)}</td>
    <td class="num" style="color:${r.triggers&&r.triggers!=='0'?'var(--red)':'var(--dim)'}">${esc(r.triggers)}</td>
    <td><span class="chip ${r.action==='NO_TRADE'?'gray':'B'}" title="${esc(r.action)}">${esc(zh(ACTION_ZH,r.action))}</span></td>
    <td class="mut">${esc(r.note)}</td></tr>`).join('')
    : '<tr><td colspan="6" class="mut">暂无前向观察 — 运行 bash tools/quant_daily.sh 开始积累</td></tr>';

  // data quality
  const q = D.data_quality;
  const deg = (q.degradations||[]);
  const dims = q.dimensions||{};
  const DIM_STYLE = {PASS:['var(--green)','PASS'],WARN:['#b58900','WARN'],FAIL:['var(--red)','FAIL'],UNKNOWN:['var(--dim)','UNKNOWN']};
  const badge = (k,label)=>{const d=dims[k]||{};const c=DIM_STYLE[d.status]||DIM_STYLE.UNKNOWN;
    return `<span title="${esc(d.detail||'')}" style="font-weight:700;color:${c[0]}">${label} ${c[1]}</span>`;};
  const AL_VERDICT = (D.anti_leakage||{}).verdict;
  const AL_STYLE = {P0_4_SCOPED_PASS:['var(--green)','SCOPED PASS'],P0_4_FAIL:['var(--red)','FAIL'],P0_4_UNKNOWN:['var(--dim)','UNKNOWN']};
  const al = AL_STYLE[AL_VERDICT]||AL_STYLE.P0_4_UNKNOWN;
  $('dq-box').innerHTML = `<dl class="kv">
    <dt>数据质量分维</dt><dd>${badge('coverage','覆盖')} · ${badge('freshness','新鲜')} · ${badge('semantic_integrity','语义')} · ${badge('source_degradation','源')} · ${badge('pit','PIT')} · <span title="anti-leakage 行为验证：删除未来数据不得改变过去结果" style="font-weight:700;color:${al[0]}">防前视 ${al[1]}</span> <span class="dim">分维各自判定；覆盖率 100% 不等于整体可信 (spec P0.2)</span></dd>
    <dt>候选快照时间</dt><dd>${esc(q.snapshot_as_of||'—')} ${q.degraded?'<span class="chip bad">已降级</span>':''}</dd>
    <dt>行情时间</dt><dd>${esc(q.quote_as_of||'—')}</dd>
    <dt>财报数据源</dt><dd>${esc(q.financial_source||'—')} · 最新报告期 ${esc(q.financial_latest_report||'—')} · 取数 ${esc((q.financial_retrieved_at||'').slice(0,19))}</dd>
    <dt>估值来源</dt><dd>${esc(q.valuation_source||'—')}</dd>
    <dt>报价来源</dt><dd>${esc(q.quotes_source||'—')}</dd>
    <dt>必要字段覆盖率</dt><dd style="color:${q.coverage!=null&&q.coverage>=0.8?'var(--green)':'var(--red)'};font-weight:700">${pct(q.coverage)} ${(dims.coverage||{}).status==='WARN'?'<span class="chip bad">低于阈值 — A 级完整性不作声明</span>':''}</dd>
    <dt>行业集中度</dt><dd>${q.concentration==='enforced'?'已强制约束':(q.concentration==='unknown'?'未知':'—')} <span class="dim">(前 30 名内每个一级行业 ≤ 4 只; 行业数据缺失时如实标记"未知", 不假装分散)</span></dd>
    <dt>降级/失败来源</dt><dd>${deg.length? deg.map(d=>`<span class="rf">${esc(d.source||'')}: ${esc((d.error||'').slice(0,80))}</span>`).join('<br>') : '—'}</dd>
  </dl>`;
}

/* live polling: deterministic scan + legacy watchlist quotes */
function applyScan(s){
  if ((s.volume_semantics||{}).status !== 'PASS'){
    $('dq-banner').textContent = '交易可信度受限 — 成交量语义未通过，实时触发已关闭';
    $('dq-banner').style.display = 'block';
  }
  $('kpi-triggers').textContent = (s.triggers||[]).length;
  const trs = (s.triggers||[]).map(t=>{
    const cand = (D.board_rows||[]).find(c=>c.symbol===t.symbol) || {};
    return {symbol:t.symbol, name:t.name||cand.name||'', industry:cand.industry||'—',
      price:t.price, value_score:cand.value_score, quality_score:cand.quality_score,
      composite_score:cand.composite_score, pullback_5d:t.pullback_5d, volume_ratio_20d:t.volume_ratio_20d,
      trigger_time:t.quote_time||'', agent_action:null,
      red_flags:cand.red_flags||[]};
  });
  drawTriggers(trs, true);
}
async function poll(url){
  const r = await fetch(url, {cache:'no-store'});
  if(!r.ok) throw new Error('http '+r.status);
  return r.json();
}
async function pollScan(){
  try{
    const s = await poll('/api/scan');
    if(s.error) throw new Error(s.error);
    applyScan(s);
    $('scan-meta').textContent = `实时连接正常 · ${s.as_of||''} · ${s.universe||''} (${s.universe_size??'—'} 只)`;
  }catch(e){
    $('dq-banner').textContent = '实时连接失效 — 页面保留的扫描结果可能已经过期，不可视为当前信号';
    $('dq-banner').style.display = 'block';
    $('scan-meta').textContent = '实时连接失效 / 数据可能过期';
  }
}
async function pollWatchlist(){
  try{
    const s = await poll('/api/watchlist');
    (s.quotes||[]).forEach(q=>{
      const el = document.getElementById('lp-'+q.symbol);
      if(el && q.price!=null) el.textContent = Number(q.price).toFixed(2);
    });
  }catch(e){ /* prices stay from snapshot */ }
}
document.addEventListener('DOMContentLoaded', ()=>{
  renderStatic();
  renderGlossary();
  pollScan(); pollWatchlist();
  setInterval(pollScan, 60000);
  setInterval(pollWatchlist, 300000);
});
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the quant business dashboard.")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output html path")
    args = ap.parse_args()
    data = build_data()
    html = render_html(data)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    workspace_copy = BUSINESS_ART / "business.html"
    BUSINESS_ART.mkdir(parents=True, exist_ok=True)
    workspace_copy.write_text(html, encoding="utf-8")
    kpi = data["kpi"]
    rt = data["real_trend"]
    dims = data["data_quality"].get("dimensions") or {}
    dim_summary = " ".join(f"{k}={v['status']}" for k, v in dims.items())
    print(
        f"OK -> {out} ({out.stat().st_size / 1024:.1f} KB, also {workspace_copy}); "
        f"decision={kpi['today_decision']} triggers={kpi['live_triggers']} "
        f"candidates={kpi['active_candidates']} evidence={kpi['strategy_evidence']} "
        f"real_records={rt['record_count']} forward={rt['forward']['count']} "
        f"m1={rt['m1_evidence']['verdict']} "
        f"dq_status={data['data_quality']['status']} ({dim_summary})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
