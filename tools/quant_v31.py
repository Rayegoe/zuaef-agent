"""v3.1 文件研究适配器：严格 replay、shadow、实验记录；无网络或生产写入。

历史输入是 JSON：calendar 为真实交易日；records 为带 kind、symbol、
event_time、available_at、source、revision_state 和 payload 的证据行。
candidate payload 必须有 symbols、valid_for 与 frozen=true；daily payload
使用既有 OHLCV 字段；quote 使用生产 quote 字段；semantics payload 有 status。
没有历史归档时，CLI 只利用真实 cache 的日期列选择窗口，逐日报告缺失。
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
from datetime import datetime
from pathlib import Path
from statistics import mean

import pandas as pd
import quant_trading_monitor as monitor
from quant_core import StrategySpec, load_config
from quant_live_scan import timing_from_quote_hist

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "workspace/artifacts/quant/v31"
NAMESPACES = {"research", "replay", "shadow", "live_forward"}
TRUST = ("coverage", "freshness", "semantic_integrity", "source_integrity",
         "pit_integrity", "timing_integrity", "runtime_availability")
RULE_VERSION = "regime-shadow-v1"


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value if not value.endswith("Z") else value[:-1] + "+00:00")
    if result.tzinfo is None:
        raise ValueError("TIMEZONE_UNKNOWN")
    return result.astimezone(monitor.TZ_SH)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_once(path: Path, value) -> None:
    """不可覆盖结果。目录由调用方限定在隔离研究根下。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, indent=2, allow_nan=False)
        file.write("\n")


def run_directory(root: Path, namespace: str, run_id: str) -> Path:
    if namespace not in NAMESPACES - {"live_forward"}:
        raise ValueError("研究适配器不能写 live_forward")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", run_id):
        raise ValueError("INVALID_RUN_ID")
    root = root.resolve()
    production = (ROOT / "workspace/artifacts/quant/trading").resolve()
    if root == production or production in root.parents or root in production.parents:
        raise ValueError("PRODUCTION_PATH_FORBIDDEN")
    target = root / namespace / run_id
    # Resolve existing symlink ancestors before any store can be created.
    if not target.resolve().is_relative_to(root):
        raise ValueError("OUTPUT_ESCAPE")
    target.mkdir(parents=True, exist_ok=False)
    return target


def evidence(namespace: str, kind: str, as_of: str, source: str, payload: dict) -> dict:
    if namespace not in NAMESPACES:
        raise ValueError("INVALID_NAMESPACE")
    return {"schema_version": 1, "namespace": namespace, "created_at": as_of,
            "as_of": as_of, "kind": kind, "source": source, "payload": payload}


def availability_reason(record: dict, now: datetime) -> str | None:
    """先检查元数据；拒绝的 payload 不进入任何 evaluator。"""
    if not record.get("source"):
        return "SOURCE_UNKNOWN"
    if not record.get("available_at"):
        return "AVAILABILITY_UNKNOWN"
    try:
        available = timestamp(record["available_at"])
        event = timestamp(record["event_time"])
        if available > now:
            return "AVAILABLE_AFTER_DECISION"
        if event > now:
            return "EVENT_AFTER_DECISION"
        if available < event:
            return "AVAILABILITY_BEFORE_EVENT"
        if record.get("revision_state") not in {"original", "as_of_revision"}:
            return "REVISION_UNKNOWN"
        if record.get("revision_state") == "as_of_revision" and not record.get("revision_available_at"):
            return "REVISION_AVAILABILITY_UNKNOWN"
        if record.get("revision_available_at") and timestamp(record["revision_available_at"]) > now:
            return "REVISION_AFTER_DECISION"
        if record.get("kind") == "daily":
            # Even a malformed provider timestamp cannot expose today's EOD at 10am.
            bar_end = event.replace(hour=15, minute=0, second=0, microsecond=0)
            if bar_end > now or available < bar_end:
                return "INCOMPLETE_EOD_BAR"
    except (ValueError, TypeError, KeyError):
        return "INVALID_TIME"
    return None


