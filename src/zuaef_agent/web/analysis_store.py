"""Filesystem handoff for one Run Analysis workspace.

The directory is ordinary Markdown/JSON intended for Stillwrite and human
review. Runtime facts remain in StepPersistence/receipts; this module only
renders the already-loaded :class:`RunFacts` projection and never becomes a
second execution store.
"""

from __future__ import annotations

from pathlib import Path

from ..models import PauseReceipt
from .analysis_projector import (
    render_projection_json,
    render_projection_json_text,
    render_projection_markdown,
)
from .projector import RunFacts, project_run

_WORKSPACE_DIR = "analysis"
_VALID_RUN_ID_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
)


def _safe_run_id(run_id: str) -> str:
    if (
        not isinstance(run_id, str)
        or not run_id
        or any(char not in _VALID_RUN_ID_CHARS for char in run_id)
    ):
        raise ValueError(f"invalid run id: {run_id!r}")
    return run_id


def analysis_workspace(settings, subject_run_id: str) -> Path:
    """Return ``workspace/analysis/<subject_run_id>`` safely."""
    return settings.workspace_root / _WORKSPACE_DIR / _safe_run_id(subject_run_id)


def analysis_artifact_path(settings, subject_run_id: str) -> Path:
    return analysis_workspace(settings, subject_run_id) / "analysis.md"


def projection_paths(settings, subject_run_id: str) -> dict[str, Path]:
    root = analysis_workspace(settings, subject_run_id)
    return {
        "projection_md": root / "projection.md",
        "projection_json": root / "projection.json",
        "analysis_md": root / "analysis.md",
    }


def export_projection(settings, facts: RunFacts) -> dict[str, Path]:
    """Write the deterministic projection files for one analysis workspace.

    ``operator-notes.md`` is intentionally absent from this writer. Existing
    human notes and an existing ``analysis.md`` are never touched here.
    """
    paths = projection_paths(settings, facts.run_id)
    paths["projection_md"].parent.mkdir(parents=True, exist_ok=True)
    paths["projection_md"].write_text(
        render_projection_markdown(facts), encoding="utf-8"
    )
    paths["projection_json"].write_text(
        render_projection_json_text(facts) + "\n", encoding="utf-8"
    )
    return paths


def _observed_value(value: object) -> object:
    """Preserve projected values while making absence explicit."""
    return "unknown" if value is None or value == "" else value


def render_observed_facts(facts: RunFacts) -> str:
    """Render host-owned Section 2 from the existing run projection.

    This is a presentation helper only. It deliberately does not infer
    configuration from usage and does not reinterpret tool or artifact
    identifiers.
    """
    projection = project_run(facts)
    bounded_projection = render_projection_json(facts)
    run = projection["run"]
    execution_state = (
        "paused"
        if isinstance(facts.receipt, PauseReceipt)
        else getattr(facts.receipt, "execution_state", None)
    )
    outgoing = [
        "## 2. Observed Facts",
        f"- Run ID: `{facts.run_id}`",
        f"- Status: {_observed_value(run.get('status'))}",
        f"- Execution state: {_observed_value(execution_state)}",
        f"- Model: {_observed_value(run.get('model'))}",
        f"- Requests: {_observed_value(run.get('request_count'))}",
        f"- Tool calls: {_observed_value(run.get('tool_call_count'))}",
        "- Configured output limit: unknown",
        "- Usage:",
    ]

    usage = projection.get("usage")
    if isinstance(usage, dict) and usage:
        preferred_keys = (
            "input_tokens",
            "output_tokens",
            "reasoning_tokens",
            "cache_read_tokens",
            "cache_miss_tokens",
            "requests",
            "source",
        )
        keys = [key for key in preferred_keys if key in usage]
        keys.extend(sorted(key for key in usage if key not in preferred_keys))
        outgoing.extend(
            f"  - {key}: {_observed_value(usage[key])}" for key in keys
        )
    else:
        outgoing.append("  - unknown")

    tools = bounded_projection["tool_sequence"]["sequence"]
    tool_total = run["tool_call_count"]
    tools_omitted = max(tool_total - len(tools), 0)
    outgoing.append(
        f"- Tools ({tool_total} total, {len(tools)} shown, "
        f"{tools_omitted} omitted):"
    )
    if tools:
        for row in tools:
            outgoing.append(
                "  - "
                f"`{_observed_value(row.get('tool'))}` "
                f"(step={_observed_value(row.get('step'))}, "
                f"status={_observed_value(row.get('status'))})"
            )
    else:
        outgoing.append("  - none")

    artifacts = bounded_projection["artifacts"]
    artifact_total = len(projection["artifacts"])
    artifacts_omitted = max(artifact_total - len(artifacts), 0)
    outgoing.append(
        f"- Artifacts ({artifact_total} total, {len(artifacts)} shown, "
        f"{artifacts_omitted} omitted):"
    )
    if artifacts:
        outgoing.extend(
            "  - "
            f"`{_observed_value(artifact.get('path'))}` "
            f"(size={_observed_value(artifact.get('size'))}, "
            f"change={_observed_value(artifact.get('change'))})"
            for artifact in artifacts
        )
    else:
        outgoing.append("  - none")
    return "\n".join(outgoing)


__all__ = [
    "analysis_artifact_path",
    "analysis_workspace",
    "export_projection",
    "projection_paths",
    "render_observed_facts",
]
