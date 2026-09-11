"""Gateway Service — SPEC v0.3 §28–§39, §63–§70.

The single dispatch point between a surface and the ZUAEF runtime. It owns
routing state (sessions, approval tokens, cursors live in the store) and
delegates every run to the shared seams: new runs via
``bridge.start_profile_run``, resumes via the shared ``resume_paused_run``.
It never owns an agent loop, business policy, approval semantics, or
receipts — ReceiptStore/StepPersistence stay the execution truth.

Authorization (allowlist) answers "who may interact"; PydanticAI approval
answers "is this side effect authorized" — the two never merge, and no model
output is ever interpreted as approval.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from ..composition import CompositionError
from ..config import AgentSettings
from ..fast_actions import try_fast_action
from ..models import PauseReceipt, RunReceipt
from ..profiles import list_profiles
from ..receipt_store import ReceiptStore
from ..runtime import (
    DeliveryExportError,
    PausedRun,
    TerminalRun,
    export_receipt_artifacts,
)
from . import bridge
from .models import (
    CONTROL_CALLBACK_ACTIONS,
    CONTROL_PREFIX,
    InboundEnvelope,
    SessionBinding,
)
from .renderer import (
    chunk_text,
    render_case_card,
    render_cases,
    render_error,
    render_new_conversation,
    render_pause,
    render_profile,
    render_run_natural_ack,
    render_run_progress,
    render_status,
    render_terminal,
)
from .routing import RoutingPolicy
from .store import ApprovalTokenError, GatewayStore
from .surface import SurfaceAdapter

logger = logging.getLogger(__name__)

# Terminal Delivery Guard: bounded presentation of a domain-marked reply
# artifact when a run ends without the model's final response.
REPLY_ARTIFACT_MAX_CHARS = 2400

HELP_TEXT = """\
ZUAEF

Send a task normally.

Commands:
/new
/case [id]
/cases
/unbind
/profile [name]
/status
/inspect
/approve
/deny
/artifacts
/help"""

WAITING_FOR_APPROVAL = """\
This session is waiting for approval.