class PITAdapter:
    """生产 run_cycle 的窄数据平面；不修改模块全局或生产配置。"""
    def __init__(self, records: list[dict], now: datetime):
        self.now = now
        self.accepted = []
        self.rejected = []
        for record in records:
            reason = availability_reason(record, now)
            if reason:
                self.rejected.append({"kind": record.get("kind"), "symbol": record.get("symbol"),
                                      "reason": reason})
            else:
                self.accepted.append(record)

    def rows(self, kind: str, symbol: str | None = None) -> list[dict]:
        return sorted((r for r in self.accepted if r.get("kind") == kind
                       and (symbol is None or r.get("symbol") == symbol)),
                      key=lambda r: timestamp(r["available_at"]))

    def resolve_universe(self) -> dict:
        day = self.now.date().isoformat()
        candidates = [r for r in self.rows("candidate")
                      if r["payload"].get("valid_for") == day and r["payload"].get("frozen") is True]
        if not candidates:
            raise ValueError("HISTORICAL_CANDIDATE_UNAVAILABLE")
        record = candidates[-1]
        symbols = record["payload"].get("symbols", [])
        if not symbols or len(set(symbols)) != len(symbols):
            raise ValueError("HISTORICAL_CANDIDATE_INVALID")
        return {"symbols": symbols, "as_of": record["available_at"], "source": record["source"],
                "source_path": record.get("lineage", record["source"])}

    def fetch_batch_quotes(self, symbols: list[str]) -> dict:
        quotes = {}
        for symbol in symbols:
            rows = self.rows("quote", symbol)
            if not rows:
                quotes[symbol] = None
                continue
            row = rows[-1]
            quote = row["payload"]
            try:
                quote_time = timestamp(f"{quote['date'][:4]}-{quote['date'][4:6]}-{quote['date'][6:8]}T{quote['time']}+08:00")
                fresh = 0 <= (self.now - quote_time).total_seconds() <= 60
                consistent = quote_time == timestamp(row["event_time"])
                numeric = all(math.isfinite(float(quote[k])) for k in ("price", "prev_close", "volume"))
            except (ValueError, TypeError, KeyError):
                fresh = consistent = numeric = False
            quotes[symbol] = copy.deepcopy(quote) if fresh and consistent and numeric else None
        return quotes

    def read_cache(self, kind: str, key: str):
        symbol = key.split("_")[0]
        by_day = {}
        for row in self.rows(kind, symbol):
            payload = row["payload"]
            day = payload.get("date")
            if day != timestamp(row["event_time"]).date().isoformat():
                continue
            if day >= self.now.date().isoformat():
                continue  # Both entry and position exits use completed prior sessions.
            by_day[day] = payload
        if not by_day:
            return None, None
        return pd.DataFrame([by_day[d] for d in sorted(by_day)]), {"pit_status": "PASS"}

    def preflight(self, position_symbols=()) -> tuple[list[str], str]:
        reasons = []
        try:
            universe = self.resolve_universe()
            symbols = universe["symbols"]
        except ValueError as exc:
            universe = None
            symbols = []
            reasons.append(str(exc))
        symbols = sorted(set(symbols) | set(position_symbols))
        quotes = self.fetch_batch_quotes(symbols)
        if not self.rows("quote"):
            reasons.append("HISTORICAL_QUOTE_ARCHIVE_UNAVAILABLE")
        for symbol in symbols:
            quote = quotes.get(symbol)
            if quote is None:
                reasons.append(f"QUOTE_MISSING_OR_STALE:{symbol}")
                continue
            hist, _ = self.read_cache("daily", f"{symbol}_qfq")
            if hist is None or timing_from_quote_hist(quote, hist) is None:
                reasons.append(f"PIT_HISTORY_INSUFFICIENT:{symbol}")
        semantics = self.rows("semantics")
        matched = [r for r in semantics if universe
                   and sorted(r["payload"].get("symbols", [])) == sorted(universe["symbols"])
                   and r["payload"].get("universe_as_of") == universe["as_of"]]
        semantic = matched[-1]["payload"].get("status", "UNKNOWN") if matched else "UNKNOWN"
        if semantic != "PASS":
            reasons.append("HISTORICAL_VOLUME_SEMANTICS_UNPROVEN")
        return reasons, semantic


