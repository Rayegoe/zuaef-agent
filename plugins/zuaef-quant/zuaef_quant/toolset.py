"""QuantToolset — the six model-visible deterministic tools.

Boundary (spec pack 03 §4): the host owns validation, data, evaluator,
market rules, costs and benchmark; the Agent owns interpretation and the
bounded numeric StrategySpec it submits. Strategy children are whitelisted
TOML key/value specs — arbitrary Python never crosses this boundary.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.models import CoreDeps
from zuaef_agent.plugin_api import CompositionError

from .freshness import derive_freshness, market_date_of, now_market

REPO_ROOT_ENV = "ZUAEF_QUANT_REPO_ROOT"
TOOLS_DIR_ENV_MARKERS = ("tools/quant_eval_qlib.py", "benchmarks/quant/gen1/quant.toml")


def resolve_repo_root() -> Path:
    """Locate the repository holding the quant side-env scripts.

    Resolution order: ``ZUAEF_QUANT_REPO_ROOT`` wins (explicit), then the
    package position derives the repo root from ``__file__`` (editable
    layouts: ``<repo>/plugins/zuaef-quant/zuaef_quant/``), then the current
    directory must carry the quant tool markers. Loud failure otherwise —
    never guess. The package-derived step makes plugin composition
    independent of the process cwd (workers, worktrees, systemd services).
    """
    import os

    configured = os.getenv(REPO_ROOT_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    package = Path(__file__).resolve()
    # editable: <repo>/plugins/zuaef-quant/zuaef_quant/toolset.py
    candidate = package.parents[3]
    if all((candidate / marker).exists() for marker in TOOLS_DIR_ENV_MARKERS):
        return candidate
    candidate = Path.cwd().resolve()
    if all((candidate / marker).exists() for marker in TOOLS_DIR_ENV_MARKERS):
        return candidate
    raise CompositionError(
        "quant plugin cannot locate the repository quant tooling; run the "
        f"agent from the repo root or set {REPO_ROOT_ENV}"
    )


REPO_ROOT = resolve_repo_root()
TOOLS_DIR = REPO_ROOT / "tools"
QUANT_EVAL_SCRIPT = TOOLS_DIR / "quant_eval_qlib.py"
QUANT_SCAN_SCRIPT = TOOLS_DIR / "quant_live_scan.py"
QUANT_MONITOR_SCRIPT = TOOLS_DIR / "quant_trading_monitor.py"
QUANT_RENDER_SCRIPT = TOOLS_DIR / "quant_render_business_dashboard.py"
DEFAULT_BENCH_DIR = REPO_ROOT / "benchmarks" / "quant" / "gen1"
EVAL_TIMEOUT_S = 1200
SCAN_TIMEOUT_S = 300
ACK_TIMEOUT_S = 120
RENDER_TIMEOUT_S = 120
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


def _read_json(path: Path, default):
    """Tolerant canonical-artifact read: absent/corrupt -> the default, never
    a fabricated business state."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _read_jsonl_tail(path: Path, limit: int) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    rows = []
    for line in lines[-limit:]:
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _run(script: Path, args: list[str], quant_python: Path, timeout: int) -> str:
    proc = subprocess.run(
        [str(quant_python), str(script), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout)[-800:]
        raise RuntimeError(f"quant side-env run failed ({script.name}): {tail}")
    return proc.stdout


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
        stdout = _run(
            QUANT_EVAL_SCRIPT,
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

    @toolset.tool_plain
    def get_live_signals() -> str:
        """Scan the active candidate universe using current market quotes and
        return bounded triggers with their timestamps and scan latency.
        Universe resolution is deterministic (candidate-pool handoff first,
        frozen CSI500 subset as compatibility fallback; never empty). The
        model never scans the whole market. An empty trigger list is a valid
        NO_TRADE answer; triggers are evidence, not orders.
        """
        stdout = _run(
            QUANT_SCAN_SCRIPT,
            ["--max-triggers", "10"],
            quant_python,
            SCAN_TIMEOUT_S,
        )
        return stdout.strip().splitlines()[-1]

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
        EXIT. ENTER_CANDIDATE is never an order. signal_timestamp must be the
        timestamp returned by get_live_signals, so the host can measure
        end-to-end decision latency. decision_id must be unique, e.g.
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
        stdout = _run(QUANT_MONITOR_SCRIPT, args, quant_python, ACK_TIMEOUT_S)
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

    @toolset.tool_plain
    def get_trading_context() -> str:
        """Read the bounded CURRENT trading context from the canonical M1
        artifacts (workspace/artifacts/quant/trading/). Read-only projection:
        never recomputes the market and never re-derives triggers. Returns
        system health, market/data-trust status, READY/NEAR lists, open
        positions, exit alerts, recent durable material events, forward
        summary and heartbeat/last-scan times. Freshness is a HOST-derived
        fact (freshness_status/freshness_reason plus the requested/data/scan
        dates): never infer data freshness from dates yourself and never
        interpret READY/NEAR as a current-day result unless
        freshness_status is FRESH. Base every trading answer on this context
        instead of memory; a stale context is a fact to report, not to
        refresh by re-scanning.
        """
        trading = workspace_root / "artifacts" / "quant" / "trading"
        state = _read_json(trading / "state.json", {})
        positions = _read_json(trading / "positions.json", {"open": [], "closed": []})
        forward = _read_json(trading / "forward.json", {"observations": []})
        soak = _read_jsonl_tail(trading / "soak.jsonl", 50)
        alerts = _read_jsonl_tail(trading / "alerts.jsonl", 20)
        observations = forward.get("observations") or []
        events = [
            {k: a.get(k) for k in ("ts", "type", "symbol", "what", "why", "price", "venue")}
            for a in alerts
        ]
        last_scan_at = next(
            (r.get("ts") for r in reversed(soak) if (r.get("symbols") or 0) > 0), None
        )
        now = now_market()
        freshness = derive_freshness(
            now=now,
            latest_market_data_date=state.get("day"),
            last_scan_at=last_scan_at,
        )
        return json.dumps(
            {
                "present": bool(state),
                "as_of": state.get("as_of"),
                "day": state.get("day"),
                "status": state.get("status"),
                "data_trust": state.get("data_trust") or "UNKNOWN",
                "market_no_trade": state.get("market_no_trade"),
                "system_unavailable": state.get("system_unavailable"),
                "heartbeat_at": soak[-1].get("ts") if soak else None,
                "last_scan_at": last_scan_at,
                "ready": state.get("ready") or [],
                "near": state.get("near") or [],
                "exit_alerts": state.get("exit_alerts") or [],
                "positions": positions.get("open") or [],
                "recent_material_events": events,
                "forward": {
                    "observations": len(observations),
                    "settled": sum(1 for o in observations if o.get("d8") is not None),
                },
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
                ],
            },
            ensure_ascii=False,
        )

    @toolset.tool_plain
    def render_quant_business_artifact() -> str:
        """Deterministically render the current business dashboard HTML from
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
        stdout = _run(
            QUANT_RENDER_SCRIPT, ["--out", str(out)], quant_python, RENDER_TIMEOUT_S
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
