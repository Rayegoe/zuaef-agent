"""Quant Telegram event bridge — the single delivery authority for proactive
quant notifications (ZUAEF Quant Phase 2 v0.1, spec §8).

A host-side ONE-SHOT consumer (systemd timer ticks it; each run reads, acts,
exits — no long-lived process to go half-dead). It consumes the monitor's
durable alert stream (workspace/artifacts/quant/trading/alerts.jsonl) and:

- E1 NEW_READY / E2 POSITION_EXIT_ALERT -> one quant-decision Agent run
  (interpretation-only: the run is prompted and post-guarded so it has NO
  delivery authority; the bridge is the only sender) -> push
- E3 LIVE_CONNECTION_LOST (the durable proxy for SYSTEM_UNAVAILABLE) /
  E4 DATA_UNTRUSTED / E5 POSITION_OPENED / POSITION_CLOSED -> deterministic
  fixed copy, zero model calls
- SYSTEM_RECOVERED once, only on deterministic evidence (in-session +
  system_unavailable false + fresh heartbeat), never inferred by an Agent
- T10 daily summary after close, once per trading day, continuity verdict
  taken from the SAME load_real_trend() implementation the Dashboard uses

Failure semantics (spec §22): an Agent failure degrades to the
deterministic event copy (the canonical event remains valid); a Telegram
send failure leaves the event unconsumed — consumption is ordered,
line-by-line, checkpoint-after-delivery, so the cursor never moves past a
failed line. The cursor is only a read position: delivery identities live
separately, so a truncated/rotated alerts.jsonl re-scans from zero without
re-sending.

Runtime state lives under .zuaef-state/quant-bridge/ (cursor, delivery
identities, notify log) — never a second trading ledger.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime
from datetime import time as dtime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import quant_render_business_dashboard as biz
from zuaef_telegram.client import TelegramClient, TelegramError

from zuaef_agent.config import AgentSettings
from zuaef_agent.gateway.bridge import start_profile_run
from zuaef_agent.gateway.renderer import chunk_text

TRADING_DIR = REPO_ROOT / "workspace" / "artifacts" / "quant" / "trading"
BRIDGE_STATE_DIR = REPO_ROOT / ".zuaef-state" / "quant-bridge"
PROFILE = "quant-decision"

TZ_SH = ZoneInfo("Asia/Shanghai")
DAILY_SUMMARY_AFTER = dtime(15, 5)
DELIVERED_IDS_MAX = 500

#: Material-event contract (spec §5). Everything else in alerts.jsonl
#: (NEW_NEAR, READY_INVALIDATED, POSITION_EXIT_CLEARED, HUMAN_SKIP) is not a
#: proactive interrupt (spec §6) and is consumed silently.
AGENT_EVENTS = {"NEW_READY", "POSITION_EXIT_ALERT"}
DETERMINISTIC_EVENTS = {
    "LIVE_CONNECTION_LOST",
    "DATA_UNTRUSTED",
    "POSITION_OPENED",
    "POSITION_CLOSED",
}
#: Interpretation-only contract (amendment ①): any settled tool effect from
#: a delivery tool inside a bridge-triggered run is an authority violation.
DELIVERY_TOOLS = {"report_to_telegram", "send_artifact_to_supervisor"}

RUN_PROMPT = """\
A canonical Quant Runtime material event has occurred.

Event:
{event_json}

First call get_trading_context. Use canonical trading facts as truth.

Explain in concise Chinese, suitable for a Telegram message:
1. What changed
2. Why it matters
3. What deterministic rule caused it
4. Current position/state
5. What the human needs to decide now