def outcome(observation: dict, namespace: str, run_id: str, strategy_version: str,
            bars: pd.DataFrame | None = None) -> dict:
    values = monitor.forward_math(bars, observation["day"], observation["ref_price"]) if bars is not None else {}
    values = {**observation, **values}
    fields = {f"d{n}": values.get(f"d{n}") for n in monitor.FORWARD_HORIZONS}
    present = sum(value is not None for value in fields.values())
    return {"observation_id": observation.get("ref_id") or f"{observation['symbol']}:{observation['day']}:{observation['kind']}",
            "namespace": namespace, "decision_time": observation.get("decision_time", observation["day"]),
            "symbol": observation["symbol"], "state": observation["kind"],
            "human_action": "SKIPPED" if observation["kind"] == "SKIP" else
                            "EXECUTED" if observation["kind"] in {"EXECUTED", "CLOSED"} else "NONE",
            **fields, "mfe": values.get("mfe_5d"), "mae": values.get("mae_5d"),
            "settlement_state": "SETTLED" if present == 4 else "PARTIAL" if present else "PENDING",
            "strategy_version": strategy_version, "run_id": run_id}


def replay(bundle: dict, cfg: dict, strategy_version: str, root: Path, run_id: str,
           days: int = 10) -> dict:
    directory = run_directory(root, "replay", run_id)
    store = monitor.Store(directory / "state")
    spec = StrategySpec.from_config(cfg)
    calendar = sorted(set(bundle["calendar"]))[-days:]
    if not calendar:
        raise ValueError("TRADING_CALENDAR_EMPTY")
    records = bundle.get("records", [])
    reports = []
    for day in calendar:
        # Archived quote times select a bounded diagnostic cadence, never fabricate ticks.
        points = sorted({timestamp(r["event_time"]).isoformat() for r in records
                         if r.get("kind") == "quote" and str(r.get("event_time", ""))[:10] == day})
        points = points or [f"{day}T10:00:00+08:00"]
        daily = {"namespace": "replay", "day": day, "candidate_reconstruction": "BLOCKED",
                 "observation_count": 0, "transitions": [], "decisions": [], "blocked_reasons": [],
                 "degraded_reasons": ["BOUNDED_ARCHIVE_CADENCE_NOT_FULL_INTRADAY_EQUIVALENCE"],
                 "trust": {key: "UNKNOWN" for key in TRUST}, "outcomes": [],
                 "d1": None, "d3": None, "d5": None, "d8": None, "mfe": None, "mae": None,
                 "settlement_state": "PENDING", "runtime_status": "PIT_BLOCKED"}
        for point in points:
            clock = timestamp(point)
            adapter = PITAdapter(records, clock)
            reasons, semantic = adapter.preflight(p["symbol"] for p in store.positions["open"])
            daily["rejected_evidence"] = adapter.rejected
            try:
                universe = adapter.resolve_universe()
                daily["candidate_reconstruction"] = "FROZEN_HISTORICAL_HANDOFF"
                daily["candidate_source"] = universe
            except ValueError:
                pass
            if reasons:
                daily["blocked_reasons"].extend(reasons)
                daily["decisions"].append({"at": point, "decision": "DATA_UNTRUSTED", "reasons": reasons})
                daily["trust"]["pit_integrity"] = "FAIL"
                continue
            result = monitor.run_cycle(store, active_cfg=copy.deepcopy(cfg), spec=spec,
                                       state_dir=store.dir, now=clock, semantic_status=semantic,
                                       data_adapter=adapter)
            daily["runtime_status"] = result["status"]
            daily["observation_count"] += result["symbols"]
            daily["transitions"].extend(result["events"])
            daily["trust"] = {"coverage": "PASS", "freshness": "PASS", "semantic_integrity": "PASS",
                              "source_integrity": "UNKNOWN", "pit_integrity": "FAIL" if daily["blocked_reasons"] else "PASS",
                              "timing_integrity": "UNKNOWN", "runtime_availability": "PASS"}
            daily["decisions"].append({"at": point, "decision": result["status"],
                                       "opportunities": copy.deepcopy(store.opportunities)})
        daily["blocked_reasons"] = sorted(set(daily["blocked_reasons"]))
        daily["status"] = "blocked" if not daily["observation_count"] else "partial" if daily["blocked_reasons"] else "completed"
        reports.append(daily)
    # Settlement is a separate as-of read, with the same production forward_math.
    settle_at = timestamp(bundle.get("settlement_as_of", f"{calendar[-1]}T23:59:59+08:00"))
    settlement = PITAdapter(records, settle_at)
    outcomes = []
    for obs in store.forward["observations"]:
        # End-of-day settlement may use today's completed bar; entry never does.
        rows = {}
        for r in settlement.rows("daily", obs["symbol"]):
            if r["payload"].get("date") == timestamp(r["event_time"]).date().isoformat():
                rows[r["payload"]["date"]] = r["payload"]
        bars = pd.DataFrame(list(rows.values())) if rows else None
        outcomes.append(outcome(obs, "replay", run_id, strategy_version, bars))
    for daily in reports:
        daily["outcomes"] = [o for o in outcomes if o["decision_time"][:10] == daily["day"]]
    report = evidence("replay", "production_monitor_replay", settle_at.isoformat(),
                      bundle.get("source", "explicit_archive"),
                      {"days": reports, "strategy_version": strategy_version, "config": cfg,
                       "cache_source": {"pit_status": "NON_PIT_FOR_HISTORICAL_REPLAY",
                                        "meta": bundle.get("cache_source"),
                                        "calendar_limitation": "OBSERVED_CACHE_DATES_ARE_NOT_AVAILABILITY_TIMESTAMPS"},
                       "current_candidate_snapshot": bundle.get("current_candidate_snapshot"),
                       "cadence": "bounded_archive_diagnostic", "intraday_equivalence": False,
                       "outcomes": outcomes, "live_forward_increment": 0,
                       "status": "blocked" if all(d["status"] == "blocked" for d in reports) else "partial",
                       "limitations": ["缺少 tick 的日期禁止解释为 NO_TRIGGER；诊断 cadence 不证明完整盘中等价。"]})
    write_once(directory / "report.json", report)
    return report


