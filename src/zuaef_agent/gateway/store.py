"""Gateway routing-state store — SPEC v0.3 §9–§12.

A single SQLite database (``.zuaef-state/gateway.sqlite3``) holding ONLY
surface routing state: session bindings, the surface cursor (Telegram
``update_id`` offset) and opaque approval tokens (SHA-256 of the raw token).
Execution truth (receipts, step history, tool effects, artifacts) is never
copied here — the ReceiptStore and StepPersistence remain the authority.

No ORM, no migration framework: ``PRAGMA user_version = 1``.
"""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from uuid import uuid4

from .models import ApprovalBinding, SessionBinding

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_bindings (
    surface TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    thread_key TEXT NOT NULL,

    conversation_id TEXT NOT NULL,
    profile TEXT,
    case_id TEXT,

    active_run_id TEXT,
    paused_run_id TEXT,
    last_terminal_run_id TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    PRIMARY KEY (
        surface,
        tenant_id,
        channel_id,
        thread_key
    )
);

CREATE TABLE IF NOT EXISTS approval_bindings (
    token_hash TEXT PRIMARY KEY,

    surface TEXT NOT NULL,
    user_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,

    paused_run_id TEXT NOT NULL,

    state TEXT NOT NULL,

    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);

CREATE TABLE IF NOT EXISTS surface_offsets (
    surface TEXT PRIMARY KEY,
    cursor TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


class ApprovalTokenError(ValueError):
    """An approval token cannot authorize a resume (missing, expired, consumed
    or bound to a different user/channel)."""


class GatewayStore:
    """SQLite-backed routing state for the Gateway."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        """Idempotent column migrations for databases created by earlier
        releases (no migration framework — SPEC §9)."""
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(session_bindings)")
        }
        if "case_id" not in columns:
            self._conn.execute(
                "ALTER TABLE session_bindings ADD COLUMN case_id TEXT"
            )

    def close(self) -> None:
        self._conn.close()

    # ── session bindings ────────────────────────────────────────────────────

    @staticmethod
    def normalize_thread_key(thread_id: str | None) -> str:
        """``thread_id=None`` normalizes to ``""`` to avoid NULL composite keys."""
        return thread_id or ""

    def get_or_create_session(
        self,
        *,
        surface: str,
        tenant_id: str,
        user_id: str,
        channel_id: str,
        thread_id: str | None,
        default_profile: str | None,
    ) -> SessionBinding:
        thread_key = self.normalize_thread_key(thread_id)
        row = self._conn.execute(
            "SELECT * FROM session_bindings "
            "WHERE surface = ? AND tenant_id = ? AND channel_id = ? AND thread_key = ?",
            (surface, tenant_id, channel_id, thread_key),
        ).fetchone()
        if row is not None:
            return self._session_from_row(row)
        binding = SessionBinding(
            surface=surface,
            tenant_id=tenant_id,
            user_id=user_id,
            channel_id=channel_id,
            thread_key=thread_key,
            conversation_id=uuid4().hex,
            profile=default_profile,
        )
        self.save_session(binding)
        return binding

    def save_session(self, binding: SessionBinding) -> None:
        now = _iso(_now())
        self._conn.execute(
            """
            INSERT INTO session_bindings (
                surface, tenant_id, user_id, channel_id, thread_key,
                conversation_id, profile, case_id,
                active_run_id, paused_run_id, last_terminal_run_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (surface, tenant_id, channel_id, thread_key) DO UPDATE SET
                -- First writer owns the session: the binding creator stays the
                -- approval-token owner even when colleagues speak in the same
                -- group afterwards (Feishu groups are multi-operator).
                user_id = session_bindings.user_id,
                conversation_id = excluded.conversation_id,
                profile = excluded.profile,
                case_id = excluded.case_id,
                active_run_id = excluded.active_run_id,
                paused_run_id = excluded.paused_run_id,
                last_terminal_run_id = excluded.last_terminal_run_id,
                updated_at = excluded.updated_at
            """,
            (
                binding.surface,
                binding.tenant_id,
                binding.user_id,
                binding.channel_id,
                binding.thread_key,
                binding.conversation_id,
                binding.profile,
                binding.case_id,
                binding.active_run_id,
                binding.paused_run_id,
                binding.last_terminal_run_id,
                now,
                now,
            ),
        )
        self._conn.commit()

    def bind_case(
        self,
        session: SessionBinding,
        case_id: str | None,
    ) -> SessionBinding:
        """Deterministic supervisor operation: bind (or unbind, with ``None``)
        this channel/thread to one Case. Conversation identity is untouched;
        the model can never bind itself to a Case (SPEC v1.0 §5.4)."""
        updated = session.model_copy(update={"case_id": case_id})
        self.save_session(updated)
        return updated

    def get_session(
        self,
        *,
        surface: str,
        tenant_id: str,
        user_id: str,
        channel_id: str,
        thread_id: str | None,
    ) -> SessionBinding | None:
        row = self._conn.execute(
            "SELECT * FROM session_bindings "
            "WHERE surface = ? AND tenant_id = ? AND channel_id = ? AND thread_key = ?",
            (surface, tenant_id, channel_id, self.normalize_thread_key(thread_id)),
        ).fetchone()
        return self._session_from_row(row) if row is not None else None

    def list_sessions(self) -> list[SessionBinding]:
        rows = self._conn.execute(
            "SELECT * FROM session_bindings ORDER BY updated_at"
        ).fetchall()
        return [self._session_from_row(row) for row in rows]

    def reset_session(self, session: SessionBinding) -> SessionBinding:
        """Start a fresh conversation in the same session: invalidate the
        paused run's pending approval tokens, clear run pointers, mint a new
        conversation_id, keep the profile. The business Case binding survives
        a ``/new`` unless a supervisor explicitly unbinds it (SPEC v1.0 §5.3).
        The old PauseReceipt is untouched — it remains historical evidence."""
        if session.paused_run_id:
            self.expire_approvals_for_run(session.paused_run_id)
        updated = session.model_copy(
            update={
                "conversation_id": uuid4().hex,
                "active_run_id": None,
                "paused_run_id": None,
                "last_terminal_run_id": None,
            }
        )
        self.save_session(updated)
        return updated

    @staticmethod
    def _session_from_row(row: sqlite3.Row) -> SessionBinding:
        return SessionBinding(
            surface=row["surface"],
            tenant_id=row["tenant_id"],
            user_id=row["user_id"],
            channel_id=row["channel_id"],
            thread_key=row["thread_key"],
            conversation_id=row["conversation_id"],
            profile=row["profile"],
            case_id=row["case_id"],
            active_run_id=row["active_run_id"],
            paused_run_id=row["paused_run_id"],
            last_terminal_run_id=row["last_terminal_run_id"],
        )

    # ── surface cursors ─────────────────────────────────────────────────────

    def get_cursor(self, surface: str) -> str | None:
        row = self._conn.execute(
            "SELECT cursor FROM surface_offsets WHERE surface = ?", (surface,)
        ).fetchone()
        return row["cursor"] if row is not None else None

    def set_cursor(self, surface: str, cursor: str) -> None:
        self._conn.execute(
            """
            INSERT INTO surface_offsets (surface, cursor, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT (surface) DO UPDATE SET
                cursor = excluded.cursor,
                updated_at = excluded.updated_at
            """,
            (surface, cursor, _iso(_now())),
        )
        self._conn.commit()

    # ── approval tokens ─────────────────────────────────────────────────────

    def create_approval(
        self,
        *,
        session: SessionBinding,
        paused_run_id: str,
        ttl_seconds: int,
    ) -> str:
        """Mint an opaque callback token; the database stores only its SHA-256."""
        raw_token = secrets.token_urlsafe(16)
        now = _now()
        self._conn.execute(
            """
            INSERT INTO approval_bindings (
                token_hash, surface, user_id, channel_id, paused_run_id,
                state, created_at, expires_at, consumed_at
            ) VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, NULL)
            """,
            (
                self._hash_token(raw_token),
                session.surface,
                session.user_id,
                session.channel_id,
                paused_run_id,
                _iso(now),
                _iso(now + self._ttl_delta(ttl_seconds)),
            ),
        )
        self._conn.commit()
        return raw_token

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    @staticmethod
    def _ttl_delta(ttl_seconds: int) -> timedelta:
        return timedelta(seconds=ttl_seconds)

    def resolve_approval(self, raw_token: str) -> ApprovalBinding | None:
        """Look up a token by hash; lazily marks pending tokens expired."""
        row = self._conn.execute(
            "SELECT * FROM approval_bindings WHERE token_hash = ?",
            (self._hash_token(raw_token),),
        ).fetchone()
        if row is None:
            return None
        binding = self._approval_from_row(row)
        if binding.state == "pending" and binding.expires_at <= _now():
            self._conn.execute(
                "UPDATE approval_bindings SET state = 'expired' WHERE token_hash = ?",
                (binding.token_hash,),
            )
            self._conn.commit()
            binding = binding.model_copy(update={"state": "expired"})
        return binding

    def consume_approval(
        self,
        raw_token: str,
        *,
        decision: Literal["approved", "denied"],
        user_id: str | None = None,
        channel_id: str | None = None,
    ) -> ApprovalBinding:
        """Atomically consume a pending token; any failure raises and must NOT
        resume the run (SPEC §12)."""
        binding = self.resolve_approval(raw_token)
        if binding is None:
            raise ApprovalTokenError("unknown approval token")
        if binding.state != "pending":
            raise ApprovalTokenError(f"approval token already {binding.state}")
        if user_id is not None and binding.user_id != user_id:
            raise ApprovalTokenError("approval token belongs to another user")
        if channel_id is not None and binding.channel_id != channel_id:
            raise ApprovalTokenError("approval token belongs to another channel")
        now = _iso(_now())
        cursor = self._conn.execute(
            "UPDATE approval_bindings SET state = ?, consumed_at = ? "
            "WHERE token_hash = ? AND state = 'pending'",
            (decision, now, binding.token_hash),
        )
        self._conn.commit()
        if cursor.rowcount != 1:
            raise ApprovalTokenError("approval token was already consumed")
        return self._approval_from_row(
            self._conn.execute(
                "SELECT * FROM approval_bindings WHERE token_hash = ?",
                (binding.token_hash,),
            ).fetchone()
        )

    def expire_approvals_for_run(self, paused_run_id: str) -> None:
        """Invalidate every pending token of a paused run (used by ``/new``)."""
        self._conn.execute(
            "UPDATE approval_bindings SET state = 'expired', consumed_at = ? "
            "WHERE paused_run_id = ? AND state = 'pending'",
            (_iso(_now()), paused_run_id),
        )
        self._conn.commit()

    @staticmethod
    def _approval_from_row(row: sqlite3.Row) -> ApprovalBinding:
        return ApprovalBinding(
            token_hash=row["token_hash"],
            surface=row["surface"],
            user_id=row["user_id"],
            channel_id=row["channel_id"],
            paused_run_id=row["paused_run_id"],
            state=row["state"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]),
            consumed_at=(
                datetime.fromisoformat(row["consumed_at"])
                if row["consumed_at"]
                else None
            ),
        )