Do not:
- invent missing facts
- claim profitability
- turn NEAR into READY
- treat SYSTEM_UNAVAILABLE as NO_TRADE
- create a second trading ledger
- You have no delivery authority. Do not send, report, or deliver anything \
anywhere — the bridge delivers your explanation. Explain only.
"""


class BridgeError(RuntimeError):
    """Configuration-level failure: the bridge cannot run at all."""


# ---------------------------------------------------------------------------
# durable state (cursor + delivery identities + flags) — runtime state,
# never trading truth; atomic tmp+rename like the receipt store
# ---------------------------------------------------------------------------


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _fresh_state() -> dict:
    return {
        "offset": 0,
        "inode": None,
        "delivered_ids": [],
        "pending_recovery": False,
        "daily": {},
    }


def load_state(state_dir: Path) -> dict:
    try:
        data = json.loads((state_dir / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _fresh_state()
    state = _fresh_state()
    state.update({k: v for k, v in data.items() if k in state})
    return state


def save_state(state_dir: Path, state: dict) -> None:
    _atomic_write_json(state_dir / "state.json", state)


def log_action(state_dir: Path, entry: dict) -> None:
    """Minimal notify log (spec §21): event identity, run id, delivery fact."""
    entry = {"ts": datetime.now(TZ_SH).isoformat(timespec="seconds"), **entry}
    path = state_dir / "bridge.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def event_identity(alert: dict) -> str:
    return f"{alert.get('type')}:{alert.get('symbol')}:{alert.get('ts') or alert.get('day')}"


# ---------------------------------------------------------------------------
# tolerant readers (missing file -> honest default, never fabricated)
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _read_jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


# ---------------------------------------------------------------------------
# telegram sender (single delivery authority)
# ---------------------------------------------------------------------------


def build_client() -> TelegramClient:
    token = os.getenv("ZUAEF_TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        raise BridgeError(
            "bridge credentials missing: set ZUAEF_TELEGRAM_BOT_TOKEN/"
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (local environment only)"
        )
    return TelegramClient(bot_token=token, chat_id=chat)


def send_text(client: TelegramClient, text: str) -> None:
    """Chunked text delivery through the single sender."""
    for chunk in chunk_text(text):
        client.send_message(chunk)


# ---------------------------------------------------------------------------
# deterministic copy (E3/E4/E5) — zero model calls
# ---------------------------------------------------------------------------


def deterministic_message(alert: dict) -> str:
    etype = alert.get("type")
    symbol = alert.get("symbol") or "—"
    why = str(alert.get("why") or "")
    if etype == "LIVE_CONNECTION_LOST":
        return (
            "⚠️ SYSTEM_UNAVAILABLE\n"
            f"系统当前无法可靠判断是否存在机会：{why}\n"
            "SYSTEM_UNAVAILABLE ≠ NO_TRADE — 不要把沉默当作没有信号。"
        )
    if etype == "DATA_UNTRUSTED":
        return (
            "⚠️ DATA_UNTRUSTED\n"
            f"数据质量达到阻断级：{why}\n"
            "数据信任与系统可用性、市场状态相互独立；UNKNOWN 不会被推断为 FAIL。"
        )
    if etype == "POSITION_OPENED":
        venue = alert.get("venue") or "paper"
        return (
            f"✅ 已记录 {venue} Buy：{symbol} @ {alert.get('price')}\n"
            f"{why}\ncanonical position 已建立。"
        )
    if etype == "POSITION_CLOSED":
        venue = alert.get("venue") or "paper"
        return (
            f"✅ 已记录 {venue} Sell：{symbol} @ {alert.get('price')}\n"
            f"{why}\nposition 已平仓。"
        )
    raise BridgeError(f"no deterministic copy for event type {etype!r}")


RECOVERED_MESSAGE = (
    "✅ SYSTEM_RECOVERED\n"
    "Runtime 已恢复：本时段心跳新鲜、system_unavailable 已解除。\n"
    "此后的事件再次可信。"
)

AGENT_FAILED_SUFFIX = "Agent explanation unavailable. Canonical runtime event remains valid."


def fallback_message(alert: dict) -> str:
    what = alert.get("what") or alert.get("type")
    return (
        f"🔶 {alert.get('type')} · {alert.get('symbol')}\n"
        f"{what} @ {alert.get('price')}\n"
        f"{alert.get('why')}\n\n{AGENT_FAILED_SUFFIX}"
    )


# ---------------------------------------------------------------------------
# agent interpretation (E1/E2) — interpretation-only, bridge delivers
# ---------------------------------------------------------------------------


def agent_explanation(alert: dict, settings: AgentSettings) -> Any:
    """One quant-decision run per material event, fresh conversation (no
    history), interaction-projected as the telegram supervisor. Returns the
    raw outcome (TerminalRun; the caller reads .presentation and inspects
    .receipt for the delivery-authority guard). Raises on composition/run
    failure (caller degrades to deterministic copy, spec §22.1)."""
    event_json = json.dumps(alert, ensure_ascii=False)
    run_id = uuid.uuid4().hex
    conversation_id = f"quant-bridge-{alert.get('day')}-{alert.get('type')}-{alert.get('symbol')}-{run_id[:8]}"
    outcome = start_profile_run(
        settings=settings,
        profile=PROFILE,
        prompt=RUN_PROMPT.format(event_json=event_json),
        conversation_id=conversation_id,
        run_id=run_id,
        surface="telegram",
        actor_role="supervisor",
    )
    if getattr(outcome, "pause_receipt", None) is not None:
        raise RuntimeError("bridge-triggered run paused for approval (unexpected)")
    return outcome


def delivery_authority_violation(outcome: Any) -> bool:
    """Amendment ①: the bridge is the only sender. Any settled delivery-tool
    effect inside a bridge-triggered run means the Agent delivered on its
    own — the bridge must then NOT forward (no double delivery)."""
    receipt = getattr(outcome, "receipt", None)
    for fact in getattr(receipt, "tool_effect_facts", None) or []:
        if getattr(fact, "tool_name", None) in DELIVERY_TOOLS and getattr(fact, "status", "") == "completed":
            return True
    return False


# ---------------------------------------------------------------------------
# recovery (amendment ④: deterministic evidence only, Agent never judges)
# ---------------------------------------------------------------------------


def recovery_evidence(now: datetime, trading_dir: Path) -> bool:
    state = _read_json(trading_dir / "state.json")
    if state.get("system_unavailable") is not False:
        return False
    if state.get("status") not in ("NO_TRADE", "ALERTS"):
        return False
    if not biz.in_trading_session(now):
        return False
    soak = _read_jsonl(trading_dir / "soak.jsonl")
    if not soak:
        return False
    ts = biz._parse_ts(soak[-1].get("ts"))
    if ts is None:
        return False
    age = (now - ts).total_seconds()
    return 0 <= age <= biz.NOW_STALE_AFTER_S


# ---------------------------------------------------------------------------
# daily summary (T10) — continuity verdict from the dashboard's own
# implementation (amendment ⑤: no second threshold set)
# ---------------------------------------------------------------------------

_CONTINUITY_MAP = {"PASS": "PASS", "PARTIAL": "PARTIAL", "NO_REAL_EVIDENCE": "FAIL"}


def daily_summary(day: str, trading_dir: Path) -> str:
    soak = [
        row for row in _read_jsonl(trading_dir / "soak.jsonl")
        if str(row.get("ts", "")).startswith(day)
    ]
    scans = sum(
        1 for row in soak
        if row.get("status") in biz.SOAK_IN_SESSION_STATUSES and (row.get("symbols") or 0) > 0
    )
    no_trade = "yes" if any(row.get("status") == "NO_TRADE" for row in soak) else "no"
    alerts = [a for a in _read_jsonl(trading_dir / "alerts.jsonl") if str(a.get("day")) == day]
    ready = sum(1 for a in alerts if a.get("type") == "NEW_READY")
    entered = sum(1 for a in alerts if a.get("type") == "POSITION_OPENED")
    exited = sum(1 for a in alerts if a.get("type") == "POSITION_EXIT_ALERT")
    forward_new = sum(
        1 for obs in (_read_json(trading_dir / "forward.json").get("observations") or [])
        if str(obs.get("day")) == day
    )
    positions = len(_read_json(trading_dir / "positions.json").get("open") or [])
    trend = biz.load_real_trend(trading_dir)
    verdict = _CONTINUITY_MAP.get(trend["m1_evidence"]["verdict"], "FAIL")
    return (
        f"📊 Quant 日报 {day}\n"
        f"扫描：{scans} 次\n"
        f"READY：{ready}\n"
        f"ENTER：{entered}\n"
        f"EXIT：{exited}\n"
        f"NO_TRADE：{no_trade}\n"
        f"Forward新增：{forward_new}\n"
        f"持仓：{positions}\n"
        f"Runtime continuity：{verdict}"
    )


# ---------------------------------------------------------------------------
# alerts.jsonl consumption: ordered, line-by-line, checkpoint-after-delivery
# (amendments ②③). state["offset"] only ever advances to a line boundary
# that has been FULLY delivered (or skipped as malformed/non-material) —
# a failed send raises with the checkpoint still on the previous line.
# ---------------------------------------------------------------------------


def consume_alerts(
    alerts_path: Path,
    state: dict,
    state_dir: Path,
    client: TelegramClient,
    settings: AgentSettings | None,
    *,
    dry_run: bool = False,
) -> None:
    try:
        stat = alerts_path.stat()
    except OSError:
        return  # no alert stream yet: honest no-op
    if state["inode"] is not None and (stat.st_ino != state["inode"] or stat.st_size < state["offset"]):
        # source reset (truncate/rotate): re-scan from zero; delivered_ids
        # prevent re-sending (amendment ②: cursor != delivery identity)
        state["offset"] = 0
    state["inode"] = stat.st_ino

    with alerts_path.open("rb") as fh:
        fh.seek(state["offset"])
        for raw_line in fh:
            line_end = state["offset"] + len(raw_line)
            text = raw_line.decode("utf-8", errors="replace").strip()
            if not text:
                state["offset"] = line_end
                if not dry_run:
                    save_state(state_dir, state)
                continue
            try:
                alert = json.loads(text)
            except ValueError:
                state["offset"] = line_end  # malformed lines must not wedge the bridge
                if not dry_run:
                    save_state(state_dir, state)
                    log_action(state_dir, {"action": "malformed_line_skipped", "offset": line_end})
                continue
            etype = alert.get("type")
            if etype not in AGENT_EVENTS and etype not in DETERMINISTIC_EVENTS:
                state["offset"] = line_end  # non-material: consumed silently
                if not dry_run:
                    save_state(state_dir, state)
                continue
            identity = event_identity(alert)
            if identity in state["delivered_ids"]:
                state["offset"] = line_end  # already delivered before a source reset
                if not dry_run:
                    save_state(state_dir, state)
                continue

            if dry_run:
                print(f"[dry-run] {identity}: would dispatch "
                      f"({'agent' if etype in AGENT_EVENTS else 'deterministic'})")
                continue

            run_id = None
            if etype in AGENT_EVENTS:
                try:
                    outcome = _agent_outcome(alert, settings)
                    run_id = getattr(getattr(outcome, "receipt", None), "run_id", None)
                    if delivery_authority_violation(outcome):
                        # the Agent delivered on its own; forwarding again
                        # would double-send — mark and log, never resend (①)
                        log_action(state_dir, {
                            "action": "DELIVERY_AUTHORITY_VIOLATION",
                            "event": identity, "run_id": run_id,
                        })
                    else:
                        send_text(client, str(outcome.presentation))
                except TelegramError:
                    # §22.2: keep the event; retry next tick from the last
                    # checkpoint (state["offset"] has NOT moved past it)
                    log_action(state_dir, {"action": "send_failed", "event": identity})
                    raise
                except Exception as exc:  # noqa: BLE001 — §22.1: ANY agent failure degrades to the deterministic copy
                    log_action(state_dir, {
                        "action": "agent_failed_fallback",
                        "event": identity, "error": str(exc)[:200],
                    })
                    send_text(client, fallback_message(alert))
            else:
                send_text(client, deterministic_message(alert))
                if etype == "LIVE_CONNECTION_LOST":
                    state["pending_recovery"] = True

            state["delivered_ids"].append(identity)
            del state["delivered_ids"][:-DELIVERED_IDS_MAX]
            state["offset"] = line_end
            save_state(state_dir, state)  # checkpoint AFTER delivery (③)
            log_action(state_dir, {
                "action": "delivered", "event": identity, "run_id": run_id,
            })


def _agent_outcome(alert: dict, settings: AgentSettings | None) -> Any:
    if settings is None:
        raise RuntimeError("agent settings unavailable")
    return agent_explanation(alert, settings)


# ---------------------------------------------------------------------------
# one tick
# ---------------------------------------------------------------------------


def run_tick(
    *,
    now: datetime,
    trading_dir: Path = TRADING_DIR,
    state_dir: Path = BRIDGE_STATE_DIR,
    client: TelegramClient | None = None,
    settings: AgentSettings | None = None,
    dry_run: bool = False,
) -> int:
    state = load_state(state_dir)
    summary_day = now.strftime("%Y-%m-%d")

    def push(text: str) -> None:
        if dry_run:
            print(f"[dry-run] would send:\n{text}")
            return
        send_text(client, text)

    # E3 recovery — deterministic evidence only (amendment ④)
    if state.get("pending_recovery") and recovery_evidence(now, trading_dir):
        push(RECOVERED_MESSAGE)
        if not dry_run:
            state["pending_recovery"] = False
            save_state(state_dir, state)
            log_action(state_dir, {"action": "system_recovered", "event": f"RECOVERED:None:{summary_day}"})

    # T10 daily summary — once per trading day, after close
    daily = state.setdefault("daily", {})
    has_soak_today = any(
        str(row.get("ts", "")).startswith(summary_day)
        for row in _read_jsonl(trading_dir / "soak.jsonl")
    )
    if now.time() >= DAILY_SUMMARY_AFTER and daily.get("sent_for") != summary_day and has_soak_today:
        push(daily_summary(summary_day, trading_dir))
        if not dry_run:
            daily["sent_for"] = summary_day
            save_state(state_dir, state)
            log_action(state_dir, {"action": "daily_summary", "event": f"DAILY:None:{summary_day}"})

    # material events
    try:
        consume_alerts(
            trading_dir / "alerts.jsonl", state, state_dir, client, settings,
            dry_run=dry_run,
        )
    except TelegramError:
        if not dry_run:
            save_state(state_dir, state)  # checkpoint stays on the last good line
        return 1
    if not dry_run:
        save_state(state_dir, state)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quant Telegram event bridge (oneshot)")
    parser.add_argument("--dry-run", action="store_true", help="process events, print instead of sending")
    args = parser.parse_args(argv)
    try:
        # AgentSettings.from_env() loads PROJECT_ROOT/.env, which carries the
        # telegram credentials used by both the client and profile composition.
        settings = AgentSettings.from_env()
        client = None if args.dry_run else build_client()
    except BridgeError as exc:
        print(f"bridge config error: {exc}", file=sys.stderr)
        return 2
    return run_tick(
        now=datetime.now(TZ_SH),
        client=client,
        settings=settings,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