def local_bundle(cache: Path, end: str, candidate_path: Path | None = None) -> dict:
    """Ground a diagnostic bundle in real cache dates without inventing PIT truth.

    Cache `retrieved_at` and a current candidate snapshot are authoritative
    retrieval facts, not historical publication facts.  Therefore they are not
    converted into records; the replay must fail closed until an explicit
    point-in-time archive supplies `available_at` and historical membership.
    """
    bars = pd.read_csv(cache, usecols=["date"])
    calendar = sorted({str(d)[:10] for d in bars["date"] if str(d)[:10] <= end})
    if len(calendar) < 10:
        raise ValueError("TRADING_CALENDAR_INSUFFICIENT")
    candidate = load_json(candidate_path) if candidate_path else load_json(
        ROOT / "data/quant-cache/candidates/active_symbols.json")
    cache_meta = load_json(cache.with_suffix(".meta.json")) if cache.with_suffix(".meta.json").exists() else None
    return {
        "calendar": calendar[-10:],
        "records": [],
        "source": str(cache),
        "cache_source": cache_meta,
        "current_candidate_snapshot": {
            "path": str(candidate_path or ROOT / "data/quant-cache/candidates/active_symbols.json"),
            "as_of": candidate.get("as_of"),
            "count": candidate.get("count"),
            "pit_status": "NON_PIT_FOR_HISTORICAL_REPLAY",
        },
        "limitations": [
            "TRADING_CALENDAR_FROM_OBSERVED_CACHE",
            "CANDIDATE_SNAPSHOT_IS_CURRENT_NOT_HISTORICAL_MEMBERSHIP",
            "CACHE_RETRIEVED_AT_IS_NOT_PUBLICATION_AVAILABLE_AT",
        ],
    }


def targeted_evidence(records: list[dict], as_of: str) -> dict:
    now = timestamp(as_of)
    kinds = ("market_breadth", "sector_breadth", "announcement", "corporate_action")
    result = {}
    for kind in kinds:
        rows = []
        for row in records:
            if row.get("kind") != kind:
                continue
            reason = availability_reason(row, now)
            rows.append({"source": row.get("source"), "event_time": row.get("event_time"),
                         "available_at": row.get("available_at"), "revision_state": row.get("revision_state"),
                         "pit_status": "PASS" if reason is None else "NON_PIT",
                         "excluded_reason": reason, "payload": row["payload"] if reason is None else None})
        result[kind] = {"status": "PASS" if any(r["pit_status"] == "PASS" for r in rows) else "NON_PIT",
                        "records": rows, "limitation": None if rows else "SOURCE_UNAVAILABLE"}
    return result


