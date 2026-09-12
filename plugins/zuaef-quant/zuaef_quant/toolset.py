"""QuantToolset — the quant domain's model-visible deterministic tools.

Boundary (spec pack 03 §4): the host owns validation, data, evaluator,
market rules, costs and benchmark; the Agent owns interpretation and the
bounded numeric StrategySpec it submits. Strategy children are whitelisted
TOML key/value specs — arbitrary Python never crosses this boundary.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.models import CoreDeps

from . import research as research_store
from . import watchlist as watchlist_store
from .freshness import market_date_of
from .runtime import package_parent, resolve_repo_root
from .trading import read_trading_snapshot

#: Repo/workspace resolution is owned by the stdlib-only runtime helper.
REPO_ROOT = resolve_repo_root()
DEFAULT_BENCH_DIR = REPO_ROOT / "benchmarks" / "quant" / "gen1"
EVAL_TIMEOUT_S = 1200
SCAN_TIMEOUT_S = 300
ACK_TIMEOUT_S = 120
RENDER_TIMEOUT_S = 120
SYMBOL_CONTEXT_TIMEOUT_S = 120
PREWARM_TIMEOUT_S = 300
MKT_INTEL_TIMEOUT_S = 120
MARKET_CONTEXT_TIMEOUT_S = 180
GEN1_DIR = DEFAULT_BENCH_DIR

#: Whitelisted StrategySpec keys (schema 1). Nothing else crosses the boundary.
SPEC_KEYS = {
    "schema",
    "name",
    "universe",
    "max_holding_days",
    "stop_loss_pct",
    "take_profit_pct",
    "position_fraction",
    "max_positions",
    "entry_pullback_max",
    "entry_volume_ratio_min",
}
INT_KEYS = {"max_holding_days", "max_positions"}
FLOAT_KEYS = {
    "stop_loss_pct",
    "take_profit_pct",
    "position_fraction",
    "entry_pullback_max",
    "entry_volume_ratio_min",
}


class SpecError(ValueError):
    """Raised when a submitted strategy spec violates the execution ABI."""


# Terminal Delivery Guard (incident 9c1c9abb / 77c45d0e): a run that ends
# without the model's final reply must not bury an already-recorded decision.
# The reply marker is the domain-owned handoff to the Gateway presentation
# layer: same path and JSON shape are read by
# ``src/zuaef_agent/gateway/service.py`` (_reply_artifact_text). It lives
# under artifacts/ (model write-protected) and carries presentation-ready
# text composed mechanically from the brief fields — never new semantics.
REPLY_MARKER_NAME = "last-reply.json"


def compose_reply_text(record: dict[str, Any]) -> str:
    """Deterministic user-facing text assembled from the model-authored
    brief fields (presentation formatting only, no new judgment)."""
    return (
        f"{record['symbol']}：{record['action']}（{record['strategy_name']}）\n"
        f"{record['why']}\n"
        f"失效条件：{record['invalidation']}\n"
        f"依据：{record['trigger_facts']}"
    )


def _write_reply_marker(
    briefs_dir: Path, decision_id: str, recorded_at: _dt.datetime, record: dict[str, Any]
) -> None:
    """Atomically publish the run's user-facing deliverable pointer.

    The Gateway renders this only when a run ends without the model's reply
    and the marker is fresh for that run (recorded_at >= run start), so a
    stale marker from an earlier run is never re-delivered."""
    marker = {
        "recorded_at": recorded_at.isoformat(),
        "decision_id": decision_id,
        "text": compose_reply_text(record),
    }
    tmp = briefs_dir / f".{REPLY_MARKER_NAME}.tmp"
    tmp.write_text(json.dumps(marker, ensure_ascii=False), encoding="utf-8")
    tmp.replace(briefs_dir / REPLY_MARKER_NAME)


def validate_spec_dict(data: dict[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(data) - SPEC_KEYS)
    if unknown:
        raise SpecError(f"unknown strategy spec keys: {unknown}")
    if not isinstance(data.get("name"), str) or not re.fullmatch(r"[a-z0-9_]{3,40}", data["name"]):
        raise SpecError("name must be 3-40 chars of [a-z0-9_]")
    if data.get("universe") != "csi500_subset":
        raise SpecError("universe must be 'csi500_subset' (the frozen gen1 universe)")
    for key in INT_KEYS:
        if key in data and not isinstance(data[key], int):
            raise SpecError(f"{key} must be an integer")
    for key in FLOAT_KEYS:
        if key in data and not isinstance(data[key], (int, float)):
            raise SpecError(f"{key} must be a number")
    hold = data.get("max_holding_days", 5)
    if not 1 <= int(hold) <= 20:
        raise SpecError("max_holding_days out of range [1, 20]")
    positions = data.get("max_positions", 5)
    if not 1 <= int(positions) <= 20:
        raise SpecError("max_positions out of range [1, 20]")
    fraction = float(data.get("position_fraction", 0.10))
    if not 0.01 <= fraction <= 0.5:
        raise SpecError("position_fraction out of range [0.01, 0.5]")
    stop = float(data.get("stop_loss_pct", 0.03))
    take = float(data.get("take_profit_pct", 0.06))
    if not 0.005 <= stop <= 0.15 or not 0.01 <= take <= 0.5 or take <= stop:
        raise SpecError("need 0.005 <= stop_loss_pct <= 0.15 < take_profit_pct <= 0.5")
    return data


def validate_spec(toml_text: str) -> dict[str, Any]:
    try:
        data = tomllib.loads(toml_text)
    except tomllib.TOMLDecodeError as exc:
        raise SpecError(f"strategy spec is not valid TOML: {exc}") from exc
    return validate_spec_dict(data)


def render_spec_toml(data: dict[str, Any]) -> str:
    """Render a validated spec dict back to canonical TOML text."""
    lines = ["schema = 1"]
    for key in sorted(SPEC_KEYS - {"schema"}):
        if key in data:
            value = data[key]
            lines.append(f'{key} = "{value}"' if isinstance(value, str) else f"{key} = {value}")
    return "\n".join(lines) + "\n"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", name)


def _run_module(module: str, args: list[str], quant_python: Path, timeout: int) -> str:
    """Run one domain-owned side-environment module (same authority as CLI)."""
    env = os.environ.copy()
    previous = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(package_parent()) + (
        os.pathsep + previous if previous else ""
    )
    proc = subprocess.run(
        [str(quant_python), "-m", module, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        cwd=str(REPO_ROOT),
        env=env,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout)[-800:]
        raise RuntimeError(f"quant sidecar run failed ({module}): {tail}")
    return proc.stdout


def _live_scan_payload(quant_python: Path) -> dict[str, Any]:
    """Run the deterministic candidate-pool scan engine once and parse it.

    ``run_live_scan`` calls this function, and the operator CLI executes
    ``zuaef_quant.scan_sidecar`` directly. There is one scan implementation
    authority: production scan runs this domain module in the quant side
    environment.
    """
    stdout = _run_module(
        "zuaef_quant.scan_sidecar",
        ["--max-triggers", "10"],
        quant_python,
        SCAN_TIMEOUT_S,
    )
    raw = stdout.strip().splitlines()[-1] if stdout.strip() else "{}"
    try:
        data = json.loads(raw)
    except ValueError:
        return {
            "evidence_scope": "CANDIDATE_POOL",
            "error": "candidate-pool scan returned unreadable output",
            "raw_tail": stdout[-500:],
        }
    if not isinstance(data, dict):
        return {
            "evidence_scope": "CANDIDATE_POOL",
            "error": "candidate-pool scan returned an unexpected payload",
        }
    data["evidence_scope"] = "CANDIDATE_POOL"
    return data

def make_toolset(*, quant_python: Path, workspace_root: Path) -> AbstractToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset()
    evaluations_used = {"count": 0}

    @toolset.tool_plain
    def evaluate_strategy(
        name: str,
        entry_pullback_max: float = -0.06,
        entry_volume_ratio_min: float = 1.80,
        max_holding_days: int = 5,
        stop_loss_pct: float = 0.03,
        take_profit_pct: float = 0.06,
        position_fraction: float = 0.10,
        max_positions: int = 5,
        window: str = "research",
    ) -> str:
        """Evaluate one strategy child against the frozen benchmark protocol.

        Change exactly ONE numeric field per child versus the baseline
        (defaults below ARE the frozen gen1 baseline). The entry structure is
        host-owned: 5-day pullback depth, 20-day volume ratio, non-negative
        close strength. The host runs the Qlib vector stage plus the
        independent A-share replay (T+1, price limits, suspension, lots,
        commission, stamp duty, slippage) and returns bounded evidence:
        returns, drawdown, trades, costs, blocked fills, cross-engine
        consistency. Evaluation takes a few minutes. ONE evaluation per
        research round: after it returns, write the Strategy Result and end
        the task.
        """
        if evaluations_used["count"] >= 1:
            raise RuntimeError(
                "evaluate_strategy already ran this round: one evaluation per "
                "round — write the Strategy Result from the evidence you have "
                "and end the task"
            )
        evaluations_used["count"] += 1
        data = validate_spec_dict({
            "schema": 1,
            "name": name,
            "universe": "csi500_subset",
            "entry_pullback_max": entry_pullback_max,
            "entry_volume_ratio_min": entry_volume_ratio_min,
            "max_holding_days": max_holding_days,
            "stop_loss_pct": stop_loss_pct,
            "take_profit_pct": take_profit_pct,
            "position_fraction": position_fraction,
            "max_positions": max_positions,
        })
        children = workspace_root / "artifacts" / "quant" / "children"
        children.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now(_dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        child_dir = children / f"{_slug(data['name'])}-{stamp}"
        child_dir.mkdir(parents=True, exist_ok=True)
        strategy_path = child_dir / "strategy.toml"
        strategy_path.write_text(render_spec_toml(data), encoding="utf-8")
        stdout = _run_module(
            "zuaef_quant.eval_sidecar",
            ["--strategy", str(strategy_path), "--out", str(child_dir), "--window", window],
            quant_python,
            EVAL_TIMEOUT_S,
        )
        evidence_path = child_dir / "evidence.json"
        if not evidence_path.exists():
            raise RuntimeError(f"evaluator produced no evidence.json ({stdout[-300:]})")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        # File tools are workspace-relative: hand the model the path WITHOUT
        # the workspace prefix so write_file lands at <workspace>/<path>.
        result_hint = child_dir.relative_to(workspace_root) / "result.md"
        return json.dumps(
            {
                "artifact_dir": str(child_dir),
                "result_file": str(result_hint),
                "window": evidence["window"],
                "intents": evidence["intents"],
                "independent_replay": evidence["independent_replay"],
                "vector_stage": evidence["vector_stage"],
                "blocked_trades": evidence["blocked_trades"],
                "consistency": evidence["consistency"],
                "limitations": [
                    "universe: current CSI500 membership applied to all dates",
                    "research window only; promotion/holdout are host-owned",
                ],
            },
            ensure_ascii=False,
        )

    @toolset.tool_plain(defer_loading=True)
    def run_live_scan() -> str:
        """Explicitly run today's deterministic candidate-pool scan
        (扫描/刷新/重新跑/今天信号/READY/NEAR): scan the resolved active
        universe with the frozen strategy and return bounded triggers,
        timestamps, scan metadata and latency.

        This is the same scan engine the monitor and the operator CLI use.
        Use it when the user asks to refresh today's signals;
        never fall back to shell, repo search or a hand-written script. An
        empty trigger list is a valid NO_TRADE result, not an error.
        """
        data = _live_scan_payload(quant_python)
        data.setdefault("evidence_scope", "CANDIDATE_POOL")
        return json.dumps(data, ensure_ascii=False)

    @toolset.tool_plain
    def record_decision_brief(
        decision_id: str,
        symbol: str,
        action: str,
        signal_timestamp: str,
        why: str,
        invalidation: str,
        expected_holding: str,
        strategy_name: str,
        trigger_facts: str,
    ) -> str:
        """Persist one Decision Brief as a structured record (file-native)
        and return the measured signal→brief latency.

        action must be NO_TRADE | WATCH | ENTER_CANDIDATE | HOLD | REDUCE |
        EXIT. ENTER_CANDIDATE is never an order. signal_timestamp must come
        from the current run's authoritative fresh scan evidence (the
        run_live_scan result), so the host can measure end-to-end decision
        latency. decision_id must be unique, e.g.
        'brief-20260902-1430-600519'.
        """
        actions = {"NO_TRADE", "WATCH", "ENTER_CANDIDATE", "HOLD", "REDUCE", "EXIT"}
        if action not in actions:
            raise ValueError(f"action must be one of {sorted(actions)}")
        if not decision_id or not re.fullmatch(r"[a-zA-Z0-9._-]{6,80}", decision_id):
            raise ValueError("decision_id must be 6-80 chars of [a-zA-Z0-9._-]")
        signal_dt = _dt.datetime.fromisoformat(signal_timestamp)
        if signal_dt.tzinfo is None:
            signal_dt = signal_dt.replace(tzinfo=_dt.timezone(_dt.timedelta(hours=8)))
        brief_dt = _dt.datetime.now(_dt.UTC)
        latency_s = round((brief_dt - signal_dt).total_seconds(), 1)
        record = {
            "decision_id": decision_id,
            "recorded_at": brief_dt.isoformat(),
            "symbol": symbol,
            "action": action,
            "strategy_name": strategy_name,
            "signal_timestamp": signal_dt.isoformat(),
            "brief_latency_seconds": latency_s,
            "why": why,
            "invalidation": invalidation,
            "expected_holding": expected_holding,
            "trigger_facts": trigger_facts,
        }
        briefs = workspace_root / "artifacts" / "quant" / "briefs"
        briefs.mkdir(parents=True, exist_ok=True)
        out = briefs / f"{decision_id}.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_reply_marker(briefs, decision_id, brief_dt, record)
        return json.dumps(
            {
                "recorded": True,
                "file": out.name,
                "signal_to_brief_latency_seconds": latency_s,
                "note": "ENTER_CANDIDATE is a candidate, not an order",
            },
            ensure_ascii=False,
        )

    @toolset.tool_plain
    def record_trade_outcome(
        symbol: str,
        action: str,
        shares: int,
        price: float,
        venue: str,
        executed_at: str,
        notes: str = "",
    ) -> str:
        """Record one human-completed or paper trade FACT into the canonical
        trading state via the canonical ack host operation (LOCAL fact write;
        no broker action is taken and none can be). action must be BUY or
        SELL; venue must be 'paper' or 'real'; executed_at is the human
        fact's own ISO time. BUY creates a Position; SELL closes the FULL
        position only (shares must equal the open position's shares) and its
        venue must match the position's venue — the canonical host rejects
        anything else and this tool surfaces that rejection verbatim.
        """
        if action not in ("BUY", "SELL"):
            raise ValueError("action must be BUY or SELL")
        if venue not in ("paper", "real"):
            raise ValueError("venue must be 'paper' or 'real'")
        if shares <= 0 or price <= 0:
            raise ValueError("shares and price must be positive")
        args = [
            "--state-dir", str(workspace_root / "artifacts" / "quant" / "trading"),
            "ack-buy" if action == "BUY" else "ack-sell",
            "--symbol", symbol.strip().upper(),
            "--price", repr(float(price)),
            "--shares", str(int(shares)),
            "--venue", venue,
            "--time", executed_at,
        ]
        if notes.strip():
            args += ["--note", notes.strip()]
        stdout = _run_module("zuaef_quant.monitor", args, quant_python, ACK_TIMEOUT_S)
        ack = json.loads(stdout.strip() or "{}")
        return json.dumps(
            {
                "recorded": True,
                "canonical": "workspace/artifacts/quant/trading/",
                "ack": ack,
                "note": "human trade fact via canonical ack; no broker action",
            },
            ensure_ascii=False,
        )

    @toolset.tool_plain(defer_loading=True)
    def get_trading_context() -> str:
        """Read the bounded CURRENT trading context (持仓/交易状态/仓位)
        from the canonical M1 artifacts (workspace/artifacts/quant/trading/). Read-only projection:
        never recomputes the market and never re-derives triggers. Returns
        system health, market/data-trust status, READY/NEAR lists, open
        positions, exit alerts, recent durable material events, the
        validation_accounting block (ledger-computed strategy maturity:
        validation ages, observation settlement, per-symbol lifecycle) and
        heartbeat/last-scan times. Freshness is a HOST-derived
        fact (freshness_status/freshness_reason plus the requested/data/scan
        dates): never infer data freshness from dates yourself and never
        interpret READY/NEAR as a current-day result unless
        freshness_status is FRESH. This is the broad mixed compatibility
        projection: for a narrow READY/NEAR, holdings or validation question
        prefer get_signal_board / get_positions / get_validation_status. Base
        the answer on current tool facts instead of memory; a stale context
        is a fact to report, not to refresh by re-scanning.
        """
        snapshot = read_trading_snapshot(workspace_root)
        state = snapshot["state"]
        now = snapshot["now"]
        freshness = snapshot["freshness"]
        validation_accounting = snapshot["validation_accounting"]
        last_scan_at = snapshot["last_scan_at"]
        return json.dumps(
            {
                "present": bool(state),
                "as_of": state.get("as_of"),
                "day": state.get("day"),
                "status": state.get("status"),
                "data_trust": state.get("data_trust") or "UNKNOWN",
                "market_no_trade": state.get("market_no_trade"),
                "system_unavailable": state.get("system_unavailable"),
                "heartbeat_at": snapshot["soak"][-1].get("ts") if snapshot["soak"] else None,
                "last_scan_at": last_scan_at,
                # Evidence scope is first-class: this projection intentionally
                # merges two different scopes, so no single top-level scope may
                # be claimed.  The per-field map is the authorizing boundary.
                "evidence_scope": None,
                "scope_map": {
                    "ready": "CANDIDATE_POOL",
                    "near": "CANDIDATE_POOL",
                    "positions": "TRADING_ACCOUNT",
                    "exit_alerts": "TRADING_ACCOUNT",
                },
                "ready": state.get("ready") or [],
                "near": state.get("near") or [],
                "exit_alerts": state.get("exit_alerts") or [],
                "positions": snapshot["positions"].get("open") or [],
                "recent_material_events": snapshot["events"],
                "validation_accounting": validation_accounting,
                # Freshness contract (Freshness Spec v0.1 §3): host-derived
                # facts the model must read before any "today" claim.
                "requested_at": now.isoformat(),
                "requested_market_date": freshness["requested_market_date"],
                "data_as_of": state.get("as_of"),
                "latest_market_data_date": state.get("day"),
                "last_scan_market_date": (
                    market_date_of(last_scan_at).isoformat()
                    if market_date_of(last_scan_at) is not None
                    else None
                ),
                "market_state": state.get("status"),
                "freshness_status": freshness["freshness_status"],
                "freshness_reason": freshness["freshness_reason"],
                "limitations": [
                    "strategy profitability UNPROVEN (S3 frozen, PIT-contaminated universe)",
                    "READY/NEAR are deterministic facts from the frozen scan rules, not orders",
                    "READY/NEAR are current-day results only when freshness_status is FRESH",
                    "ready/near are CANDIDATE_POOL evidence; positions/exit_alerts are TRADING_ACCOUNT evidence; neither is market-wide evidence",
                ],
            },
            ensure_ascii=False,
        )


    # --- narrow semantic OBSERVE tools (Domain Surface Refoundation P2) -----
    # These intent-oriented projections read the canonical trading artifacts.
    # They are deferred so the initial tool surface stays small; ToolSearch
    # reveals the tool matching the user's vocabulary, and each payload keeps
    # unrelated evidence scopes out of the model context.

    @toolset.tool_plain(defer_loading=True)
    def get_signal_board() -> str:
        """Read today's deterministic opportunity board (今天机会/
        READY/NEAR/盯盘/信号板): candidate-pool readiness, scan freshness
        and scan metadata only.

        Discovery vocabulary: 机会 候选 信号 READY NEAR 盯盘 今天 扫描 新鲜度.
        Evidence scope is CANDIDATE_POOL. READY/NEAR are deterministic scan
        facts, not orders, and are current-day results only when
        freshness_status is FRESH. Positions, holdings, validation and
        market-wide context are deliberately not part of this payload.
        """
        snapshot = read_trading_snapshot(workspace_root)
        state = snapshot["state"]
        freshness = snapshot["freshness"]
        last_scan_at = snapshot["last_scan_at"]
        return json.dumps(
            {
                "present": bool(state),
                "evidence_scope": "CANDIDATE_POOL",
                "as_of": state.get("as_of"),
                "day": state.get("day"),
                "market_state": state.get("status"),
                "data_trust": state.get("data_trust") or "UNKNOWN",
                "market_no_trade": state.get("market_no_trade"),
                "system_unavailable": state.get("system_unavailable"),
                "ready": state.get("ready") or [],
                "near": state.get("near") or [],
                "symbols_scanned": state.get("symbols_scanned"),
                "last_scan_at": last_scan_at,
                "requested_at": snapshot["now"].isoformat(),
                "requested_market_date": freshness["requested_market_date"],
                "latest_market_data_date": state.get("day"),
                "last_scan_market_date": (
                    market_date_of(last_scan_at).isoformat()
                    if market_date_of(last_scan_at) is not None
                    else None
                ),
                "freshness_status": freshness["freshness_status"],
                "freshness_reason": freshness["freshness_reason"],
                "limitations": [
                    "READY/NEAR are CANDIDATE_POOL evidence from the frozen scan rules, not orders",
                    "READY/NEAR are current-day results only when freshness_status is FRESH",
                    "this board says nothing about the user's holdings; use get_positions for that",
                ],
            },
            ensure_ascii=False,
        )

    @toolset.tool_plain(defer_loading=True)
    def get_positions() -> str:
        """Read the bounded current position state (当前持有/持仓/仓位/
        成本/退警): open positions, their live host-projected fields and
        exit alerts only.

        Discovery vocabulary: 当前持有 持仓 仓位 成本 个股 退警 EXIT_ALERT.
        Evidence scope is TRADING_ACCOUNT. This payload says nothing about
        today's READY/NEAR candidate board; use get_signal_board for that.
        """
        snapshot = read_trading_snapshot(workspace_root)
        state = snapshot["state"]
        positions_json = snapshot["positions"]
        live_positions = state.get("positions")
        if not isinstance(live_positions, list) or not live_positions:
            live_positions = positions_json.get("open") or []
        exit_alerts = state.get("exit_alerts")
        if exit_alerts is None:
            exit_alerts = [
                p.get("symbol") for p in live_positions if p.get("state") == "EXIT_ALERT"
            ]
        freshness = snapshot["freshness"]
        return json.dumps(
            {
                "present": bool(state) or bool(live_positions),
                "evidence_scope": "TRADING_ACCOUNT",
                "as_of": state.get("as_of"),
                "day": state.get("day"),
                "market_state": state.get("status"),
                "data_trust": state.get("data_trust") or "UNKNOWN",
                "positions": live_positions,
                "exit_alerts": exit_alerts,
                "last_scan_at": snapshot["last_scan_at"],
                "requested_at": snapshot["now"].isoformat(),
                "requested_market_date": freshness["requested_market_date"],
                "latest_market_data_date": state.get("day"),
                "freshness_status": freshness["freshness_status"],
                "freshness_reason": freshness["freshness_reason"],
                "limitations": [
                    "positions are TRADING_ACCOUNT evidence; they do not authorise READY/NEAR claims",
                    "a position in EXIT_ALERT remains OPEN until the human executes and records the close",
                ],
            },
            ensure_ascii=False,
        )

    @toolset.tool_plain(defer_loading=True)
    def get_validation_status() -> str:
        """Read strategy-forward validation maturity (策略验证/验证进度/
        forward evidence/样本/结算/交易天数/是否有效/PIT) only.

        Discovery vocabulary: 策略 验证 进度 样本 结算 forward 有效性 PIT.
        Evidence scope is TRADING_ACCOUNT. The payload is the ledger-derived
        validation_accounting block plus the current PIT/profitability
        limitations; it deliberately excludes READY/NEAR, positions and
        market-wide context.
        """
        snapshot = read_trading_snapshot(workspace_root)
        state = snapshot["state"]
        accounting = snapshot["validation_accounting"]
        return json.dumps(
            {
                "present": bool(state) or bool(accounting.get("lifecycle")),
                "evidence_scope": "TRADING_ACCOUNT",
                "as_of": accounting.get("as_of") or state.get("as_of"),
                "day": state.get("day"),
                "market_state": state.get("status"),
                "data_trust": state.get("data_trust") or "UNKNOWN",
                "validation_accounting": accounting,
                "strategy_profitability": "UNPROVEN",
                "pit_status": "CONTAMINATED",
                "pit_cause": "current CSI500 membership applied to all historical dates",
                "limitations": [
                    "settled means the full-horizon (d8) forward window exists; an EXIT_ALERT position is still open until the human executes and record_trade_outcome closes it",
                    "zero settled observations means no forward evidence yet, never that the strategy has no effect",
                    "PIT-contaminated universe: historical numbers describe only this sampled universe",
                ],
            },
            ensure_ascii=False,
        )

    # --- analysis watchlist (three-tier universe, tier B) -------------------
    # User attention facts, scoped by an opaque host binding (bound case id
    # else chat channel id). Analysis-only: never READY/NEAR, never a
    # strategy or candidate-pool mutation, no trading approval needed.

    def _analysis_scope(ctx: RunContext[CoreDeps]) -> str | None:
        return ctx.deps.bindings.get("analysis_scope")

    def _prewarm_history(symbols: list[str]) -> dict:
        """Best-effort history hydration for newly watched symbols (v0.2 T005).

        Runs the side-env monitor's prewarm op so akshare stays out of this
        environment. Best-effort by contract: a prewarm failure never
        invalidates the watchlist edit — the result reports watchlist and
        history facts separately."""
        try:
            # ``--state-dir`` precedes the subcommand (argparse, see
            # get_symbol_context).
            stdout = _run_module(
                "zuaef_quant.monitor",
                ["--state-dir", str(workspace_root / "artifacts" / "quant" / "trading"),
                 "prewarm-history", "--symbols", ",".join(symbols)],
                quant_python,
                PREWARM_TIMEOUT_S,
            )
        except (subprocess.TimeoutExpired, OSError, RuntimeError) as exc:
            return {"error": f"history prewarm unavailable: {str(exc)[-200:]}"}
        try:
            line = stdout.strip().splitlines()[-1] if stdout.strip() else "{}"
            data = json.loads(line)
        except ValueError:
            return {"error": "history prewarm returned unreadable output"}
        return data.get("prewarm") if isinstance(data.get("prewarm"), dict) else data

    def _watchlist_update(
        ctx: RunContext[CoreDeps], action: str, symbols: list[str]
    ) -> dict[str, Any]:
        """Shared host implementation for the watchlist write surface.

        ``manage_watchlist`` (add/remove) delegates here; there is one write
        path and one read-back verification, so "已加入" can never be claimed
        without persisted state proving it.
        """
        scope = _analysis_scope(ctx)
        if not scope:
            return {
                "error": "no analysis scope is bound to this run (host must provide the analysis_scope binding)"
            }
        try:
            result = watchlist_store.update_symbols_in(
                watchlist_store.scope_dir(workspace_root),
                scope,
                action,
                symbols,
                run_id=ctx.deps.run_id,
            )
        except watchlist_store.WatchlistError as exc:
            return {"error": str(exc)}
        # Write -> read-back: "已加入" may only be said after the persisted
        # state itself proves the change; a write that did not stick is
        # reported as a failure, never as success.
        persisted = watchlist_store.read_symbols_in(
            watchlist_store.scope_dir(workspace_root), scope
        )
        verified = all(
            (s in persisted) if action == "add" else (s not in persisted)
            for s in result["changed"]
        )
        result["verified"] = verified
        if not verified:
            result["error"] = "watchlist write did not persist; do not claim success"
        if verified and action == "add" and result["changed"]:
            result["history_prewarm"] = _prewarm_history(result["changed"])
        result["note"] = "watchlist updated; analysis-only, never READY/NEAR"
        return result

    @toolset.tool(defer_loading=True)
    def manage_watchlist(
        ctx: RunContext[CoreDeps], action: str, symbols: list[str] | None = None
    ) -> str:
        """Manage THIS run's analysis watchlist (自选/观察/关注/加入/移除/
        watchlist): one bounded action over user attention facts. action is
        add | remove | list; symbols are 6-digit A-share codes (not required
        for list). Local and reversible: it never places orders, never
        changes the strategy and never adds anything to the candidate pool —
        say that caveat back to the user when confirming. Newly added
        symbols get a best-effort history prewarm; report watchlist and
        prewarm facts separately.

        Discovery vocabulary: 自选 观察 关注 加入 移除 watchlist.
        """
        normalized = str(action or "").strip().lower()
        if normalized == "list":
            scope = _analysis_scope(ctx)
            if not scope:
                return json.dumps(
                    {"error": "no analysis scope is bound to this run (host must provide the analysis_scope binding)"},
                    ensure_ascii=False,
                )
            current = watchlist_store.read_symbols_in(
                watchlist_store.scope_dir(workspace_root), scope
            )
            return json.dumps(
                {
                    "scope": scope,
                    "action": "list",
                    "symbols": current,
                    "count": len(current),
                    "semantics": "analysis-only; never READY/NEAR; candidate pool untouched",
                    "note": "positions are tracked separately by get_positions",
                },
                ensure_ascii=False,
            )
        if normalized not in ("add", "remove"):
            return json.dumps(
                {"error": "action must be add, remove or list"},
                ensure_ascii=False,
            )
        return json.dumps(
            _watchlist_update(ctx, normalized, [str(s) for s in (symbols or [])]),
            ensure_ascii=False,
        )

    @toolset.tool
    def get_symbol_context(ctx: RunContext[CoreDeps], symbol: str) -> str:
        """On-demand single-symbol analysis context (个股诊断/报价) for ANY
        6-digit A-share code — including symbols outside the candidate pool. Read-only host
        diagnostics: live quote with host-derived freshness, universe
        membership (candidate pool / analysis watchlist / open positions),
        frozen S3 clause distances (how far from entry conditions), MA5
        evidence and scan freshness. Use this instead of refusing to analyze
        an off-pool symbol: not being in the candidate pool only means it
        cannot produce READY/NEAR, never that it cannot be researched."""
        # ``--state-dir`` is a top-level monitor option: it MUST precede the
        # subcommand for argparse.
        args = [
            "--state-dir", str(workspace_root / "artifacts" / "quant" / "trading"),
            "symbol-context", "--symbol", str(symbol),
        ]
        scope = _analysis_scope(ctx)
        if scope:
            args += ["--scope", scope]
        try:
            stdout = _run_module("zuaef_quant.monitor", args, quant_python, SYMBOL_CONTEXT_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "evidence_scope": "SINGLE_SYMBOL",
                    "error": "symbol context fetch timed out; try again shortly",
                },
                ensure_ascii=False,
            )
        line = stdout.strip().splitlines()[-1] if stdout.strip() else "{}"
        try:
            data = json.loads(line)
        except ValueError:
            return json.dumps(
                {
                    "evidence_scope": "SINGLE_SYMBOL",
                    "error": "symbol context returned unreadable output",
                },
                ensure_ascii=False,
            )
        if not isinstance(data, dict):
            return json.dumps(
                {
                    "evidence_scope": "SINGLE_SYMBOL",
                    "error": "symbol context returned an unexpected payload",
                },
                ensure_ascii=False,
            )
        data["evidence_scope"] = "SINGLE_SYMBOL"
        return json.dumps(data, ensure_ascii=False)

    @toolset.tool_plain(defer_loading=True)
    def get_market_intelligence(symbol: str, limit: int = 8) -> str:
        """Bounded structured finance evidence for one 6-digit A-share code:
        recent company news and announcements from the structured feed
        (公司新闻/公告/消息: title, truncated summary, published time,
        source, url). NOT open-ended web research —
        for "why did it move / what happened in the industry" questions use
        the harness WebSearch/WebFetch capabilities and keep source + time
        with every fact. A fetch failure returns structured evidence of the
        failure: degrade to PARTIAL research, never fabricate items."""
        symbol = str(symbol).strip()
        limit = max(1, min(int(limit), 20))
        try:
            stdout = _run_module(
                "zuaef_quant.market_intel",
                ["--symbol", symbol, "--limit", str(limit)],
                quant_python,
                MKT_INTEL_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "evidence_scope": "SINGLE_SYMBOL_NEWS",
                    "error": "market intelligence fetch timed out; try again shortly",
                },
                ensure_ascii=False,
            )
        except RuntimeError as exc:
            return json.dumps(
                {
                    "evidence_scope": "SINGLE_SYMBOL_NEWS",
                    "error": f"market intelligence unavailable: {str(exc)[-200:]}",
                },
                ensure_ascii=False,
            )
        line = stdout.strip().splitlines()[-1] if stdout.strip() else "{}"
        try:
            data = json.loads(line)
        except ValueError:
            return json.dumps(
                {
                    "evidence_scope": "SINGLE_SYMBOL_NEWS",
                    "error": "market intelligence returned unreadable output",
                },
                ensure_ascii=False,
            )
        if not isinstance(data, dict):
            return json.dumps(
                {
                    "evidence_scope": "SINGLE_SYMBOL_NEWS",
                    "error": "market intelligence returned an unexpected payload",
                },
                ensure_ascii=False,
            )
        data["evidence_scope"] = "SINGLE_SYMBOL_NEWS"
        return json.dumps(data, ensure_ascii=False)

    @toolset.tool_plain(defer_loading=True)
    def get_market_context() -> str:
        """Bounded market-wide A-share evidence (A股/大盘/全市场): major
        indices, 上涨/下跌 breadth, 成交额, 行业板块 leaders/laggards, 外盘
        Asia indices, 原油, 利率/美债, 美元 and a bounded macro timeline.

        Discovery vocabulary: A股 大盘 市场 全市场 今天 为什么 跌 大跌
        暴跌 普跌 上涨 下跌 板块 行业 原因 宏观 外盘 亚洲股市 原油 利率
        美债 美元 风险偏好.
        Evidence scope is A_SHARE_MARKET_WIDE.  This host proves what happened
        (OBSERVED); the model interprets why.  Not a crawler/browser.  Missing
        data stays missing and the candidate pool/watchlist/positions are never
        substituted for market-wide evidence."""
        try:
            stdout = _run_module(
                "zuaef_quant.market_context",
                [],
                quant_python,
                MARKET_CONTEXT_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return json.dumps(
                {
                    "as_of": None,
                    "evidence_scope": "A_SHARE_MARKET_WIDE",
                    "missing": ["market_context"],
                    "limitations": ["market context fetch timed out; try again shortly"],
                    "error": "market context fetch timed out",
                },
                ensure_ascii=False,
            )
        except (OSError, RuntimeError) as exc:
            return json.dumps(
                {
                    "as_of": None,
                    "evidence_scope": "A_SHARE_MARKET_WIDE",
                    "missing": ["market_context"],
                    "limitations": ["market context side environment unavailable"],
                    "error": f"market context unavailable: {str(exc)[-200:]}",
                },
                ensure_ascii=False,
            )
        line = stdout.strip().splitlines()[-1] if stdout.strip() else "{}"
        try:
            data = json.loads(line)
        except ValueError:
            return json.dumps(
                {
                    "as_of": None,
                    "evidence_scope": "A_SHARE_MARKET_WIDE",
                    "missing": ["market_context"],
                    "limitations": ["market context returned unreadable output"],
                    "error": "market context returned unreadable output",
                },
                ensure_ascii=False,
            )
        if not isinstance(data, dict):
            return json.dumps(
                {
                    "as_of": None,
                    "evidence_scope": "A_SHARE_MARKET_WIDE",
                    "missing": ["market_context"],
                    "limitations": ["market context returned an unexpected payload"],
                    "error": "market context returned an unexpected payload",
                },
                ensure_ascii=False,
            )
        data["evidence_scope"] = "A_SHARE_MARKET_WIDE"
        return json.dumps(data, ensure_ascii=False)

    # --- research artifacts (research service v0.2, T011/T012) --------------
    # Durable research packets + customer evidence, scoped like the watchlist
    # (bound case else chat channel). Business research state, never
    # execution state; customer claims stay UNVERIFIED and never touch
    # candidate/READY/NEAR/strategy/fills.

    def _research_root() -> Path:
        return workspace_root / "artifacts" / "quant" / "research"

    @toolset.tool(defer_loading=True)
    def save_research_packet(
        ctx: RunContext[CoreDeps],
        symbol: str,
        research_status: str,
        thesis: str,
        invalidation: str = "",
        coverage: list[str] | None = None,
        supporting_facts: list[str] | None = None,
        counter_evidence: list[str] | None = None,
        risks: list[str] | None = None,
        scenarios: list[str] | None = None,
        unknowns: list[str] | None = None,
        source_references: list[str] | None = None,
    ) -> str:
        """Persist one bounded research packet as a business artifact after a
        full analysis (全面分析结论/研究报告/研究记录; quant-research skill). research_status is
        COMPLETE | PARTIAL | INSUFFICIENT_EVIDENCE (business research state,
        not runtime state). scenarios: one entry per scenario (Bull / Base /
        Bear) with its conditions, evidence basis and invalidation. facts
        must be current-run evidence — no tool traces, no conversation
        memory. Returns the workspace-relative artifact path."""
        scope = _analysis_scope(ctx)
        if not scope:
            return json.dumps(
                {"error": "no analysis scope is bound to this run (host must provide the analysis_scope binding)"},
                ensure_ascii=False,
            )
        try:
            result = research_store.save_packet(
                _research_root(), scope, symbol,
                research_status=research_status, thesis=thesis,
                invalidation=invalidation, coverage=coverage,
                supporting_facts=supporting_facts, counter_evidence=counter_evidence,
                risks=risks, scenarios=scenarios, unknowns=unknowns,
                source_references=source_references, run_id=ctx.deps.run_id,
            )
        except ValueError as exc:  # ResearchError + shared 6-digit symbol rule
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        return json.dumps(result, ensure_ascii=False)

    @toolset.tool(defer_loading=True)
    def get_research_packet(ctx: RunContext[CoreDeps], symbol: str) -> str:
        """Read the LATEST research packet for one symbol in this run's scope
        (上次研究/研究记录/之前的风险: prior hypothesis + recent customer
        evidence tail). A packet is a
        PRIOR HYPOTHESIS, never current market truth: re-verify the current
        quote and evidence via get_symbol_context before building on it."""
        scope = _analysis_scope(ctx)
        if not scope:
            return json.dumps(
                {"error": "no analysis scope is bound to this run (host must provide the analysis_scope binding)"},
                ensure_ascii=False,
            )
        try:
            packet = research_store.latest_packet(_research_root(), scope, symbol)
            evidence = research_store.read_customer_evidence(_research_root(), scope, symbol)
        except research_store.ResearchError as exc:
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        return json.dumps(
            {
                "packet": packet,
                "recent_customer_evidence": evidence,
                "note": None if packet else "no prior research packet for this symbol in this scope",
            },
            ensure_ascii=False,
        )

    @toolset.tool(defer_loading=True)
    def record_customer_evidence(
        ctx: RunContext[CoreDeps], symbol: str, claim: str, source_hint: str = ""
    ) -> str:
        """Record a customer-reported claim (客户说/客户提供/供应商说, e.g.
        供应商说订单很满) as
        CUSTOMER_REPORTED / UNVERIFIED evidence with provenance. It may shape
        research attention, hypotheses and web search terms — it can NEVER
        create READY/NEAR, change the candidate pool, the strategy or any
        fill; say that boundary back when it matters. When a Case is bound,
        high-value durable business context also belongs in the Case itself
        (via the Case tools)."""
        scope = _analysis_scope(ctx)
        if not scope:
            return json.dumps(
                {"error": "no analysis scope is bound to this run (host must provide the analysis_scope binding)"},
                ensure_ascii=False,
            )
        try:
            result = research_store.record_customer_evidence(
                _research_root(), scope, symbol, claim=claim, source_hint=source_hint,
                run_id=ctx.deps.run_id,
            )
        except ValueError as exc:  # ResearchError + shared 6-digit symbol rule
            return json.dumps({"error": str(exc)}, ensure_ascii=False)
        return json.dumps(result, ensure_ascii=False)

    @toolset.tool_plain(defer_loading=True)
    def render_quant_business_artifact() -> str:
        """Deterministically render the current business dashboard HTML (业务
        报表/导出报表/交付报告) from
        the canonical trading artifacts (runs the host renderer; the model
        never assembles HTML itself). Returns the workspace-relative artifact
        path under artifacts/quant/delivery/ plus the renderer's bounded OK
        summary. The output is a single-file self-contained HTML suitable for
        direct delivery as a document attachment.
        """
        stamp = _dt.datetime.now(_dt.UTC).strftime("%Y%m%d-%H%M")
        delivery = workspace_root / "artifacts" / "quant" / "delivery"
        delivery.mkdir(parents=True, exist_ok=True)
        out = delivery / f"quant-business-{stamp}.html"
        stdout = _run_module(
            "zuaef_quant.dashboard.render", ["--out", str(out)], quant_python, RENDER_TIMEOUT_S
        )
        summary = next((ln for ln in stdout.splitlines() if ln.startswith("OK ->")), stdout[-200:])
        return json.dumps(
            {
                "artifact": str(out.relative_to(workspace_root)),
                "summary": summary,
                "note": "single-file self-contained HTML; opens offline",
            },
            ensure_ascii=False,
        )

    return toolset
