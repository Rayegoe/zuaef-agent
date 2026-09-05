"""Telegram reporting toolset — two model-visible actions.

``report_to_telegram`` is an external write (a message leaves the host for a
third-party service and a human's chat), so it carries the same native
PydanticAI approval contract as the WordPress write tools: the Agent owns
*what* is worth reporting; the human approves the external send.

``send_artifact_to_supervisor`` is operator SELF-delivery (spec Phase 2 §12):
the host hard-pins the recipient (``TELEGRAM_CHAT_ID``, not a tool parameter)
and the artifact scope, so the model has no recipient choice and no path
authority — the permission question is a capability boundary, not a prompt
constraint. Customer/external delivery stays behind its own approval gate
and never touches this tool.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic_ai import FunctionToolset
from pydantic_ai.toolsets import AbstractToolset

from zuaef_agent.effects import EffectClass, requires_approval
from zuaef_agent.models import CoreDeps

from .client import TelegramClient

#: Self-delivery scope: only files under this workspace-relative root may be
#: sent, only to the operator's own chat. Nothing else is reachable, ever.
DELIVERY_ROOT_PARTS = ("artifacts", "quant", "delivery")
ALLOWED_EXTENSIONS = {".html", ".json", ".csv", ".md", ".pdf", ".txt"}
MAX_ARTIFACT_BYTES = 20 * 1024 * 1024

TOOLSET_INSTRUCTIONS = """\
Send concise human-facing reports and operator-owned artifacts to the
configured Telegram chat (the supervisor's own chat).

- report_to_telegram is an external write (third-party service + a human's
  chat) and therefore requires explicit human approval before execution.
- send_artifact_to_supervisor sends a file from the quant delivery scope to
  the SAME operator chat. It is self-delivery, not customer delivery: the
  recipient and the allowed directory are host-fixed, so it needs no
  approval. Path validation is host-owned — a rejected path must not be
  retried with a variant; report the rejection instead.
- Report material milestones, completion, blocking failures, or when a human
  decision is required. Keep messages concise and outcome-oriented.
- Do not report routine internal reasoning or every tool action.
- Never send secrets, credentials, or private source material unless
  explicitly authorized.
"""


class ArtifactPathError(ValueError):
    """A path outside the host-pinned self-delivery boundary was requested."""


def resolve_delivery_artifact(path: str, workspace_root: Path) -> Path:
    """Host-owned path safety chain (spec Phase 2 §14): workspace-relative
    normalization → resolve() → containment in the quant delivery root →
    extension whitelist → regular file → size cap. Resolve() follows
    symlinks, so a link escaping the root fails containment here."""
    raw = Path(path.strip())
    if not str(raw) or raw.is_absolute() or ".." in raw.parts:
        raise ArtifactPathError("path must be a workspace-relative path without '..'")
    delivery_root = workspace_root.joinpath(*DELIVERY_ROOT_PARTS).resolve()
    candidate = (workspace_root / raw).resolve()
    if not candidate.is_relative_to(delivery_root):
        raise ArtifactPathError(
            "only files under workspace/artifacts/quant/delivery/ may be sent"
        )
    if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ArtifactPathError(
            f"extension {candidate.suffix!r} not allowed "
            f"(allowed: {sorted(ALLOWED_EXTENSIONS)})"
        )
    if not candidate.is_file():
        raise ArtifactPathError(f"not a regular file: {raw}")
    if candidate.stat().st_size > MAX_ARTIFACT_BYTES:
        raise ArtifactPathError(
            f"file too large: {candidate.stat().st_size} > {MAX_ARTIFACT_BYTES} bytes"
        )
    return candidate


def make_toolset(
    client: TelegramClient, *, workspace_root: Path
) -> AbstractToolset[CoreDeps]:
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=TOOLSET_INSTRUCTIONS
    )

    @toolset.tool_plain(requires_approval=requires_approval(EffectClass.EXTERNAL_WRITE))
    def report_to_telegram(message: str) -> str:
        """Send one concise report message to the configured Telegram chat (external write)."""
        return _json(client.send_message(message))

    @toolset.tool_plain
    def send_artifact_to_supervisor(path: str) -> str:
        """Send one file from the quant delivery scope
        (workspace/artifacts/quant/delivery/) to the operator's own Telegram
        chat as a document. The recipient is host-fixed; use
        render_quant_business_artifact first to produce the HTML report."""
        try:
            candidate = resolve_delivery_artifact(path, workspace_root)
        except ArtifactPathError as exc:
            return _json({"sent": False, "rejected": str(exc)})
        fact = client.send_document(candidate)
        return _json({"sent": True, **fact, "file": candidate.name})

    return toolset


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)
