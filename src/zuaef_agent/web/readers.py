"""Store access for the web console.

Opens the public store APIs only — ``pydantic_ai_harness`` ``FileStepStore``
and the ZUAEF ``ReceiptStore`` — and merges them into :class:`RunFacts` for
the projector. This module never parses private file layout and never writes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from pydantic import ValidationError
from pydantic_ai_harness.step_persistence import (
    ContinuableSnapshot,
    FileStepStore,
    StepEvent,
    ToolEffectRecord,
)

from ..config import AgentSettings
from ..models import AnyReceipt, PauseReceipt, RunReceipt
from ..receipt_store import ReceiptStore
from .projector import RunFacts, derive_run_status, timestamp_sort_key

logger = logging.getLogger(__name__)

# Bounded list page (API-CONTRACT §3): default page size with a hard ceiling.
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def open_step_store(settings: AgentSettings) -> FileStepStore:
    return FileStepStore(settings.step_store_dir)


# Same charset contract as ReceiptStore.path_for — reject junk before it
# becomes a filename.
_VALID_RUN_ID_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
)


def _receipt_path(settings: AgentSettings, run_id: str) -> Path:
    if not run_id or any(ch not in _VALID_RUN_ID_CHARS for ch in run_id):
        raise ValueError(f"invalid run_id: {run_id!r}")
    return settings.state_root / "receipts" / f"{run_id}.json"


def _load_receipt(path: Path) -> tuple[AnyReceipt | None, str | None]:
    """Best-effort receipt read: ``(receipt, diagnostic)``.

    A receipt the current runtime cannot parse (foreign/old schema_version,
    corrupt JSON) is IGNORED — it only loses receipt-derived facts
    (settlement verdict, artifacts, composition, aggregate usage). It never
    masks StepPersistence facts: events and the tool ledger are read
    independently of this result. No legacy model, migration or compat
    schema exists; the diagnostic is a transient projection note.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return None, None  # no receipt persisted — normal, not a warning
    except (json.JSONDecodeError, ValueError) as exc:
        # Debug, not warning: real state holds ~110 legacy receipts and a
        # polled console would flood its own log; the returned diagnostic is
        # the operator-visible surface.
        warning = f"receipt_unavailable: unreadable ({exc})"
        logger.debug("%s: %s", path, warning)
        return None, warning
    try:
        if data.get("state") == "paused":
            return PauseReceipt.model_validate(data), None
        return RunReceipt.model_validate(data), None
    except ValidationError:
        warning = (
            "receipt_unavailable: unsupported schema_version="
            f"{data.get('schema_version')!s}"
        )
        logger.debug("%s: %s", path, warning)
        return None, warning


def _receipt_run_ids(settings: AgentSettings) -> list[str]:
    root = settings.state_root / "receipts"
    if not root.exists():
        return []
    return sorted(path.stem for path in root.glob("*.json"))


async def load_run_facts(
    settings: AgentSettings, run_id: str
) -> RunFacts | None:
    """Load every fact for one run; ``None`` when nothing is persisted.

    Read order is by authority: execution facts (events, tool ledger) are
    read independently and FIRST; snapshot and receipt are best-effort
    enrichments that can each fail without touching the others.
    """
    store = open_step_store(settings)
    record = await store.get_run(run_id=run_id)
    receipt, diagnostic = _load_receipt(_receipt_path(settings, run_id))

    async def _events() -> tuple[StepEvent, ...]:
        try:
            return tuple(await store.list_events(run_id=run_id))
        except (OSError, ValueError):
            return ()

    async def _effects() -> tuple[ToolEffectRecord, ...]:
        try:
            return tuple(await store.list_unresolved_tool_effects(run_id=run_id))
        except (OSError, ValueError):
            return ()

    async def _snapshot() -> ContinuableSnapshot | None:
        # include_interrupted: a paused run's frontier snapshot IS its history.
        try:
            return await store.latest_snapshot(
                run_id=run_id, include_interrupted=True
            )
        except (OSError, ValueError, LookupError):
            return None

    events, unresolved, snapshot = await asyncio.gather(
        _events(), _effects(), _snapshot()
    )
    if record is None and receipt is None and not events and diagnostic is None:
        return None
    return RunFacts(
        run_id=run_id,
        record=record,
        events=events,
        receipt=receipt,
        snapshot=snapshot,
        tool_effects=unresolved,
        diagnostics=(diagnostic,) if diagnostic else (),
    )


