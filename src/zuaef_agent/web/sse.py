"""SSE invalidation stream (T008C): one thin ``run_changed`` event per facts
change, nothing more.

The stream carries run_id + a revision string — never timeline payloads.
The browser answers every invalidation by refetching the HTTP projection,
which stays the single UI truth. No WebSocket, no duplicated event stream,
no metrics store.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable

from ..config import AgentSettings
from . import readers

SSE_MEDIA_TYPE = "text/event-stream"
_HEARTBEAT_SECONDS = 15.0


def sse_frame(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def run_changed_stream(
    settings: AgentSettings,
    run_id: str,
    *,
    poll_interval: float,
    heartbeat_seconds: float = _HEARTBEAT_SECONDS,
    is_disconnected: Callable[[], Awaitable[bool]] | None = None,
) -> AsyncIterator[str]:
    """Yield SSE frames while ``run_id``'s persisted facts change.

    Emits once on subscribe (so the client can confirm the stream is live),
    then whenever the revision changes. A revision that disappears after
    having existed means the run's facts were deleted: one final frame lets
    the client refetch into a 404, then the stream ends. A registered run
    with zero events and no receipt (revision ``None`` from the start) keeps
    streaming — its first real fact will arrive as a change.
    """
    last: str | None = None
    had_revision = False
    next_beat = time.monotonic() + heartbeat_seconds
    while True:
        if is_disconnected is not None and await is_disconnected():
            return
        await asyncio.sleep(poll_interval)
        revision = await readers.run_revision(settings, run_id)
        if revision is not None:
            had_revision = True
        if revision != last:
            last = revision
            next_beat = time.monotonic() + heartbeat_seconds
            yield sse_frame("run_changed", {"run_id": run_id, "revision": revision})
            if revision is None and had_revision:
                return
        elif time.monotonic() >= next_beat:
            next_beat = time.monotonic() + heartbeat_seconds
            yield ": ping\n\n"