def market_regime(records: list[dict], as_of: str) -> dict:
    adapter = PITAdapter(records, timestamp(as_of))
    required = ("csi300_trend", "csi500_trend", "realized_volatility", "market_breadth",
                "sector_breadth", "turnover_change", "trigger_degradation", "abnormal_trading")
    features, reasons = {}, []
    for name in required:
        rows = adapter.rows(name)
        if rows:
            value = rows[-1]["payload"].get("value")
            if isinstance(value, (int, float)) and math.isfinite(value):
                features[name] = value
        if name not in features:
            reasons.append(f"MISSING_PIT_{name.upper()}")
    if reasons:
        regime = "DO_NOT_PARTICIPATE"
    elif features["abnormal_trading"] or (features["csi300_trend"] < 0 and features["csi500_trend"] < 0 and features["market_breadth"] < .4):
        regime = "DO_NOT_PARTICIPATE"
        reasons = ["ABNORMAL_OR_BROAD_DOWNTREND"]
    elif (features["realized_volatility"] > .03 or features["sector_breadth"] < .5
          or features["turnover_change"] < -.2 or features["trigger_degradation"] > .2
          or min(features["csi300_trend"], features["csi500_trend"]) < 0):
        regime, reasons = "SELECTIVE", ["VOLATILITY_BREADTH_LIQUIDITY_OR_DEGRADATION"]
    else:
        regime, reasons = "NORMAL", ["ALL_SHADOW_INPUTS_NORMAL"]
    return {"namespace": "shadow", "regime": regime, "participation_permission": regime,
            "regime_reason_codes": reasons, "regime_as_of": as_of, "regime_rule_version": RULE_VERSION,
            "mode": "shadow", "as_of": as_of, "reason_codes": reasons, "rule_version": RULE_VERSION,
            "confidence": None, "features": features, "production_effect": False,
            "status": "blocked" if len(features) < len(required) else "completed"}


def position_audit(path: Path) -> dict:
    content = load_json(path)
    positions = content.get("open", []) + content.get("closed", [])
    gaps = [{"id": p.get("id"), "missing": [k for k in ("symbol", "entry_price", "shares", "entry_time", "venue") if p.get(k) is None]}
            for p in positions]
    return {"namespace": "research", "source": str(path), "positions": len(positions),
            "gaps": [g for g in gaps if g["missing"]],
            "conclusion": "INSUFFICIENT_EVIDENCE" if not positions else "COVERED" if not any(g["missing"] for g in gaps) else "GAPS",
            "minute_data": "NOT_ADDED: historical quote cadence required for replay, no archive available"}


def skip_analysis(path: Path) -> dict:
    observations = load_json(path).get("observations", [])
    groups = {"SYSTEM_READY_HUMAN_EXECUTED": [], "SYSTEM_READY_HUMAN_SKIPPED": [],
              "SYSTEM_NEAR_HUMAN_SKIPPED": [], "SYSTEM_EXIT_ALERT_HUMAN_EXECUTED": [], "UNCLASSIFIED": []}
    human_observations = [o for o in observations if o.get("kind") in {"SKIP", "EXECUTED", "CLOSED"}]
    for obs in human_observations:
        kind, state = obs.get("kind"), obs.get("opportunity_state")
        label = "UNCLASSIFIED"
        if kind == "EXECUTED":
            label = "SYSTEM_READY_HUMAN_EXECUTED" if state == "READY" else "UNCLASSIFIED"
        elif kind == "SKIP" and state in {"READY", "NEAR"}:
            label = f"SYSTEM_{state}_HUMAN_SKIPPED"
        elif kind == "CLOSED" and obs.get("exit_alert"):
            label = "SYSTEM_EXIT_ALERT_HUMAN_EXECUTED"
        groups[label].append(obs)
    metrics = {}
    for label, rows in groups.items():
        settled = [r for r in rows if r.get("d5") is not None]
        values = [r["d5"] for r in settled]
        metrics[label] = {"count": len(rows), "settled_d5": len(settled),
                          "expectancy_d5": mean(values) if values else None,
                          "tail_loss_d5": min(values) if values else None,
                          "mfe": mean([r["mfe_5d"] for r in settled if r.get("mfe_5d") is not None]) if any(r.get("mfe_5d") is not None for r in settled) else None,
                          "mae": mean([r["mae_5d"] for r in settled if r.get("mae_5d") is not None]) if any(r.get("mae_5d") is not None for r in settled) else None}
    return {"namespace": "research", "source_namespace": "live_forward", "source": str(path),
            "groups": metrics, "total": len(human_observations), "non_human_observations": len(observations) - len(human_observations), "synthetic_fills": 0,
            "conclusion": "INSUFFICIENT_EVIDENCE", "limitations": ["未知原机会状态不推断为 READY；解释改善决策尚无对照证据。"]}