async def list_run_facts(
    settings: AgentSettings,
    *,
    limit: int | None = None,
    cursor: str | None = None,
    status: str | None = None,
) -> tuple[list[RunFacts], str | None]:
    """Bounded, newest-first page of run facts merged from both stores.

    A run exists if EITHER store knows it; settlement status comes from the
    projector over the same facts the detail view uses, so list and detail
    never disagree. Snapshot payloads are deliberately not loaded here —
    the list page needs lifecycle facts only.
    """
    page_size = min(limit if limit is not None else _DEFAULT_LIMIT, _MAX_LIMIT)
    if page_size < 1:
        raise ValueError("limit must be >= 1")
    offset = 0
    if cursor:
        try:
            offset = int(cursor)
            if offset < 0:
                raise ValueError
        except ValueError as exc:
            raise ValueError("cursor must be a non-negative integer") from exc

    store = open_step_store(settings)
    records = await store.list_runs()  # full set, started_at ascending
    records_by_id = {record.run_id: record for record in records}

    run_ids = set(records_by_id) | set(_receipt_run_ids(settings))
    receipts: dict[str, tuple[AnyReceipt | None, str | None]] = {}

    def _started_at(run_id: str):
        record = records_by_id.get(run_id)
        if record is not None:
            return record.started_at
        if run_id not in receipts:
            receipts[run_id] = _load_receipt(_receipt_path(settings, run_id))
        receipt = receipts[run_id][0]
        return receipt.started_at if receipt else None

    # Harness contract: list_runs() is complete and ascending — newest-first
    # display is a plain reversal plus a bounded page. No index, no cache.
    # Runs with no known start stamp sort last (descending), never first.
    ordered = sorted(
        run_ids,
        key=lambda r: (
            _started_at(r) is not None,
            timestamp_sort_key(_started_at(r)),
        ),
        reverse=True,
    )

    page: list[RunFacts] = []
    scanned = offset
    for run_id in ordered[offset:]:
        scanned += 1
        record = records_by_id.get(run_id)
        if run_id not in receipts:
            receipts[run_id] = _load_receipt(_receipt_path(settings, run_id))
        receipt, diagnostic = receipts[run_id]
        # Enrich only the bounded page: status/counts/timing come from real
        # events so the list never shows all-unknown rows while facts exist.
        try:
            events: tuple[StepEvent, ...] = tuple(
                await store.list_events(run_id=run_id)
            )
        except (OSError, ValueError):
            events = ()
        facts = RunFacts(
            run_id=run_id,
            record=record,
            events=events,
            receipt=receipt,
            snapshot=None,
            tool_effects=(),
            diagnostics=(diagnostic,) if diagnostic else (),
        )
        if status is not None and derive_run_status(facts.receipt, facts.events) != status:
            continue
        page.append(facts)
        if len(page) >= page_size:
            break

    next_cursor: str | None = None
    if len(page) >= page_size and scanned < len(ordered):
        next_cursor = str(scanned)
    return page, next_cursor


def read_receipt(settings: AgentSettings, run_id: str) -> AnyReceipt | None:
    return _load_receipt(_receipt_path(settings, run_id))[0]


async def run_revision(settings: AgentSettings, run_id: str) -> str | None:
    """Cheap change signal for SSE invalidation (T008C).

    Event count via the store's public API plus a stat of ZUAEF's own
    receipt file — never the harness's private on-disk layout, so a layout
    change cannot silently kill live updates. ``None`` means neither source
    holds anything for the run (0 events AND no receipt file).
    """
    store = open_step_store(settings)
    try:
        count = len(await store.list_events(run_id=run_id))
    except (OSError, ValueError):
        count = 0
    receipt_stamp = "-"
    path = _receipt_path(settings, run_id)
    try:
        stat = path.stat()
    except OSError:
        pass
    else:
        receipt_stamp = f"{stat.st_mtime_ns:x}{stat.st_size:x}"
    if count == 0 and receipt_stamp == "-":
        return None
    return f"events={count};receipt={receipt_stamp}"


def open_receipt_store(settings: AgentSettings) -> ReceiptStore:
    return ReceiptStore(settings.state_root)
