"""ZUAEF Quant deterministic operator CLI (P5).

This is the operator surface for humans, systemd and automation.  It never
starts a model request by itself and never re-implements Quant business logic:
each command delegates to the same deterministic authority the Agent tools
use (the scan sidecar, the canonical monitor, the watchlist store, the
renderer/serve/bridge entry points) and only projects bounded facts for a
human or ``--json`` consumer.

Command tree (kept deliberately small):

    zuaef-quant status
    zuaef-quant scan
    zuaef-quant watchlist list|add|remove
    zuaef-quant monitor once|status
    zuaef-quant dashboard render|serve
    zuaef-quant bridge once

The CLI belongs to the Quant package; the Core CLI does not register domain
commands.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import watchlist as watchlist_store
from .freshness import market_date_of

#: The operator watchlist has no implicit channel/case scope.  Deployments may
#: bind the real existing scope via env or explicit --scope; the CLI never
#: invents a new scope model.
OPERATOR_SCOPE_ENV = "ZUAEF_QUANT_OPERATOR_SCOPE"

SCAN_TIMEOUT_S = 300
MONITOR_TIMEOUT_S = 300
DASHBOARD_TIMEOUT_S = 300
BRIDGE_TIMEOUT_S = 900


class OperatorError(RuntimeError):
    """A deterministic operator-facing failure with a human-readable cause."""


# ---------------------------------------------------------------------------
# deployment environment helpers (stdlib-only runtime resolution)
# ---------------------------------------------------------------------------


def _plugin_root() -> Path:
    from .runtime import package_parent

    return package_parent()


def _repo_root() -> Path:
    from .runtime import resolve_repo_root

    return resolve_repo_root()


def _workspace_root() -> Path:
    configured = os.getenv("ZUAEF_WORKSPACE")
    if configured:
        return Path(configured).expanduser().resolve()
    return _repo_root() / "workspace"


def _quant_python() -> Path:
    from .runtime import resolve_quant_python

    path = resolve_quant_python()
    if not path.is_file():
        raise OperatorError(
            "quant side environment missing: "
            f"{path} not found (set ZUAEF_QUANT_PYTHON to the python that "
            "has akshare/qlib installed)"
        )
    return path


def _side_env() -> dict[str, str]:
    env = os.environ.copy()
    plugin_root = str(_plugin_root())
    previous = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = plugin_root + (os.pathsep + previous if previous else "")
    return env


def _run_capture(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int,
    allowed: tuple[int, ...] = (0,),
) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise OperatorError(f"required command is unavailable: {cmd[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise OperatorError(f"operation timed out after {timeout}s") from exc
    if proc.returncode not in allowed:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        tail = detail[-1] if detail else f"exit code {proc.returncode}"
        raise OperatorError(tail[-500:])
    return proc


def _last_json_line(text: str) -> dict[str, Any] | None:
    for line in reversed(text.strip().splitlines()):
        try:
            data = json.loads(line)
        except ValueError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _emit(args: argparse.Namespace, payload: dict[str, Any], lines: list[str]) -> None:
    if getattr(args, "json", False):
        print(json.dumps(payload, ensure_ascii=False, default=str))
        return
    for line in lines:
        print(line)


# ---------------------------------------------------------------------------
# shared read projections
# ---------------------------------------------------------------------------


def _trading_snapshot() -> dict[str, Any]:
    from .trading import read_trading_snapshot

    return read_trading_snapshot(_workspace_root())


def _bounded_validation(accounting: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "forward_validation_started_at",
        "validation_age_calendar_days",
        "validation_age_trading_days",
        "observations",
        "observations_executed",
        "observations_skipped",
        "observations_settled_full_horizon",
        "observations_accumulating",
        "open_positions",
        "open_positions_in_exit_alert",
        "completed_exits",
    )
    return {key: accounting.get(key) for key in keys}


def _status_payload() -> dict[str, Any]:
    snapshot = _trading_snapshot()
    state = snapshot.get("state") or {}
    freshness = snapshot.get("freshness") or {}
    positions = snapshot.get("positions") or {}
    open_positions = positions.get("open") or []
    validation = snapshot.get("validation_accounting") or {}

    last_scan_date = market_date_of(snapshot.get("last_scan_at"))
    dashboard = _workspace_root() / "artifacts" / "quant" / "business" / "business.html"
    dashboard_present = dashboard.is_file()
    return {
        "market_date": state.get("day"),
        "market_state": state.get("status"),
        "freshness_status": freshness.get("freshness_status"),
        "freshness_reason": freshness.get("freshness_reason"),
        "last_scan_at": snapshot.get("last_scan_at"),
        "last_scan_market_date": last_scan_date.isoformat() if last_scan_date else None,
        "ready": len(state.get("ready") or []),
        "near": len(state.get("near") or []),
        "open_positions": len(open_positions),
        "exit_alert_count": len(state.get("exit_alerts") or []),
        "data_trust": state.get("data_trust") or "UNKNOWN",
        "validation": _bounded_validation(validation),
        "monitor": {
            "status": state.get("status"),
            "market_phase": state.get("market_phase"),
            "heartbeat_at": state.get("heartbeat_at"),
            "symbols_scanned": state.get("symbols_scanned"),
            "last_soak_status": (
                snapshot["soak"][-1].get("status") if snapshot.get("soak") else None
            ),
        },
        "dashboard": {
            "present": dashboard_present,
            "rendered_at": _file_mtime_iso(dashboard) if dashboard_present else None,
        },
    }


def _file_mtime_iso(path: Path) -> str | None:
    try:
        return _iso_from_ns(path.stat().st_mtime_ns)
    except OSError:
        return None


def _iso_from_ns(value: int) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(value / 1_000_000_000, tz=UTC).isoformat()


def _fmt(value: Any) -> str:
    return "UNKNOWN" if value in (None, "") else str(value)


# ---------------------------------------------------------------------------
# status / monitor status
# ---------------------------------------------------------------------------


def cmd_status(args: argparse.Namespace) -> int:
    payload = _status_payload()
    validation = payload["validation"]
    _emit(
        args,
        payload,
        [
            "ZUAEF Quant status",
            f"Market date: {_fmt(payload['market_date'])}",
            f"Market state: {_fmt(payload['market_state'])} (data trust {payload['data_trust']})",
            f"Freshness: {_fmt(payload['freshness_status'])} - {_fmt(payload['freshness_reason'])}",
            f"Last scan: {_fmt(payload['last_scan_at'])}",
            f"Candidate board: READY {payload['ready']} / NEAR {payload['near']}",
            f"Positions: {payload['open_positions']} open / {payload['exit_alert_count']} exit-alert",
            (
                "Validation: "
                f"age_trading_days={_fmt(validation.get('validation_age_trading_days'))} "
                f"observations={_fmt(validation.get('observations'))} "
                f"settled={_fmt(validation.get('observations_settled_full_horizon'))}"
            ),
            (
                "Monitor: "
                f"status={_fmt(payload['monitor'].get('status'))} "
                f"phase={_fmt(payload['monitor'].get('market_phase'))} "
                f"heartbeat={_fmt(payload['monitor'].get('heartbeat_at'))}"
            ),
            f"Dashboard: {'rendered' if payload['dashboard']['present'] else 'not rendered'}",
        ],
    )
    return 0


def cmd_monitor_status(args: argparse.Namespace) -> int:
    payload = _status_payload()
    monitor = payload["monitor"]
    _emit(
        args,
        {
            "market_date": payload["market_date"],
            "market_state": payload["market_state"],
            "freshness_status": payload["freshness_status"],
            "last_scan_at": payload["last_scan_at"],
            "positions": payload["open_positions"],
            "exit_alerts": payload["exit_alert_count"],
            "monitor": monitor,
        },
        [
            "ZUAEF Quant monitor status",
            f"Market date: {_fmt(payload['market_date'])}",
            f"Market state: {_fmt(payload['market_state'])}",
            f"Freshness: {_fmt(payload['freshness_status'])}",
            f"Last scan: {_fmt(payload['last_scan_at'])}",
            f"Positions: {payload['open_positions']} / exit-alert {payload['exit_alert_count']}",
            (
                "Last tick: "
                f"status={_fmt(monitor.get('status'))} "
                f"phase={_fmt(monitor.get('market_phase'))} "
                f"heartbeat={_fmt(monitor.get('heartbeat_at'))} "
                f"symbols_scanned={_fmt(monitor.get('symbols_scanned'))}"
            ),
        ],
    )
    return 0


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------


def _scan_sidecar(args: argparse.Namespace) -> dict[str, Any]:
    cmd = [str(_quant_python()), "-m", "zuaef_quant.scan_sidecar"]
    cmd += ["--max-triggers", str(args.max_triggers)]
    if getattr(args, "universe_file", None):
        cmd += ["--universe-file", str(args.universe_file)]
    proc = subprocess.run(
        cmd,
        cwd=str(_repo_root()),
        env=_side_env(),
        capture_output=True,
        text=True,
        timeout=SCAN_TIMEOUT_S,
        check=False,
    )
    payload = _last_json_line(proc.stdout) or _last_json_line(proc.stderr)
    if proc.returncode != 0:
        if isinstance(payload, dict) and payload.get("error"):
            detail = str(payload.get("detail") or payload.get("error"))
            raise OperatorError(f"scan failed: {detail}") from None
        tail = (proc.stderr or proc.stdout).strip().splitlines()
        raise OperatorError(f"scan failed: {(tail[-1] if tail else 'unknown sidecar error')[-500:]}")
    if payload is None:
        raise OperatorError("scan sidecar returned unreadable output")
    return payload


def cmd_scan(args: argparse.Namespace) -> int:
    payload = _scan_sidecar(args)
    triggers = payload.get("triggers") or []
    volume = payload.get("volume_semantics") or {}
    scan_date = str(payload.get("as_of") or "")
    lines = [
        "Scan completed",
        f"Scan time: {_fmt(scan_date)}",
        f"Universe: {_fmt(payload.get('universe'))} ({_fmt(payload.get('universe_size'))} symbols)",
        f"Quotes fetched: {_fmt(payload.get('quotes_fetched'))}",
        f"READY triggers: {len(triggers)}",
        f"Volume semantics: {_fmt(volume.get('status'))}",
    ]
    if payload.get("triggers_suppressed"):
        lines.append(f"Suppressed by semantic gate: {payload['triggers_suppressed']}")
    _emit(args, payload, lines)
    return 0


# ---------------------------------------------------------------------------
# watchlist
# ---------------------------------------------------------------------------


def _operator_scope(args: argparse.Namespace) -> str:
    value = getattr(args, "scope", None) or os.getenv(OPERATOR_SCOPE_ENV)
    if not value:
        raise OperatorError(
            "watchlist scope is not configured: pass --scope or set "
            f"{OPERATOR_SCOPE_ENV} (existing case/channel scopes stay explicit)"
        )
    return str(value)


def _watchlist_result(scope: str, action: str, symbols: list[str]) -> dict[str, Any]:
    directory = watchlist_store.scope_dir(_workspace_root())
    try:
        result = watchlist_store.update_symbols_in(
            directory, scope, action, symbols, run_id="zuaef-quant-cli"
        )
        persisted = watchlist_store.read_symbols_in(directory, scope)
    except watchlist_store.WatchlistError as exc:
        raise OperatorError(str(exc)) from exc
    verified = all(
        (symbol in persisted) if action == "add" else (symbol not in persisted)
        for symbol in result["changed"]
    )
    if not verified:
        raise OperatorError("watchlist write did not persist; do not claim success")
    return {**result, "verified": True, "scope": scope}


def cmd_watchlist_list(args: argparse.Namespace) -> int:
    scope = _operator_scope(args)
    directory = watchlist_store.scope_dir(_workspace_root())
    try:
        symbols = watchlist_store.read_symbols_in(directory, scope)
    except watchlist_store.WatchlistError as exc:
        raise OperatorError(str(exc)) from exc
    _emit(
        args,
        {
            "scope": scope,
            "symbols": symbols,
            "count": len(symbols),
            "semantics": "analysis-only; never READY/NEAR; candidate pool untouched",
        },
        [f"Watchlist scope: {scope}", *([f"  {symbol}" for symbol in symbols] or ["  (empty)"])],
    )
    return 0


def cmd_watchlist_add(args: argparse.Namespace) -> int:
    return _watchlist_mutation(args, "add")


def cmd_watchlist_remove(args: argparse.Namespace) -> int:
    return _watchlist_mutation(args, "remove")


def _watchlist_mutation(args: argparse.Namespace, action: str) -> int:
    scope = _operator_scope(args)
    result = _watchlist_result(scope, action, [str(s) for s in args.symbols])
    human = [
        f"Watchlist {action} verified",
        f"Scope: {scope}",
        f"Changed: {', '.join(result['changed']) or '(none)'}",
        f"Count now: {result['count']}",
    ]
    _emit(args, result, human)
    return 0


# ---------------------------------------------------------------------------
# monitor
# ---------------------------------------------------------------------------


def _monitor_once_payload(state_dir: Path | None = None) -> dict[str, Any]:
    cmd = [str(_quant_python()), "-m", "zuaef_quant.monitor"]
    if state_dir is not None:
        cmd += ["--state-dir", str(state_dir)]
    cmd.append("once")
    proc = _run_capture(
        cmd,
        cwd=_repo_root(),
        env=_side_env(),
        timeout=MONITOR_TIMEOUT_S,
        # 3 = SYSTEM_UNAVAILABLE is an operational failure but still prints a
        # bounded JSON result; let the caller surface it.
        allowed=(0, 1, 2, 3),
    )
    payload = _last_json_line(proc.stdout)
    if proc.returncode not in (0,):
        detail = payload.get("status") if isinstance(payload, dict) else f"exit code {proc.returncode}"
        raise OperatorError(f"monitor tick failed: {detail}")
    if payload is None:
        raise OperatorError("monitor tick returned unreadable output")
    return payload


def cmd_monitor_once(args: argparse.Namespace) -> int:
    payload = _monitor_once_payload(getattr(args, "state_dir", None))
    events = payload.get("events") or []
    _emit(
        args,
        payload,
        [
            "Monitor tick completed",
            f"Status: {_fmt(payload.get('status'))}",
            f"Symbols scanned: {_fmt(payload.get('symbols'))}",
            f"Events: {len(events)}",
        ],
    )
    return 0


# ---------------------------------------------------------------------------
# dashboard
# ---------------------------------------------------------------------------


def cmd_dashboard_render(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "zuaef_quant.dashboard.render"]
    if getattr(args, "out", None):
        cmd += ["--out", str(args.out)]
    proc = _run_capture(
        cmd, cwd=_repo_root(), env=_side_env(), timeout=DASHBOARD_TIMEOUT_S
    )
    summary = (proc.stdout or proc.stderr).strip().splitlines()
    summary_line = summary[-1] if summary else "dashboard rendered"
    path = Path(args.out) if getattr(args, "out", None) else _repo_root() / "docs" / "quant" / "business.html"
    try:
        display_path = path.relative_to(_repo_root())
    except ValueError:
        display_path = path
    _emit(
        args,
        {"artifact": str(display_path), "summary": summary_line},
        [f"Dashboard rendered: {display_path}", summary_line],
    )
    return 0


def cmd_dashboard_serve(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        "-m",
        "zuaef_quant.dashboard.serve",
        "--host", str(args.host),
        "--port", str(args.port),
    ]
    try:
        proc = subprocess.run(cmd, cwd=str(_repo_root()), env=_side_env(), check=False)
    except FileNotFoundError as exc:
        raise OperatorError("dashboard server could not start: python interpreter unavailable") from exc
    return int(proc.returncode)


# ---------------------------------------------------------------------------
# bridge
# ---------------------------------------------------------------------------


def cmd_bridge_once(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "zuaef_quant.bridge"]
    if getattr(args, "dry_run", False):
        cmd.append("--dry-run")
    proc = _run_capture(
        cmd,
        cwd=_repo_root(),
        env=_side_env(),
        timeout=BRIDGE_TIMEOUT_S,
    )
    output = (proc.stdout or "").strip()
    if getattr(args, "json", False):
        print(json.dumps({"ok": True, "dry_run": bool(getattr(args, "dry_run", False)), "output": output}, ensure_ascii=False))
    else:
        print(output or "Bridge tick completed")
    return 0


# ---------------------------------------------------------------------------
# command parser
# ---------------------------------------------------------------------------


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit one bounded JSON object instead of human text",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="show operator diagnostics on failure",
    )


def _add_scope(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--scope",
        default=None,
        help=(
            "existing analysis scope for this watchlist operation "
            f"(else {OPERATOR_SCOPE_ENV})"
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zuaef-quant",
        description="ZUAEF Quant deterministic operator surface (no model requests).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="show bounded Quant business/runtime status")
    _add_common(status)
    status.set_defaults(func=cmd_status)

    scan = sub.add_parser("scan", help="run the same live scan as run_live_scan()")
    _add_common(scan)
    scan.add_argument("--max-triggers", type=int, default=10)
    scan.add_argument("--universe-file", type=Path, default=None)
    scan.set_defaults(func=cmd_scan)

    monitor = sub.add_parser("monitor", help="run or inspect the deterministic monitor")
    monitor_sub = monitor.add_subparsers(dest="monitor_command", required=True)
    monitor_once = monitor_sub.add_parser("once", help="run one deterministic monitor tick")
    _add_common(monitor_once)
    monitor_once.add_argument(
        "--state-dir",
        type=Path,
        default=None,
        help="isolated fixture state dir (default: production trading state)",
    )
    monitor_once.set_defaults(func=cmd_monitor_once)
    monitor_status = monitor_sub.add_parser("status", help="inspect monitor runtime facts")
    _add_common(monitor_status)
    monitor_status.set_defaults(func=cmd_monitor_status)

    watchlist = sub.add_parser("watchlist", help="manage the scoped analysis watchlist")
    watchlist_sub = watchlist.add_subparsers(dest="watchlist_command", required=True)
    wl_list = watchlist_sub.add_parser("list", help="list the current watchlist")
    _add_common(wl_list)
    _add_scope(wl_list)
    wl_list.set_defaults(func=cmd_watchlist_list)
    for action, handler in (("add", cmd_watchlist_add), ("remove", cmd_watchlist_remove)):
        wl_action = watchlist_sub.add_parser(action, help=f"{action} symbols")
        _add_common(wl_action)
        _add_scope(wl_action)
        wl_action.add_argument("symbols", nargs="+", help="6-digit A-share symbols")
        wl_action.set_defaults(func=handler)

    dashboard = sub.add_parser("dashboard", help="render or serve the business dashboard")
    dashboard_sub = dashboard.add_subparsers(dest="dashboard_command", required=True)
    dash_render = dashboard_sub.add_parser("render", help="render the business dashboard HTML")
    _add_common(dash_render)
    dash_render.add_argument("--out", type=Path, default=None)
    dash_render.set_defaults(func=cmd_dashboard_render)
    dash_serve = dashboard_sub.add_parser("serve", help="serve dashboards on a local port")
    dash_serve.add_argument("--host", default="127.0.0.1")
    dash_serve.add_argument("--port", type=int, default=8787)
    dash_serve.set_defaults(func=cmd_dashboard_serve)

    bridge = sub.add_parser("bridge", help="run the existing Telegram bridge one-shot tick")
    bridge_sub = bridge.add_subparsers(dest="bridge_command", required=True)
    bridge_once = bridge_sub.add_parser("once", help="run one bridge consumption tick")
    _add_common(bridge_once)
    bridge_once.add_argument("--dry-run", action="store_true", help="process and print instead of sending")
    bridge_once.set_defaults(func=cmd_bridge_once)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.func
    try:
        return int(handler(args))
    except OperatorError as exc:
        if getattr(args, "verbose", False):
            traceback.print_exc()
        print(f"zuaef-quant: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
