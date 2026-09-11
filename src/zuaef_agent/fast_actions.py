"""Deterministic fast actions for the Gateway dispatch path.

This module is intentionally tiny: it recognizes mechanically extractable
inbound messages that must not start an Agent run.  The first and only
supported action is ``EXPLICIT_PERSIST`` — the user supplied the full text
and asked only to record it.

Design rule: false negatives are preferable to false positives.  A reply that
looks like persistence but carries a reference ("刚才那个"), an appended task
("记录下来并分析"), or any other semantic dependency falls through to the
normal profile run, where the Agent can resolve the reference and honor the
full request.

A handled fast action writes directly through ``KnowledgeStore.write_doc``.
It never allocates a run id, never sends an ack/progress message, never calls
the model, and never mutates session state.  Persistence preserves provenance;
it does not verify the supplied content.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .knowledge_store import KnowledgeStore

VERIFICATION_NOT_REQUESTED = "not_requested"
SOURCE_USER_ORIGINAL = "用户原文"

# A trailing ``记录下来`` line marker: "<complete content>\n记录下来".
_TRAILING_LINE_MARKER = re.compile(
    r"^(?P<content>.+?)\n[ \t]*记录下来[ \t]*[。.!！,，]?[ \t]*$",
    re.DOTALL,
)

# A trailing dash marker: "<complete content> —— 记录下来" (two or more
# em-dashes or ASCII hyphens).  The non-greedy content group plus the end
# anchor makes the final marker win, so dashes inside the supplied text are
# preserved as content.
_TRAILING_DASH_MARKER = re.compile(
    r"^(?P<content>.+?)[ \t]*(?:—{2,}|-{2,})[ \t]*记录下来[ \t]*[。.!！,，]?[ \t]*$",
    re.DOTALL,
)

# Explicit "record what follows" prefixes.  The colon is required; the body is
# the remainder of the current message, so recognition never depends on prior
# conversation turns.
_PREFIX_MARKERS = (
    re.compile(r"^记录以下内容[ \t]*[：:][ \t]*(?P<content>.+)$", re.DOTALL),
    re.compile(r"^把下面这段保存下来[ \t]*[：:][ \t]*(?P<content>.+)$", re.DOTALL),
)

# Content that is itself only a deictic reference cannot be persisted by this
# fast path: the referenced material is not in the current message.  Keep this
# list deliberately narrow; longer supplied prose is never treated as a bare
# reference merely because it contains one of these words.
_BARE_REFERENCE = re.compile(
    r"^(?:请|把|将|麻烦)?"
    r"(?:刚才(?:那个|这个)?|之前(?:那个|这个)?|上面(?:那个|这个)?|上述|"
    r"这个|那个|这些|那些|这条|那(?:一)?条|这段|那段|此|它)"
    r"(?:的)?(?:内容|结论|话|东西|资料)?[。.!！,，]?$"
)

# An explicit second task is outside mechanical persist even when the text
# could technically be extracted as content.  These markers are only checked
# at the outer edges of the supplied body; a full sentence may legitimately
# contain the same words, but a leading imperative clearly turns recording
# into research/validation.
_COMPOUND_LEAD = re.compile(
    r"^(?:然后|接着|再|并|并且|同时|顺便|另外|之后)?[ \t]*"
    r"(?:帮我|请|替我|帮忙)?[ \t]*"
    r"(?:验证|分析|研究|判断|检查|核实|核查|核对|查证|调查|复盘|评估|"
    r"解释|总结|扩展|润色|修改|查一下|检索|搜索|记录并|记录后|记录下来并)"
)


@dataclass(frozen=True)
class FastActionResult:
    """Result of the deterministic fast-action gate.

    ``handled=False`` means the Gateway must continue into the normal profile
    run.  ``handled=True`` carries the only user-visible reply; the operation
    itself has already completed.
    """

    handled: bool
    reply: str | None = None


def try_fast_action(
    *,
    text: str,
    workspace_root: Path,
    now: datetime,
) -> FastActionResult:
    """Try to handle a small set of mechanical inbound actions without a run.

    The Gateway calls this after slash-command and pause handling but before
    run-id allocation, acknowledgment/progress messages and profile execution.
    """
    content = extract_explicit_persist_content(text)
    if content is None:
        return FastActionResult(handled=False)

    note_id = (
        f"notes/{now.date().isoformat()}/note-{now.strftime('%Y%m%dT%H%M%S').lower()}-"
        f"{uuid4().hex[:8]}"
    )
    recorded_at = now.isoformat(timespec="seconds")
    body = (
        f"来源：{SOURCE_USER_ORIGINAL}\n"
        f"记录时间：{recorded_at}\n"
        f"验证状态：{VERIFICATION_NOT_REQUESTED}\n"
        "\n"
        "原文：\n"
        "\n"
        f"{content}\n"
    )
    KnowledgeStore(workspace_root).write_doc(
        knowledge_id=note_id,
        title="用户原文记录",
        body=body,
        tags=["explicit-persist", "not_requested", "user-original"],
        generated_by="zuaef-fast-action",
    )
    return FastActionResult(
        handled=True,
        reply=(
            f"已记录：{now.date().isoformat()} · 用户原文。\n"
            f"来源：{SOURCE_USER_ORIGINAL}；验证状态：{VERIFICATION_NOT_REQUESTED}；"
            "本次只做记录，没有进行验证。"
        ),
    )


def extract_explicit_persist_content(text: str) -> str | None:
    """Return verbatim supplied content when the current message is an
    unambiguous "record this text" request, else ``None``.

    The function operates on the current message only.  It never consults
    conversation history or any external state.
    """
    if not isinstance(text, str):
        return None
    raw = text.strip()
    if not raw:
        return None

    candidate: str | None = None
    for pattern in (*_PREFIX_MARKERS, _TRAILING_LINE_MARKER, _TRAILING_DASH_MARKER):
        match = pattern.fullmatch(raw)
        if match is None:
            continue
        candidate = match.group("content")
        break

    if candidate is None:
        return None

    stripped = candidate.strip()
    if not stripped:
        return None
    if _BARE_REFERENCE.fullmatch(stripped):
        return None
    if _looks_like_compound_request(stripped):
        return None
    return stripped


def _looks_like_compound_request(content: str) -> bool:
    """True when the supplied body opens with an explicit second task.

    This is intentionally only a leading-edge check: a recorded causal essay
    may use the words "验证" or "分析" inside its discussion.  A body that
    begins with "验证..." / "然后帮我分析..." is a compound request, not a
    mechanical persist.
    """
    first_line = content.strip().splitlines()[0].strip()
    if not first_line:
        return False
    return _COMPOUND_LEAD.match(first_line) is not None