Use the buttons above, /approve, /deny, or /new."""

PROFILE_BLOCKED_BY_PAUSE = (
    "A run is waiting for approval.\nApprove, deny, or /new before changing profile."
)

CASE_BLOCKED_BY_PAUSE = (
    "A run is waiting for approval.\n"
    "Approve, deny, or /new before changing the Case binding — a resumed run "
    "must keep the Case it was bound to."
)

NOTHING_TO_APPROVE = "Nothing is awaiting approval."

GATEWAY_DENY_REASON = "denied by operator from gateway"

# /cases shows the most recent case directories; one keyboard row per case.
CASES_LIST_LIMIT = 20

# Callback-framing contract: a case id rides inside ``zc:bind:<id>`` Telegram
# callback_data, which the Bot API caps at 64 bytes, and the framing uses ":"
# as its separator — so an id must fit the remainder and must not contain a
# colon. The charset matches the case plugin's validate_case_id (duplicated
# here as one regex: the gateway must not import a business plugin).
CALLBACK_DATA_MAX = 64
CASE_ID_MAX = CALLBACK_DATA_MAX - len("zc:bind:")
_CASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_DRAFT_REF = re.compile(r"msg-[A-Za-z0-9_.-]+\.md")

# The approval card shows the outbound draft content so the operator never
# approves unseen text; Telegram caps one message, so long drafts truncate.
DRAFT_PREVIEW_MAX = 2800


def progress_checkpoint_seconds(first: float, second: float, n: int) -> float:
    """Checkpoint time T_n of the arithmetic-backoff progress schedule
    (gateway progress telemetry v0.1): step = second - first, and
    T_n = first + step * n * (n-1) / 2 — so the first two checkpoints are
    exactly the configured seeds and later gaps grow by one step each
    (25, 50, 100, 175, 275, ...). Pure arithmetic; no schedule knobs."""
    return first + (second - first) * n * (n - 1) / 2


def _run_coro(coro):
    """Run one coroutine to completion from a non-loop thread (the progress
    watchdog). The dispatch loop stays synchronous; this thread owns its own
    event loop."""
    return asyncio.run(coro)


class GatewayService:
    def __init__(
        self,
        *,
        settings: AgentSettings,
        store: GatewayStore,
        surface: SurfaceAdapter,
        default_profile: str | None = None,
        config_root: Path | None = None,
        approval_ttl_seconds: int = 86400,
        max_artifact_bytes: int = 10 * 1024 * 1024,
        allowed_user_ids: set[str] | None = None,
        routing_policy: RoutingPolicy | None = None,
        run_ack: bool = True,
        run_progress_seconds: float = 25.0,
        run_progress_seconds_2: float = 50.0,
        auto_artifacts: bool = False,
    ):
        self.settings = settings
        self.store = store
        self.surface = surface
        self.default_profile = default_profile
        self.config_root = config_root
        self.approval_ttl_seconds = approval_ttl_seconds
        self.max_artifact_bytes = max_artifact_bytes
        self.allowed_user_ids = allowed_user_ids
        self.routing = routing_policy or RoutingPolicy()
        self.receipts = ReceiptStore(settings.state_root)
        # Feishu artifacts loop (spec pack 08): when enabled, a settled
        # completed run's receipt-listed artifacts are sent automatically —
        # same containment/size rules as the manual /artifacts command,
        # which stays as recovery. Transport-only: no format policy here.
        self.auto_artifacts = auto_artifacts
        # Natural chat bridging: one state-composed acknowledgment at
        # acceptance, plus arithmetic-backoff mid-run checkpoint lines
        # (25s, 50s, 100s, 175s, ... from the two seed configs) composed
        # from persisted StepPersistence facts. Bounded deterministic
        # transport — no new execution model.
        self.run_ack = run_ack
        self.run_progress_seconds = run_progress_seconds
        self.run_progress_seconds_2 = run_progress_seconds_2
        self._progress_stops: dict[str, threading.Event] = {}
        self._progress_lock = threading.Lock()

    # ── dispatch ────────────────────────────────────────────────────────────

    def handle(self, envelope: InboundEnvelope) -> None:
        if (
            self.allowed_user_ids is not None
            and envelope.user_id not in self.allowed_user_ids
        ):
            logger.info(
                "service rejected inbound from unauthorized user %s", envelope.user_id
            )
            return
        # Thread sessions are created WITHOUT a profile so they inherit the
        # chat-level binding dynamically (spec pack 03 §2 precedence:
        # thread binding > chat binding > group default > gateway default);
        # chat-level sessions keep the gateway default at creation.
        session = self.store.get_or_create_session(
            surface=envelope.surface,
            tenant_id=envelope.tenant_id,
            user_id=envelope.user_id,
            channel_id=envelope.channel_id,
            thread_id=envelope.thread_id,
            default_profile=None if envelope.thread_id else self.default_profile,
        )
        if envelope.callback_action is not None:
            self._handle_callback(envelope, session)
            return
        text = envelope.text.strip()
        if text.startswith("/"):
            self._handle_command(envelope, session)
            return
        if session.paused_run_id:
            self._send_text(session, WAITING_FOR_APPROVAL)
            return
        # Deterministic fast path: mechanically extractable actions run
        # directly without run-id allocation, acknowledgment/progress state or
        # a model call.  False positives are more expensive than false
        # negatives here, so recognition is deliberately strict.
        fast_result = try_fast_action(
            text=envelope.text,
            workspace_root=self.settings.workspace_root,
            now=datetime.now(UTC),
        )
        if fast_result.handled:
            self._send_text(session, fast_result.reply or "已记录。")
            return
        self._start_run(envelope, session)

    def _send_text(self, session: SessionBinding, text: str) -> None:
        for chunk in chunk_text(text):
            self.surface.send_text(session.channel_id, chunk)

    def _effective_profile(
        self, envelope: InboundEnvelope, session: SessionBinding
    ) -> str | None:
        """Binding precedence (spec pack 03 §2): explicit session binding >
        chat binding > configured group default > gateway default. A thread
        session inherits its chat's binding until it binds its own profile
        via ``/profile`` in the thread."""
        if session.profile is not None:
            return session.profile
        if envelope.thread_id:
            chat_session = self.store.get_session(
                surface=envelope.surface,
                tenant_id=envelope.tenant_id,
                user_id=envelope.user_id,
                channel_id=envelope.channel_id,
                thread_id=None,
            )
            if chat_session is not None and chat_session.profile is not None:
                return chat_session.profile
        return (
            self.routing.group_defaults.get(envelope.channel_id)
            or self.default_profile
        )

    # ── run start ───────────────────────────────────────────────────────────

    def _start_run(self, envelope: InboundEnvelope, session: SessionBinding) -> None:
        profile = self._effective_profile(envelope, session)
        # Profile admission happens BEFORE any run state is written and
        # before the agent executes (spec pack 00 §3) — a DM quant attempt
        # never reaches the runtime.
        denial = self.routing.access_error(
            profile,
            surface=envelope.surface,
            chat_type=envelope.chat_type,
            channel_id=envelope.channel_id,
        )
        if denial is not None:
            self._send_text(session, render_error(denial))
            return
        run_id = uuid4().hex
        session = session.model_copy(update={"active_run_id": run_id})
        self.store.save_session(session)
        if self.run_ack:
            self._send_text(session, render_run_natural_ack(
                profile=profile,
                is_continuation=session.last_terminal_run_id is not None,
            ))
        self._start_progress_watchdog(session, run_id)
        # Normal-turn continuity (research service v0.2, T002 / ADR-03): a
        # follow-up message carries bounded recent SEMANTIC turns (user
        # prompts + business answers) — the prior run's tool trajectory is
        # not replayed into the prompt. ConversationSearch covers older
        # facts on demand; pause/resume keeps the exact StepPersistence
        # continuation via the shared resume seam.
        history = (
            bridge.prior_semantic_history(
                self.settings,
                run_id=session.last_terminal_run_id,
                conversation_id=session.conversation_id,
                receipts=self.receipts,
            )
            if session.last_terminal_run_id is not None
            else None
        )
        try:
            outcome = bridge.start_profile_run(
                settings=self.settings,
                profile=profile,
                prompt=bridge.project_prompt(envelope),
                conversation_id=session.conversation_id,
                config_root=self.config_root,
                run_id=run_id,
                message_history=history,
                # Deterministic Case binding: the session's bound case is
                # threaded into the run's CoreDeps — the model never guesses it.
                case_id=session.case_id,
                # Analysis watchlist scope (three-tier universe): the user's
                # attention facts follow the bound Case, else the chat
                # channel — opaque to the kernel, never cross-scope visible.
                analysis_scope=session.case_id or envelope.channel_id,
                # Host-grounded interaction identity (P3B-3 T001/T002): the
                # surface states who is talking; the model never infers it.
                surface=envelope.surface,
                actor_role=envelope.actor_role,
            )
        except CompositionError as exc:
            self._stop_progress_watchdog(run_id)
            session = session.model_copy(update={"active_run_id": None})
            self.store.save_session(session)
            self._send_text(session, render_error(str(exc)))
            return
        self._stop_progress_watchdog(run_id)
        if isinstance(outcome, PausedRun):
            self._settle_paused(session, outcome)
        else:
            self._settle_terminal(session, outcome)

    def _settle_terminal(self, session: SessionBinding, outcome: TerminalRun) -> None:
        session = session.model_copy(
            update={
                "active_run_id": None,
                "last_terminal_run_id": outcome.receipt.run_id,
            }
        )
        self.store.save_session(session)
        logger.info(
            "gateway run %s settled %s",
            outcome.receipt.run_id,
            outcome.receipt.execution_state,
        )
        self._export_delivery(session, outcome)
        self._send_text(
            session,
            render_terminal(
                outcome, reply_artifact=self._reply_artifact_text(outcome.receipt)
            ),
        )
        self._auto_deliver_artifacts(session, outcome.receipt)

    def _reply_artifact_text(self, receipt: RunReceipt) -> str | None:
        """Terminal Delivery Guard (incidents 9c1c9abb / 77c45d0e): a run that
        ended without the model's final reply must not bury an already
        recorded business result. Reads the quant domain's reply marker
        (``artifacts/quant/briefs/last-reply.json``, written by
        ``record_decision_brief``), fresh for THIS run only (marker
        ``recorded_at`` >= run start — a stale marker from an earlier run is
        never re-delivered), bounded. Host-grounded presentation transport:
        the domain decides WHAT is the reply, the gateway only delivers it."""
        if receipt.execution_state == "completed":
            return None
        marker_path = (
            self.settings.workspace_root / "artifacts" / "quant" / "briefs"
            / "last-reply.json"
        )
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            recorded_at = datetime.fromisoformat(str(marker["recorded_at"]))
            text = str(marker["text"])
        except (OSError, ValueError, KeyError, TypeError):
            return None
        started_at = receipt.started_at
        if getattr(started_at, "tzinfo", None) is None and recorded_at.tzinfo is not None:
            started_at = started_at.replace(tzinfo=recorded_at.tzinfo)
        if recorded_at < started_at or not text.strip():
            return None
        return text.strip()[:REPLY_ARTIFACT_MAX_CHARS]

    def _export_delivery(self, session: SessionBinding, outcome: TerminalRun) -> None:
        """Caller-side durable delivery of a completed run's artifacts.

        Generic mechanical transport after settlement (Candidate C): export the
        receipt-listed artifacts to a caller-owned durable root before the
        surface transport completes. Execution truth stays ``completed``; a
        delivery failure is independently observable to the operator through
        the existing surface (a text error notice) — never a receipt rewrite,
        a new terminal state, an approval, or a new delivery schema.
        """
        try:
            export_receipt_artifacts(
                outcome,
                self.settings.workspace_root,
                self.settings.delivery_root,
            )
        except DeliveryExportError as exc:
            logger.error(
                "durable delivery failed for run %s: %s",
                outcome.receipt.run_id,
                exc,
            )
            self._send_text(
                session,
                render_error(
                    f"Durable delivery failed for run {outcome.receipt.run_id}: {exc}"
                ),
            )

    def _outbound_draft_content(
        self, session: SessionBinding, paused: PausedRun
    ) -> str | None:
        """Host-side read of the draft a pending ``send_to_customer`` proposes.
        Shape-validated draft_ref + case-scoped containment — never a model
        claim; the operator approves content they can see."""
        for entry in paused.pause_receipt.pending_approvals:
            if entry.get("tool_name") != "send_to_customer":
                continue
            args = entry.get("args") or {}
            draft_ref = args.get("draft_ref")
            case_id = args.get("case_id") or session.case_id
            if (
                not isinstance(draft_ref, str)
                or not _DRAFT_REF.fullmatch(draft_ref)
                or not isinstance(case_id, str)
                or not _CASE_ID.fullmatch(case_id)
            ):
                continue
            drafts_dir = (
                self.settings.workspace_root / "cases" / case_id / "drafts"
            ).resolve()
            path = (drafts_dir / draft_ref).resolve()
            if not path.is_relative_to(drafts_dir) or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            if len(text) > DRAFT_PREVIEW_MAX:
                return (
                    text[:DRAFT_PREVIEW_MAX]
                    + f"\n…(truncated — full text: {draft_ref})"
                )
            return text
        return None

    def _settle_paused(self, session: SessionBinding, paused: PausedRun) -> None:
        session = session.model_copy(
            update={
                "active_run_id": None,
                "paused_run_id": paused.pause_receipt.run_id,
            }
        )
        token = self.store.create_approval(
            session=session,
            paused_run_id=paused.pause_receipt.run_id,
            ttl_seconds=self.approval_ttl_seconds,
        )
        self.store.save_session(session)
        logger.info(
            "gateway run %s paused awaiting approval", paused.pause_receipt.run_id
        )
        batch = len(paused.pause_receipt.pending_approvals) > 1
        self.surface.send_approval(
            session.channel_id,
            text=render_pause(
                paused, content=self._outbound_draft_content(session, paused)
            ),
            approve_token=token,
            approve_label="Approve all" if batch else "Approve",
            deny_label="Deny all" if batch else "Deny",
        )

    # ── approval callbacks ──────────────────────────────────────────────────

    def _handle_callback(
        self, envelope: InboundEnvelope, session: SessionBinding
    ) -> None:
        if envelope.callback_action in CONTROL_CALLBACK_ACTIONS:
            # Supervisor control callback (zc:<action>:<payload>) — no
            # approval token, no run, never the model.
            self._handle_control_callback(envelope, session)
            return
        callback_id = envelope.transport_context.get("callback_query_id")
        decision = "approved" if envelope.callback_action == "approve" else "denied"
        try:
            binding = self.store.consume_approval(
                envelope.callback_token or "",
                decision=decision,
                user_id=envelope.user_id,
                channel_id=envelope.channel_id,
            )
        except ApprovalTokenError as exc:
            self._reject_callback(callback_id, session, str(exc))
            return
        if (
            session.paused_run_id is None
            or session.paused_run_id != binding.paused_run_id
        ):
            self._reject_callback(
                callback_id,
                session,
                "approval does not match this session's paused run",
            )
            return
        paused_run_id = binding.paused_run_id
        try:
            receipt = self.receipts.read(paused_run_id)
        except (FileNotFoundError, ValueError):
            receipt = None
        if receipt is None or getattr(receipt, "state", "terminal") != "paused":
            session = session.model_copy(update={"paused_run_id": None})
            self.store.save_session(session)
            self._reject_callback(callback_id, session, "run is no longer paused")
            return
        if callback_id:
            self.surface.answer_callback(
                callback_id,
                "Approved. Resuming…"
                if decision == "approved"
                else "Denied. Resuming…",
            )
        logger.info("approval consumed for paused run %s: %s", paused_run_id, decision)
        outcome = bridge.resume_for_surface(
            self.settings,
            paused_run_id,
            decision="approve" if decision == "approved" else "deny",
            reason=None if decision == "approved" else GATEWAY_DENY_REASON,
        )
        if isinstance(outcome, PausedRun):
            self._settle_paused(
                session.model_copy(update={"paused_run_id": None}), outcome
            )
            return
        session = session.model_copy(
            update={
                "paused_run_id": None,
                "last_terminal_run_id": outcome.receipt.run_id,
            }
        )
        self.store.save_session(session)
        logger.info(
            "gateway run %s settled %s (continued from %s)",
            outcome.receipt.run_id,
            outcome.receipt.execution_state,
            paused_run_id,
        )
        self._export_delivery(session, outcome)
        self._send_text(
            session,
            render_terminal(
                outcome, reply_artifact=self._reply_artifact_text(outcome.receipt)
            ),
        )
        self._auto_deliver_artifacts(session, outcome.receipt)

    def _reject_callback(
        self, callback_id: str | None, session: SessionBinding, message: str
    ) -> None:
        if callback_id:
            self.surface.answer_callback(callback_id, message)
        self._send_text(session, render_error(message))
        logger.info("approval callback rejected: %s", message)

    # ── commands ────────────────────────────────────────────────────────────

    def _handle_command(
        self, envelope: InboundEnvelope, session: SessionBinding
    ) -> None:
        command, _, argument = envelope.text.strip().partition(" ")
        command = command.removeprefix("/").lower().strip()
        argument = argument.strip()
        if command == "help":
            self._send_text(session, HELP_TEXT)
        elif command == "new":
            reset = self.store.reset_session(session)
            self._send_text(reset, render_new_conversation(reset.profile))
        elif command == "case":
            self._cmd_case(argument, session)
        elif command == "cases":
            self._cmd_cases(session)
        elif command == "unbind":
            self._cmd_unbind(session)
        elif command == "profile":
            self._cmd_profile(argument, session, chat_type=envelope.chat_type)
        elif command == "status":
            self._cmd_status(session)
        elif command == "inspect":
            self._cmd_inspect(session)
        elif command == "approve" or command == "deny":
            self._cmd_resume(session, decision=command)
        elif command == "artifacts":
            self._cmd_artifacts(session)
        else:
            self._handle_alias_command(envelope, session, command, argument)

    def _handle_alias_command(
        self,
        envelope: InboundEnvelope,
        session: SessionBinding,
        command: str,
        argument: str,
    ) -> None:
        """Profile alias from the routing configuration (e.g. ``/quant``):
        switch the session profile through the exact same ``/profile`` gate,
        then run the remaining text under it. Aliases are router data — the
        surface adapter never sees them."""
        alias_profile = self.routing.resolve_alias(command)
        if alias_profile is None:
            self._send_text(session, render_error(f"unknown command: /{command}"))
            return
        updated = self._cmd_profile(
            alias_profile, session, chat_type=envelope.chat_type
        )
        if updated is not None and argument:
            self._start_run(envelope.model_copy(update={"text": argument}), updated)

    # ── supervisor case control (deterministic, never the model) ────────────

    def _case_entries(self) -> list[tuple[str, str]]:
        """Enumerate case directories under the workspace cases root —
        filesystem facts only (most recent first). The gateway never imports
        the case plugin; the directory name IS the case_id."""
        root = self.settings.workspace_root / "cases"
        if not root.is_dir():
            return []
        stamped: list[tuple[float, str]] = []
        for entry in root.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            if len(name) > CASE_ID_MAX or not _CASE_ID.fullmatch(name):
                # not addressable through the callback channel — invisible to
                # /cases and unbindable by name, by contract
                continue
            marker = entry / "situation.json"
            stamp = (
                marker.stat().st_mtime if marker.is_file() else entry.stat().st_mtime
            )
            stamped.append((stamp, name))
        stamped.sort(reverse=True)
        return [
            (name, datetime.fromtimestamp(stamp, tz=UTC).strftime("%Y-%m-%d"))
            for stamp, name in stamped[:CASES_LIST_LIMIT]
        ]

    def _case_state_label(self, session: SessionBinding) -> str:
        if session.paused_run_id:
            return "PAUSED"
        if session.active_run_id:
            return "RUNNING"
        return "READY"

    def _send_case_card(self, session: SessionBinding) -> None:
        buttons: list[tuple[str, str]] = [
            ("Cases", f"{CONTROL_PREFIX}:cases:"),
            ("New conversation", f"{CONTROL_PREFIX}:new:"),
        ]
        if session.case_id:
            buttons.append(("Unbind case", f"{CONTROL_PREFIX}:unbind:"))
        self.surface.send_keyboard(
            session.channel_id,
            text=render_case_card(
                case_id=session.case_id,
                profile=session.profile,
                conversation_id=session.conversation_id,
                state=self._case_state_label(session),
            ),
            buttons=buttons,
        )

    def _bind_case(
        self, session: SessionBinding, case_id: str
    ) -> tuple[SessionBinding, str | None]:
        """Deterministic bind (or error). Membership in the cases-root listing
        is the whole validation — a name that is not an existing
        callback-addressable directory can never be bound, which also
        structurally rules out path traversal and framing breakage."""
        if session.paused_run_id:
            return session, CASE_BLOCKED_BY_PAUSE
        known = {name for name, _ in self._case_entries()}
        if case_id not in known:
            return session, f"unknown case: {case_id} (see /cases)"
        return self.store.bind_case(session, case_id), None

    def _unbind_case(
        self, session: SessionBinding
    ) -> tuple[SessionBinding, str | None]:
        if session.paused_run_id:
            return session, CASE_BLOCKED_BY_PAUSE
        return self.store.bind_case(session, None), None

    def _cmd_case(self, argument: str, session: SessionBinding) -> None:
        if not argument:
            self._send_case_card(session)
            return
        session, error = self._bind_case(session, argument)
        if error:
            self._send_text(session, render_error(error))
            return
        logger.info("supervisor bound session to case %s", argument)
        self._send_case_card(session)

    def _cmd_cases(self, session: SessionBinding) -> None:
        entries = self._case_entries()
        buttons = [
            (f"Bind {name}", f"{CONTROL_PREFIX}:bind:{name}") for name, _ in entries
        ]
        self.surface.send_keyboard(
            session.channel_id,
            text=render_cases(entries, bound_case=session.case_id),
            buttons=buttons,
        )

    def _cmd_unbind(self, session: SessionBinding) -> None:
        session, error = self._unbind_case(session)
        if error:
            self._send_text(session, render_error(error))
            return
        logger.info("supervisor unbound session case")
        self._send_case_card(session)

    def _handle_control_callback(
        self, envelope: InboundEnvelope, session: SessionBinding
    ) -> None:
        """zc:<action>:<payload> — supervisor buttons. Same deterministic
        operations as the slash commands; every callback gets answered.

        UX invariant (deliberately no token/TTL machinery): supervisor
        buttons never expire, so a stale tap is allowed — every
        state-changing control callback re-checks the CURRENT session state
        (pause guard, live cases-root membership) instead of trusting the
        button's age. ``new`` rotates the conversation on tap by design."""
        callback_id = envelope.transport_context.get("callback_query_id")
        action = envelope.callback_action
        if action == "new":
            reset = self.store.reset_session(session)
            if callback_id:
                self.surface.answer_callback(callback_id, "New conversation.")
            self._send_text(reset, render_new_conversation(reset.profile))
            return
        if action == "cases":
            if callback_id:
                self.surface.answer_callback(callback_id, "Cases…")
            self._cmd_cases(session)
            return
        if action == "unbind":
            updated, error = self._unbind_case(session)
            if error:
                self._reject_callback(callback_id, updated, error)
                return
            if callback_id:
                self.surface.answer_callback(callback_id, "Case unbound.")
            logger.info("supervisor unbound session case (button)")
            self._send_case_card(updated)
            return
        # bind
        case_id = envelope.callback_payload or ""
        updated, error = self._bind_case(session, case_id)
        if error:
            self._reject_callback(callback_id, updated, error)
            return
        if callback_id:
            self.surface.answer_callback(callback_id, f"Bound case {case_id}.")
        logger.info("supervisor bound session to case %s (button)", case_id)
        self._send_case_card(updated)

    def _cmd_profile(
        self,
        argument: str,
        session: SessionBinding,
        *,
        chat_type: str | None = None,
    ) -> SessionBinding | None:
        if not argument:
            self._send_text(
                session,
                render_profile(
                    current=session.profile,
                    available=list_profiles(self.config_root),
                ),
            )
            return None
        if session.paused_run_id:
            self._send_text(session, render_error(PROFILE_BLOCKED_BY_PAUSE))
            return None
        try:
            bridge.validate_profile(
                argument, self.settings, config_root=self.config_root
            )
        except CompositionError as exc:
            self._send_text(session, render_error(str(exc)))
            return None
        # Profile admission (spec pack 00 §3): a restricted profile may not
        # even be BOUND on a disallowed surface/chat type/channel — the DM
        # quant attempt dies here, before any agent execution.
        denial = self.routing.access_error(
            argument,
            surface=session.surface,
            chat_type=chat_type,
            channel_id=session.channel_id,
        )
        if denial is not None:
            self._send_text(session, render_error(denial))
            return None
        session = session.model_copy(update={"profile": argument})
        self.store.save_session(session)
        self._send_text(
            session,
            render_profile(
                current=session.profile, available=list_profiles(self.config_root)
            ),
        )
        return session

    # ── progress bridging ───────────────────────────────────────────────────

    def _start_progress_watchdog(self, session: SessionBinding, run_id: str) -> None:
        """One daemon watchdog thread per run (progress telemetry v0.1):
        fires the arithmetic-backoff checkpoint schedule seeded by the two
        progress configs, each deadline anchored to ``time.monotonic()``
        watchdog start so render/send latency never drifts later
        checkpoints. At most one line per checkpoint; cancelled on settle;
        never touches the execution path."""
        first = self.run_progress_seconds
        second = self.run_progress_seconds_2
        if first is None or first <= 0:
            return  # bridge disabled (startup validation covers bad schedules)
        if second is None or second <= first:
            return
        stop = threading.Event()
        with self._progress_lock:
            self._progress_stops[run_id] = stop

        def watchdog() -> None:
            start = time.monotonic()
            n = 0
            while True:
                n += 1
                wait = start + progress_checkpoint_seconds(first, second, n) - time.monotonic()
                if stop.wait(max(0.0, wait)):
                    return
                with self._progress_lock:
                    if self._progress_stops.get(run_id) is not stop:
                        return  # already settled and cleaned up
                text = render_run_progress(
                    **self._progress_facts(
                        run_id, elapsed_seconds=int(time.monotonic() - start)
                    )
                )
                try:
                    self._send_text(session, text)
                except Exception as exc:  # noqa: BLE001 — bridging is non-fatal
                    logger.warning("progress ping failed for run %s: %s", run_id, exc)

        threading.Thread(target=watchdog, name=f"progress-{run_id[:8]}", daemon=True).start()

    def _stop_progress_watchdog(self, run_id: str) -> None:
        with self._progress_lock:
            stop = self._progress_stops.pop(run_id, None)
        if stop is not None:
            stop.set()

    def _progress_facts(self, run_id: str, *, elapsed_seconds: int = 0) -> dict:
        """Read persisted operational facts for one run; anything unreadable
        stays out of the sentence (never invented). Usage is cumulative
        settled provider-reported usage from the shared projector — it is
        omitted entirely when the correlation is absent or ambiguous."""
        facts: dict = {"elapsed_seconds": elapsed_seconds}
        try:
            from ..web.projector import activity_view, build_timeline, live_usage
            from ..web.readers import load_run_facts

            load = load_run_facts(self.settings, run_id)
            run_facts = _run_coro(load)
            if run_facts is None:
                return facts
            timeline = build_timeline(run_facts)
            requests = sum(
                1 for row in timeline if row.kind == "model_request" and row.finished_at is not None
            )
            if requests:
                facts["requests"] = requests
            tool_call_ids = {
                row.id for row in timeline if row.kind == "tool_call"
            }
            if tool_call_ids:
                facts["tool_calls"] = len(tool_call_ids)
            started = [
                row for row in timeline
                if row.kind == "tool_call" and row.status == "started"
            ]
            if started:
                facts["tool_name"] = started[-1].title
            activity = activity_view(run_facts)
            if activity == "SETTLING":
                facts.pop("tool_name", None)
            usage = live_usage(run_facts)
            if usage:
                facts["usage"] = usage
        except Exception as exc:  # noqa: BLE001 — facts are best-effort
            logger.info("progress facts unavailable for run %s: %s", run_id, exc)
        return facts

    def _cmd_inspect(self, session: SessionBinding) -> None:
        from ..web.inspection import render_inspection_markdown, render_run_json

        if not session.last_terminal_run_id:
            self._send_text(session, "No terminal run in this session to inspect.")
            return
        try:
            inspection = render_run_json(session.last_terminal_run_id, settings=self.settings)
            text = render_inspection_markdown(inspection, max_chars=7500)
        except (LookupError, OSError, ValueError) as exc:
            text = render_error(f"Inspection unavailable: {str(exc)[:300]}")
        self._send_text(session, text)

    def _cmd_status(self, session: SessionBinding) -> None:
        # Fully host-grounded: receipts only, never the model.
        if session.paused_run_id:
            receipt = self._read_receipt_or_none(session.paused_run_id)
            if (
                not isinstance(receipt, PauseReceipt)
                or getattr(receipt, "state", "") != "paused"
            ):
                session = session.model_copy(update={"paused_run_id": None})
                self.store.save_session(session)
                self._send_text(
                    session,
                    render_status(
                        profile=session.profile,
                        conversation_id=session.conversation_id,
                        case_id=session.case_id,
                        state="READY",
                    ),
                )
                return
            self._send_text(
                session,
                render_status(
                    profile=session.profile,
                    conversation_id=session.conversation_id,
                    case_id=session.case_id,
                    state="PAUSED",
                    run_id=session.paused_run_id,
                    pending_approval_count=len(receipt.pending_approvals),
                    pending_tools=[
                        entry.get("tool_name") or "unknown-tool"
                        for entry in receipt.pending_approvals
                    ],
                ),
            )
            return
        if session.active_run_id:
            self._send_text(
                session,
                render_status(
                    profile=session.profile,
                    conversation_id=session.conversation_id,
                    case_id=session.case_id,
                    state="RUNNING",
                    run_id=session.active_run_id,
                ),
            )
            return
        if session.last_terminal_run_id:
            receipt = self._read_receipt_or_none(session.last_terminal_run_id)
            if receipt is None:
                session = session.model_copy(update={"last_terminal_run_id": None})
                self.store.save_session(session)
                self._send_text(
                    session,
                    render_status(
                        profile=session.profile,
                        conversation_id=session.conversation_id,
                        case_id=session.case_id,
                        state="READY",
                    ),
                )
                return
            if not isinstance(receipt, RunReceipt):
                session = session.model_copy(update={"last_terminal_run_id": None})
                self.store.save_session(session)
                self._send_text(
                    session,
                    render_status(
                        profile=session.profile,
                        conversation_id=session.conversation_id,
                        case_id=session.case_id,
                        state="READY",
                    ),
                )
                return
            state = {
                "completed": "LAST COMPLETED",
                "failed": "LAST FAILED",
                "limit_reached": "LAST LIMIT REACHED",
            }[receipt.execution_state]
            self._send_text(
                session,
                render_status(
                    profile=session.profile,
                    conversation_id=session.conversation_id,
                    case_id=session.case_id,
                    state=state,
                    run_id=session.last_terminal_run_id,
                ),
            )
            return
        self._send_text(
            session,
            render_status(
                profile=session.profile,
                conversation_id=session.conversation_id,
                case_id=session.case_id,
                state="READY",
            ),
        )

    def _cmd_resume(self, session: SessionBinding, *, decision: str) -> None:
        if not session.paused_run_id:
            self._send_text(session, NOTHING_TO_APPROVE)
            return
        paused_run_id = session.paused_run_id
        outcome = bridge.resume_for_surface(
            self.settings,
            paused_run_id,
            decision=decision,  # type: ignore[arg-type]
            reason=None if decision == "approve" else GATEWAY_DENY_REASON,
        )
        # The slash command consumed the interactive gate: stale buttons die.
        self.store.expire_approvals_for_run(paused_run_id)
        if isinstance(outcome, PausedRun):
            self._settle_paused(
                session.model_copy(update={"paused_run_id": None}), outcome
            )
            return
        session = session.model_copy(
            update={
                "paused_run_id": None,
                "last_terminal_run_id": outcome.receipt.run_id,
            }
        )
        self.store.save_session(session)
        logger.info(
            "gateway run %s settled %s (continued from %s)",
            outcome.receipt.run_id,
            outcome.receipt.execution_state,
            paused_run_id,
        )
        self._export_delivery(session, outcome)
        self._send_text(
            session,
            render_terminal(
                outcome, reply_artifact=self._reply_artifact_text(outcome.receipt)
            ),
        )
        self._auto_deliver_artifacts(session, outcome.receipt)

    def _cmd_artifacts(self, session: SessionBinding) -> None:
        if not session.last_terminal_run_id:
            self._send_text(session, "No completed run yet.")
            return
        receipt = self._read_receipt_or_none(session.last_terminal_run_id)
        if receipt is None:
            self._send_text(session, "No receipt found for the last run.")
            return
        self._send_receipt_artifacts(session, receipt)

    def _send_receipt_artifacts(
        self, session: SessionBinding, receipt: RunReceipt
    ) -> None:
        """One generic receipt-aware artifact send loop (spec pack 08).

        Shared by the manual ``/artifacts`` recovery command and automatic
        terminal delivery: containment inside the workspace, existing file,
        size within the surface limit — the same checks for both paths, no
        duplication. Oversize/nonexistent/outside-workspace entries are
        never uploaded; a text notice is sent instead.
        """
        verified = receipt.artifact_facts
        if not verified:
            self._send_text(session, "No artifact byte facts.")
            return
        workspace = self.settings.workspace_root.resolve()
        for artifact in verified:
            path = (workspace / artifact.path).resolve()
            contained = path.is_relative_to(workspace)
            if (
                contained
                and path.is_file()
                and path.stat().st_size <= self.max_artifact_bytes
            ):
                self.surface.send_document(
                    session.channel_id, path, caption=artifact.path
                )
            else:
                self._send_text(session, f"{artifact.path} ({artifact.size} bytes)")

    def _auto_deliver_artifacts(
        self, session: SessionBinding, receipt: RunReceipt
    ) -> None:
        """Automatic terminal artifact delivery (spec pack 08, H3/H5/H6).

        Enabled deployments send the settled run's eligible artifacts right
        after the terminal text — no second user command. Delivery runs only
        for completed runs; a send failure is logged and reported as a short
        transport warning and never rewrites the settled execution truth.
        """
        if not self.auto_artifacts or receipt.execution_state != "completed":
            return
        if not receipt.artifact_facts:
            return
        try:
            self._send_receipt_artifacts(session, receipt)
        except Exception as exc:  # noqa: BLE001 - transport-only, never fatal
            logger.error(
                "automatic artifact delivery failed for run %s: %s",
                receipt.run_id,
                exc,
            )
            try:
                self._send_text(
                    session,
                    render_error(
                        "Artifact delivery failed — use /artifacts to retry."
                    ),
                )
            except Exception as exc:  # noqa: BLE001 - even the notice is best-effort
                logger.warning(
                    "artifact failure notice not delivered for run %s: %s",
                    receipt.run_id,
                    exc,
                )

    # ── restart recovery ────────────────────────────────────────────────────

    def recover_sessions(self) -> list[str]:
        """SPEC §65–§66: reconcile routing state against the ReceiptStore."""
        warnings: list[str] = []
        for session in self.store.list_sessions():
            run_id = session.paused_run_id or session.active_run_id
            if run_id is None:
                continue
            receipt = self._read_receipt_or_none(run_id)
            if receipt is None:
                warnings.append(
                    f"routing state referenced a run without a receipt: {run_id}"
                )
                self.store.save_session(
                    session.model_copy(
                        update={"active_run_id": None, "paused_run_id": None}
                    )
                )
            elif getattr(receipt, "state", "terminal") == "paused":
                self.store.save_session(
                    session.model_copy(
                        update={"active_run_id": None, "paused_run_id": receipt.run_id}
                    )
                )
            else:
                self.store.save_session(
                    session.model_copy(
                        update={
                            "active_run_id": None,
                            "paused_run_id": None,
                            "last_terminal_run_id": receipt.run_id,
                        }
                    )
                )
        return warnings

    def _read_receipt_or_none(self, run_id: str):
        try:
            return self.receipts.read(run_id)
        except (FileNotFoundError, ValueError):
            return None