def degradation_metrics(outcomes: list[dict]) -> dict:
    groups = {}
    for row in outcomes:
        key = f"{row['namespace']}:{row.get('regime', 'UNKNOWN')}"
        groups.setdefault(key, []).append(row)
    metrics = {}
    for key, rows in groups.items():
        valid = [r for r in rows if r.get("d5") is not None]
        split = len(valid) // 2
        earlier, later = valid[:split], valid[split:]
        avg = lambda values: mean([r["d5"] for r in values]) if values else None
        suppressed = [r for r in valid if r.get("participation_permission") == "DO_NOT_PARTICIPATE"]
        metrics[key] = {"count": len(rows), "settled_d5": len(valid), "expectancy_d5": avg(valid),
                        "degradation_d5": avg(earlier) - avg(later) if earlier and later else None,
                        "avoided_loss_d5": sum(-r["d5"] for r in suppressed if r["d5"] < 0) if suppressed else None,
                        "suppressed_opportunity_d5": sum(r["d5"] for r in suppressed if r["d5"] > 0) if suppressed else None}
    return {"namespace": "research", "groups": metrics, "conclusion": "INSUFFICIENT_EVIDENCE" if not metrics else "DESCRIPTIVE_ONLY"}


class Experiments:
    """文件治理；关联既有 evaluator/reconciliation，不提供第二 evaluator。"""
    def __init__(self, root: Path):
        self.root = root

    def propose(self, proposal: dict) -> Path:
        required = ("experiment_id", "hypothesis", "baseline_version", "change", "mechanism",
                    "data_window", "primary_metric", "risk_metric", "rejection_condition", "variable_changes")
        if any(not proposal.get(k) for k in required) or len(proposal["variable_changes"]) != 1:
            raise ValueError("PRESTATED_ONE_VARIABLE_HYPOTHESIS_REQUIRED")
        directory = run_directory(self.root, "research", proposal["experiment_id"])
        write_once(directory / "proposal.json", {**proposal, "state": "PROPOSED", "evidence_namespace": "research", "run_ids": [], "limitations": []})
        return directory

    def record(self, directory: Path, stage: str, result: dict, source_paths: list[Path]) -> dict:
        namespaces = {"S0_DIAGNOSIS": "research", "RESEARCH_EVAL": "research", "S1_REPLAY": "replay",
                      "S2_SHADOW": "shadow", "LIVE_FORWARD_EVAL": "live_forward"}
        if stage not in namespaces:
            raise ValueError("INVALID_STAGE")
        proposal = load_json(directory / "proposal.json")
        sources = []
        for path in source_paths:
            data = load_json(path)
            namespace = data.get("namespace", "research")
            if namespace != namespaces[stage]:
                raise ValueError("EVIDENCE_NAMESPACE_MISMATCH")
            sources.append({"path": str(path), "namespace": namespace,
                            "original_window": data.get("data_window", data.get("window", data.get("period", data.get("config", {}))))})
        record = {**proposal, "state": stage, "evidence_namespace": namespaces[stage],
                  "result": result, "sources": sources, "run_ids": [str(p) for p in source_paths]}
        write_once(directory / f"{stage}.json", record)
        return record

    def decide(self, directory: Path, action: str, reason: str) -> dict:
        if action not in {"promote", "reject"}:
            raise ValueError("INVALID_DECISION")
        # This adapter never changes active.toml. Live-forward admission is explicitly reviewed.
        if action == "promote":
            needed = ("S1_REPLAY", "S2_SHADOW", "LIVE_FORWARD_EVAL")
            missing = [s for s in needed if not (directory / f"{s}.json").exists()]
            reasons = [f"MISSING_{s}" for s in missing]
            for stage in needed:
                path = directory / f"{stage}.json"
                if path.exists():
                    record = load_json(path)
                    if record["result"].get("verdict") != "PASS" or not record["sources"]:
                        reasons.append(f"UNPROVEN_{stage}")
            # No self-attested research result can authorize real promotion.
            reasons.append("NEW_LIVE_FORWARD_AND_ZERO_UNRESOLVED_INTEGRITY_FAILURES_REQUIRE_REVIEW")
            result = {"state": "BLOCKED", "requested_action": action, "reasons": reasons}
        else:
            result = {"state": "REJECTED", "requested_action": action, "reasons": [reason]}
        result.update({"namespace": "research", "production_config_changed": False})
        write_once(directory / "decision.json", result)
        return result


