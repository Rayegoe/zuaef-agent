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

import logging
from pathlib import Path
from uuid import uuid4

from ..composition import CompositionError
from ..config import AgentSettings
from ..profiles import list_profiles
from ..receipt_store import ReceiptStore
from ..runtime import PausedRun, TerminalRun
from . import bridge
from .models import InboundEnvelope, SessionBinding
from .renderer import (
    chunk_text,
    render_error,
    render_new_conversation,
    render_pause,
    render_profile,
    render_status,
    render_terminal,
)
from .store import ApprovalTokenError, GatewayStore
from .surface import SurfaceAdapter

logger = logging.getLogger(__name__)

HELP_TEXT = """\
ZUAEF

Send a task normally.

Commands:
/new
/profile [name]
/status
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

NOTHING_TO_APPROVE = "Nothing is awaiting approval."

GATEWAY_DENY_REASON = "denied by operator from gateway"


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
    ):
        self.settings = settings
        self.store = store
        self.surface = surface
        self.default_profile = default_profile
        self.config_root = config_root
        self.approval_ttl_seconds = approval_ttl_seconds
        self.max_artifact_bytes = max_artifact_bytes
        self.allowed_user_ids = allowed_user_ids
        self.receipts = ReceiptStore(settings.state_root)

    # ── dispatch ────────────────────────────────────────────────────────────

    def handle(self, envelope: InboundEnvelope) -> None:
        if (
            self.allowed_user_ids is not None
            and envelope.user_id not in self.allowed_user_ids
        ):
            logger.info("service rejected inbound from unauthorized user %s", envelope.user_id)
            return
        session = self.store.get_or_create_session(
            surface=envelope.surface,
            tenant_id=envelope.tenant_id,
            user_id=envelope.user_id,
            channel_id=envelope.channel_id,
            thread_id=envelope.thread_id,
            default_profile=self.default_profile,
        )
        if envelope.callback_token is not None and envelope.callback_action is not None:
            self._handle_callback(envelope, session)
            return
        text = envelope.text.strip()
        if text.startswith("/"):
            self._handle_command(text, session)
            return
        if session.paused_run_id:
            self._send_text(session, WAITING_FOR_APPROVAL)
            return
        self._start_run(envelope, session)

    def _send_text(self, session: SessionBinding, text: str) -> None:
        for chunk in chunk_text(text):
            self.surface.send_text(session.channel_id, chunk)

    # ── run start ───────────────────────────────────────────────────────────

    def _start_run(self, envelope: InboundEnvelope, session: SessionBinding) -> None:
        run_id = uuid4().hex
        session = session.model_copy(update={"active_run_id": run_id})
        self.store.save_session(session)
        # Normal-turn continuity (SPEC §15 / T010): a follow-up message in the
        # same conversation resumes the prior terminal run's real history from
        # public persistence — a fresh run_id, the same conversation_id.
        history = (
            bridge.prior_run_history(
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
                profile=session.profile,
                prompt=bridge.project_prompt(envelope),
                conversation_id=session.conversation_id,
                config_root=self.config_root,
                run_id=run_id,
                message_history=history,
                # Deterministic Case binding: the session's bound case is
                # threaded into the run's CoreDeps — the model never guesses it.
                case_id=session.case_id,
            )
        except CompositionError as exc:
            session = session.model_copy(update={"active_run_id": None})
            self.store.save_session(session)
            self._send_text(session, render_error(str(exc)))
            return
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
        logger.info("gateway run %s settled %s", outcome.receipt.run_id, outcome.receipt.status)
        self._send_text(session, render_terminal(outcome))

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
        logger.info("gateway run %s paused awaiting approval", paused.pause_receipt.run_id)
        batch = len(paused.pause_receipt.pending_approvals) > 1
        self.surface.send_approval(
            session.channel_id,
            text=render_pause(paused),
            approve_token=token,
            approve_label="Approve all" if batch else "Approve",
            deny_label="Deny all" if batch else "Deny",
        )

    # ── approval callbacks ──────────────────────────────────────────────────

    def _handle_callback(
        self, envelope: InboundEnvelope, session: SessionBinding
    ) -> None:
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
        if session.paused_run_id is None or session.paused_run_id != binding.paused_run_id:
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
                "Approved. Resuming…" if decision == "approved" else "Denied. Resuming…",
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
            outcome.receipt.status,
            paused_run_id,
        )
        self._send_text(session, render_terminal(outcome))

    def _reject_callback(
        self, callback_id: str | None, session: SessionBinding, message: str
    ) -> None:
        if callback_id:
            self.surface.answer_callback(callback_id, message)
        self._send_text(session, render_error(message))
        logger.info("approval callback rejected: %s", message)

    # ── commands ────────────────────────────────────────────────────────────

    def _handle_command(self, text: str, session: SessionBinding) -> None:
        command, _, argument = text.partition(" ")
        command = command.removeprefix("/").lower().strip()
        argument = argument.strip()
        if command == "help":
            self._send_text(session, HELP_TEXT)
        elif command == "new":
            reset = self.store.reset_session(session)
            self._send_text(reset, render_new_conversation(reset.profile))
        elif command == "profile":
            self._cmd_profile(argument, session)
        elif command == "status":
            self._cmd_status(session)
        elif command == "approve" or command == "deny":
            self._cmd_resume(session, decision=command)
        elif command == "artifacts":
            self._cmd_artifacts(session)
        else:
            self._send_text(session, render_error(f"unknown command: /{command}"))

    def _cmd_profile(self, argument: str, session: SessionBinding) -> None:
        if not argument:
            self._send_text(
                session,
                render_profile(
                    current=session.profile,
                    available=list_profiles(self.config_root),
                ),
            )
            return
        if session.paused_run_id:
            self._send_text(session, render_error(PROFILE_BLOCKED_BY_PAUSE))
            return
        try:
            bridge.validate_profile(argument, self.settings, config_root=self.config_root)
        except CompositionError as exc:
            self._send_text(session, render_error(str(exc)))
            return
        session = session.model_copy(update={"profile": argument})
        self.store.save_session(session)
        self._send_text(
            session,
            render_profile(
                current=session.profile, available=list_profiles(self.config_root)
            ),
        )

    def _cmd_status(self, session: SessionBinding) -> None:
        # Fully host-grounded: receipts only, never the model.
        if session.paused_run_id:
            receipt = self._read_receipt_or_none(session.paused_run_id)
            if receipt is None or getattr(receipt, "state", "") != "paused":
                session = session.model_copy(update={"paused_run_id": None})
                self.store.save_session(session)
                self._send_text(session, render_status(
                    profile=session.profile,
                    conversation_id=session.conversation_id,
                    state="READY",
                ))
                return
            self._send_text(
                session,
                render_status(
                    profile=session.profile,
                    conversation_id=session.conversation_id,
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
                self._send_text(session, render_status(
                    profile=session.profile,
                    conversation_id=session.conversation_id,
                    state="READY",
                ))
                return
            state = {
                "completed": "LAST COMPLETED",
                "partial": "LAST PARTIAL",
                "blocked": "LAST BLOCKED",
            }[receipt.status]
            self._send_text(
                session,
                render_status(
                    profile=session.profile,
                    conversation_id=session.conversation_id,
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
            outcome.receipt.status,
            paused_run_id,
        )
        self._send_text(session, render_terminal(outcome))

    def _cmd_artifacts(self, session: SessionBinding) -> None:
        if not session.last_terminal_run_id:
            self._send_text(session, "No completed run yet.")
            return
        receipt = self._read_receipt_or_none(session.last_terminal_run_id)
        if receipt is None:
            self._send_text(session, "No receipt found for the last run.")
            return
        verified = receipt.verified_artifacts
        if not verified:
            self._send_text(session, "No verified artifacts.")
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
                self._send_text(
                    session, f"{artifact.path} ({artifact.size} bytes)"
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