def shadow(bundle: dict, as_of: str, root: Path, run_id: str) -> dict:
    directory = run_directory(root, "shadow", run_id)
    report = evidence("shadow", "market_regime", as_of, bundle.get("source", "explicit_archive"),
                      {"regime": market_regime(bundle.get("records", []), as_of),
                       "evidence": targeted_evidence(bundle.get("records", []), as_of),
                       "canonical_snapshot": {"source": str(ROOT / monitor.STATE_DIR / "state.json"),
                                              "namespace": "live_forward",
                                              "projection": load_json(ROOT / monitor.STATE_DIR / "state.json")},
                       "status": "blocked" if market_regime(bundle.get("records", []), as_of)["status"] == "blocked" else "partial",
                       "broker_effects": 0, "live_forward_increment": 0,
                       "real_session_acceptance": "IMPLEMENTED_NOT_PROVEN"})
    write_once(directory / "report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["replay", "shadow", "research", "experiment"])
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--root", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--as-of", default=datetime.now(monitor.TZ_SH).isoformat(timespec="seconds"))
    parser.add_argument("--cache", type=Path, default=ROOT / "data/quant-cache/daily/601128_qfq.csv")
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / monitor.ACTIVE_STRATEGY)
    parser.add_argument("--strategy-version", default="active-s3-frozen-2026-09-02")
    args = parser.parse_args()
    bundle = load_json(args.archive) if args.archive else local_bundle(
        args.cache, args.as_of[:10], args.candidates)
    cfg = load_config(args.config)
    if args.command == "replay":
        report = replay(bundle, cfg, args.strategy_version, args.root, args.run_id)
    elif args.command == "shadow":
        report = shadow(bundle, args.as_of, args.root, args.run_id)
    elif args.command == "research":
        directory = run_directory(args.root, "research", args.run_id)
        report = evidence("research", "S0_DIAGNOSIS", args.as_of, "canonical_read_only",
                          {"position_audit": position_audit(ROOT / monitor.STATE_DIR / "positions.json"),
                           "skip_analysis": skip_analysis(ROOT / monitor.STATE_DIR / "forward.json"),
                           "degradation": degradation_metrics([])})
        write_once(directory / "report.json", report)
    else:
        registry = Experiments(args.root)
        directory = registry.propose({"experiment_id": args.run_id,
            "hypothesis": "独立 regime shadow 可提示回避损失；未证明前不改变生产。",
            "baseline_version": args.strategy_version, "change": "regime projection OFF -> shadow",
            "mechanism": "用可用时间明确的市场证据生成独立参与建议。",
            "variable_changes": {"regime_projection": ["OFF", "shadow"]},
            "data_window": [bundle["calendar"][0], bundle["calendar"][-1]],
            "primary_metric": "avoided_loss_d5", "risk_metric": "suppressed_opportunity_d5",
            "rejection_condition": "PIT不完整或没有新live-forward，不允许promotion。"})
        registry.record(directory, "S0_DIAGNOSIS", {"verdict": "INSUFFICIENT_EVIDENCE",
                        "positions": position_audit(ROOT / monitor.STATE_DIR / "positions.json"),
                        "skip": skip_analysis(ROOT / monitor.STATE_DIR / "forward.json")}, [])
        evaluator = ROOT / "workspace/artifacts/quant/gen1/evidence.json"
        reconciliation = ROOT / "workspace/artifacts/quant/gen1/p05_reconciliation.json"
        registry.record(directory, "RESEARCH_EVAL", {"verdict": "REUSED_RESEARCH_ONLY",
                        "original_window": ["2018-01-01", "2022-12-31"],
                        "limitations": ["current CSI500 historical application; NON_PIT; no new evaluator run"]},
                        [p for p in (evaluator, reconciliation) if p.exists()])
        replay(bundle, cfg, args.strategy_version, args.root, args.run_id)
        registry.record(directory, "S1_REPLAY", {"verdict": "BLOCKED"}, [args.root / "replay" / args.run_id / "report.json"])
        shadow(bundle, args.as_of, args.root, args.run_id)
        registry.record(directory, "S2_SHADOW", {"verdict": "BLOCKED", "real_session": False}, [args.root / "shadow" / args.run_id / "report.json"])
        report = registry.decide(directory, "promote", "研究不足")
    print(json.dumps({"run_id": args.run_id, "namespace": report["namespace"], "root": str(args.root),
                      "state": report.get("state", report.get("payload", {}).get("status", "completed"))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
