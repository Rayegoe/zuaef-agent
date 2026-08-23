"""The bounded Run Analysis action.

Run Analysis is a profile-like use of the existing core Agent, not a second
runtime.  Its only model-visible actions are bound, read-only inspection
tools.  The terminal text is then handed off by the Console to the normal
workspace artifact tree as ``analysis.md``.

The subject run is captured when the action starts and cannot be changed by
the model.  This keeps the analysis run separate from the run it diagnoses
and prevents the analyst from acquiring the production Agent's tools.
"""

from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from pydantic_ai import FunctionToolset, RunContext
from pydantic_ai.toolsets import AbstractToolset

from ..config import GENERALIST_FLAGS, AgentSettings
from ..core import build_agent
from ..models import CoreDeps
from ..runtime import PausedRun, execute_run
from . import readers
from .analysis_projector import render_projection_json, render_projection_markdown
from .analysis_store import (
    analysis_artifact_path,
    export_projection,
    projection_paths,
    render_observed_facts,
)
from .projector import RunFacts

_MAX_INTENT_CHARS = 2_000
_MAX_ANALYSIS_BYTES = 120_000
_MAX_PROJECTION_CHARS = 16_000
_MAX_PROJECTION_SECTION_CHARS = 12_000
_VALID_RUN_ID_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
)


ANALYSIS_INSTRUCTIONS = """
You are the ZUAEF Run Analysis analyst. Diagnose the named subject run; do
not perform the subject task and do not repair code in this run.

Start by calling inspect_run. It is a compact deterministic summary. Only call
read_run_projection when a bounded section or chunk is needed to distinguish a
pattern. Never ask for or reconstruct the full raw log. The projection is
fact-only: missing content, usage or artifact bodies remain unknown.

Separate execution path from business outcome. A completed tool call does not
prove that the business artifact is correct, and a chronology does not prove
causation. Do not browse the web, use a shell, read repository files, modify
the subject run, rewrite receipts, or propose automatic self-modification.

The Host owns run relationship metadata and Section 2. Do not write an
Observed Facts section. Do not rename tools or identifiers. Never infer a
configured token or output limit from observed usage; absent configuration
evidence remains unknown.

Return only concise Markdown with exactly these second-level sections, in
order:

## 1. Outcome
State the execution state and business-artifact outcome. If quality cannot be
judged from the available facts, say so explicitly.

## 3. Interpretation
Explain what the facts may mean for the business result. Keep evidence gaps
explicit; correlation is not causation.

## 4. Causal Hypothesis
State one primary hypothesis and, only when necessary, one secondary
hypothesis. Explicitly distinguish projected observations, interpretation,
and unproved causal assumptions. Use uncertain language, identify what is not
proved, and never upgrade a hypothesis to fact.

## 5. Smallest Next Experiment
Propose exactly one discriminating experiment that can distinguish the
primary hypothesis from a competing explanation. Include the unchanged
baseline, the one candidate change, the expected observable difference, and
a business quality guard. Do not propose changing the model, backend,
renderer, prompt and skill together.
""".strip()


_MODEL_SECTION_HEADINGS = (
    "## 1. Outcome",
    "## 3. Interpretation",
    "## 4. Causal Hypothesis",
    "## 5. Smallest Next Experiment",
)
_ANALYSIS_PROMPT_PREFIX = "Analyze subject run `"
_ANALYSIS_PROMPT_SUFFIX = "`."


class AnalysisError(Exception):
    """A bounded operator-facing Run Analysis error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AnalysisResult:
    state: str
    subject_run_id: str
    analysis_run_id: str | None = None
    artifact_path: str | None = None
    error: str | None = None


_lock = threading.Lock()
_in_flight: dict[str, str] = {}
_results: dict[str, AnalysisResult] = {}


def _safe_run_id(run_id: str) -> str:
    if (
        not isinstance(run_id, str)
        or not run_id
        or any(char not in _VALID_RUN_ID_CHARS for char in run_id)
    ):
        raise AnalysisError("INVALID_RUN_ID", f"invalid run id: {run_id!r}")
    return run_id


def analysis_path(settings: AgentSettings, subject_run_id: str) -> Path:
    """Return the only path owned by a subject's Run Analysis artifact."""
    subject_run_id = _safe_run_id(subject_run_id)
    return analysis_artifact_path(settings, subject_run_id)


def artifact_path_text(settings: AgentSettings, subject_run_id: str) -> str:
    return str(analysis_path(settings, subject_run_id).relative_to(settings.workspace_root))


def _workspace_paths(settings: AgentSettings, subject_run_id: str) -> dict[str, str]:
    return {
        key: str(path.relative_to(settings.workspace_root))
        for key, path in projection_paths(settings, subject_run_id).items()
    }


def read_analysis(settings: AgentSettings, subject_run_id: str) -> str | None:
    """Read the bounded analysis artifact, if it has been created."""
    path = analysis_path(settings, subject_run_id)
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise AnalysisError("ANALYSIS_READ_FAILED", str(exc)) from exc
    if len(data) > _MAX_ANALYSIS_BYTES:
        raise AnalysisError(
            "ANALYSIS_TOO_LARGE",
            f"analysis.md exceeds the {_MAX_ANALYSIS_BYTES}-byte read cap",
        )
    return data.decode("utf-8")


def analysis_state(settings: AgentSettings, subject_run_id: str) -> dict[str, object]:
    """Return transient action state plus a ready artifact when present."""
    subject_run_id = _safe_run_id(subject_run_id)
    with _lock:
        analysis_run_id = _in_flight.get(subject_run_id)
        result = _results.get(subject_run_id)
    paths = _workspace_paths(settings, subject_run_id)
    if analysis_run_id is not None:
        return {
            "state": "running",
            "subject_run_id": subject_run_id,
            "analysis_run_id": analysis_run_id,
            "artifact_path": artifact_path_text(settings, subject_run_id),
            "workspace_path": str(
                analysis_path(settings, subject_run_id).parent.relative_to(
                    settings.workspace_root
                )
            ),
            **paths,
        }
    if result is not None:
        payload = {
            "state": result.state,
            "subject_run_id": subject_run_id,
            "analysis_run_id": result.analysis_run_id,
            "artifact_path": result.artifact_path,
            "error": result.error,
            "workspace_path": str(
                analysis_path(settings, subject_run_id).parent.relative_to(
                    settings.workspace_root
                )
            ),
            **paths,
        }
        if result.state == "completed":
            payload["content"] = read_analysis(settings, subject_run_id)
        return payload
    content = read_analysis(settings, subject_run_id)
    return {
        "state": "completed" if content is not None else "not_started",
        "subject_run_id": subject_run_id,
        "analysis_run_id": None,
        "artifact_path": (
            artifact_path_text(settings, subject_run_id)
            if content is not None
            else None
        ),
        "workspace_path": str(
            analysis_path(settings, subject_run_id).parent.relative_to(
                settings.workspace_root
            )
        ),
        **paths,
        "content": content,
    }


async def _subject_facts(
    settings: AgentSettings, subject_run_id: str
) -> RunFacts:
    facts = await readers.load_run_facts(settings, subject_run_id)
    if facts is None:
        raise AnalysisError("RUN_NOT_FOUND", f"Run {subject_run_id} not found")
    return facts


def make_inspection_toolset(
    settings: AgentSettings,
    subject_run_id: str,
) -> AbstractToolset[CoreDeps]:
    """Bind exactly two read-only inspection tools to one subject run."""
    subject_run_id = _safe_run_id(subject_run_id)
    toolset: FunctionToolset[CoreDeps] = FunctionToolset(
        instructions=(
            "Run Inspection is read-only and is bound to the subject run "
            f"{subject_run_id}. Start with inspect_run. Use "
            "read_run_projection only for a bounded projection section or "
            "chunk; it never returns an unbounded raw log."
        )
    )

    @toolset.tool
    async def inspect_run(ctx: RunContext[CoreDeps]) -> str:
        """Inspect the compact deterministic summary of the subject run."""
        del ctx
        try:
            facts = await _subject_facts(settings, subject_run_id)
            rendered = render_projection_markdown(facts)
            if len(rendered) <= _MAX_PROJECTION_CHARS:
                return rendered
            return (
                rendered[:_MAX_PROJECTION_CHARS].rstrip()
                + "\n\n[projection truncated at the read boundary]\n"
            )
        except AnalysisError as exc:
            return json.dumps(
                {"error": {"code": exc.code, "message": exc.message}},
                ensure_ascii=False,
            )

    @toolset.tool
    async def read_run_projection(
        ctx: RunContext[CoreDeps],
        section: str,
        offset: int = 0,
        limit: int = 8_000,
    ) -> str:
        """Read one bounded section or chunk of the subject projection."""
        del ctx
        if not isinstance(section, str) or not section:
            return json.dumps(
                {"error": {"code": "INVALID_SECTION", "message": "section must be a non-empty string"}},
                ensure_ascii=False,
            )
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return json.dumps(
                {"error": {"code": "INVALID_SCOPE", "message": "offset must be a non-negative integer"}},
                ensure_ascii=False,
            )
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 1
            or limit > _MAX_PROJECTION_SECTION_CHARS
        ):
            return json.dumps(
                {
                    "error": {
                        "code": "SCOPE_TOO_LARGE",
                        "message": f"limit must be between 1 and {_MAX_PROJECTION_SECTION_CHARS}",
                    }
                },
                ensure_ascii=False,
            )
        try:
            facts = await _subject_facts(settings, subject_run_id)
            projection = render_projection_json(facts)
            if section not in projection:
                return json.dumps(
                    {
                        "error": {
                            "code": "UNKNOWN_SECTION",
                            "message": f"unknown section {section!r}",
                            "available_sections": sorted(projection),
                        }
                    },
                    ensure_ascii=False,
                )
            value = projection[section]
            serialized = (
                value
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False, indent=2)
            )
            chunk = serialized[offset : offset + limit]
            return json.dumps(
                {
                    "section": section,
                    "offset": offset,
                    "limit": limit,
                    "truncated": offset + len(chunk) < len(serialized),
                    "content": chunk,
                },
                ensure_ascii=False,
            )
        except AnalysisError as exc:
            return json.dumps(
                {"error": {"code": exc.code, "message": exc.message}},
                ensure_ascii=False,
            )

    return toolset


def _analysis_settings(settings: AgentSettings) -> AgentSettings:
    changes: dict[str, object] = {
        "enable_planning": False,
        "enable_skills": False,
        "enable_filesystem": False,
        "enable_knowledge": False,
        # ToolOutputLimits would add the generic read_tool_result tool. The
        # analysis contract is intentionally exactly two bound read tools;
        # both of those tools already enforce their own output caps.
        "enable_tool_output_limits": False,
        "enable_step_persistence": True,
    }
    changes.update({flag: False for flag in GENERALIST_FLAGS})
    changes["request_limit"] = min(settings.request_limit, 8)
    changes["tool_calls_limit"] = min(settings.tool_calls_limit, 24)
    return settings.with_overrides(**changes)


def _analysis_prompt(
    subject_run_id: str,
    *,
    intent: str | None,
    scope: str,
    selected_row_id: str | None,
) -> str:
    operator_intent = (intent or "Diagnose the subject run for the next engineering experiment.").strip()
    scope_note = f"Selected Console row: {selected_row_id}." if selected_row_id else "Scope: full run."
    return (
        f"Analyze subject run `{subject_run_id}`.\n"
        f"Operator intent: {operator_intent[:_MAX_INTENT_CHARS]}\n"
        f"Requested scope: {scope}. {scope_note}\n\n"
        "Use the bound inspection tools and then return only the required "
        "Markdown Sections 1, 3, 4, and 5. The Host supplies Section 2."
    )


def _extract_model_sections(presentation: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in presentation.strip().splitlines():
        if line.startswith("## "):
            current = line if line in _MODEL_SECTION_HEADINGS else None
            if current is not None:
                if current in sections:
                    raise AnalysisError(
                        "INCOMPLETE_ANALYSIS",
                        f"analysis Agent repeated required heading {current!r}",
                    )
                sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)

    missing = [
        heading
        for heading in _MODEL_SECTION_HEADINGS
        if not "\n".join(sections.get(heading, ())).strip()
    ]
    if missing:
        raise AnalysisError(
            "INCOMPLETE_ANALYSIS",
            "analysis Agent omitted or emptied required sections: "
            + ", ".join(missing),
        )
    return {heading: "\n".join(sections[heading]).strip() for heading in _MODEL_SECTION_HEADINGS}


def _nested_subject_run_id(facts: RunFacts) -> str | None:
    """Parse the fixed Analysis task sentence from persisted subject history."""
    if not facts.run_id.startswith("analysis-") or facts.snapshot is None:
        return None
    for message in facts.snapshot.messages:
        if getattr(message, "kind", None) != "request":
            continue
        for part in getattr(message, "parts", ()):
            if getattr(part, "part_kind", None) != "user-prompt":
                continue
            content = getattr(part, "content", None)
            if not isinstance(content, str):
                continue
            lines = content.splitlines()
            first_line = lines[0] if lines else ""
            if not (
                first_line.startswith(_ANALYSIS_PROMPT_PREFIX)
                and first_line.endswith(_ANALYSIS_PROMPT_SUFFIX)
            ):
                continue
            nested = first_line[
                len(_ANALYSIS_PROMPT_PREFIX) : -len(_ANALYSIS_PROMPT_SUFFIX)
            ]
            if nested and all(char in _VALID_RUN_ID_CHARS for char in nested):
                return nested
    return None


def _analysis_metadata(
    subject_run_id: str, analysis_run_id: str, facts: RunFacts
) -> str:
    subject_kind = "analysis" if subject_run_id.startswith("analysis-") else "run"
    lines = [
        f"> Analysis run: `{analysis_run_id}`",
        f"> Subject run: `{subject_run_id}`",
        f"> Subject kind: {subject_kind}",
    ]
    if subject_kind == "analysis":
        nested = _nested_subject_run_id(facts)
        lines.append(f"> Nested subject: `{nested}`" if nested else "> Nested subject: unknown")
    lines.append("> Runtime facts remain authoritative in ZUAEF Console.")
    return "\n".join(lines)


def _format_analysis_artifact(
    subject_run_id: str,
    analysis_run_id: str,
    presentation: str,
    facts: RunFacts,
) -> str:
    content = presentation.strip()
    if not content:
        raise AnalysisError("EMPTY_ANALYSIS", "analysis Agent returned no Markdown")
    sections = _extract_model_sections(content)
    rendered = (
        f"# Run Analysis — {subject_run_id}\n\n"
        f"{_analysis_metadata(subject_run_id, analysis_run_id, facts)}\n\n"
        f"## 1. Outcome\n{sections['## 1. Outcome']}\n\n"
        f"{render_observed_facts(facts)}\n\n"
        f"## 3. Interpretation\n{sections['## 3. Interpretation']}\n\n"
        "## 4. Causal Hypothesis\n"
        f"{sections['## 4. Causal Hypothesis']}\n\n"
        "## 5. Smallest Next Experiment\n"
        f"{sections['## 5. Smallest Next Experiment']}\n"
    )
    if len(rendered.encode("utf-8")) > _MAX_ANALYSIS_BYTES:
        raise AnalysisError(
            "ANALYSIS_TOO_LARGE",
            f"analysis.md exceeds the {_MAX_ANALYSIS_BYTES}-byte write cap",
        )
    return rendered


def _write_new_analysis(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise AnalysisError(
            "ANALYSIS_EXISTS",
            f"refusing to overwrite existing analysis artifact: {path}",
        )
    path.write_text(content, encoding="utf-8")


def start_analysis(
    settings: AgentSettings,
    subject_run_id: str,
    *,
    intent: str | None = None,
    scope: str = "full",
    selected_row_id: str | None = None,
) -> str:
    """Launch one bounded analysis Agent for a subject run."""
    subject_run_id = _safe_run_id(subject_run_id)
    if scope not in {"full", "selected_event"}:
        raise AnalysisError("INVALID_SCOPE", f"unsupported analysis scope: {scope!r}")
    path = analysis_path(settings, subject_run_id)
    if path.exists():
        raise AnalysisError(
            "ANALYSIS_EXISTS",
            "analysis.md already exists; edit it in Stillwrite or remove it explicitly before creating a new analysis",
        )
    with _lock:
        if subject_run_id in _in_flight:
            raise AnalysisError("ANALYSIS_IN_FLIGHT", "analysis is already running")
        analysis_run_id = f"analysis-{uuid4().hex}"
        _in_flight[subject_run_id] = analysis_run_id
    thread = threading.Thread(
        target=_run_analysis,
        args=(settings, subject_run_id, analysis_run_id, intent, scope, selected_row_id),
        name=f"zuaef-web-analysis-{subject_run_id[:8]}",
        daemon=True,
    )
    thread.start()
    return analysis_run_id


def _run_analysis(
    settings: AgentSettings,
    subject_run_id: str,
    analysis_run_id: str,
    intent: str | None,
    scope: str,
    selected_row_id: str | None,
) -> None:
    result: AnalysisResult
    try:
        effective_settings = _analysis_settings(settings)
        facts = asyncio.run(
            readers.load_run_facts(effective_settings, subject_run_id)
        )
        if facts is None:
            raise AnalysisError("RUN_NOT_FOUND", f"Run {subject_run_id} not found")
        export_projection(effective_settings, facts)
        agent = build_agent(
            effective_settings,
            run_id=analysis_run_id,
            instructions=ANALYSIS_INSTRUCTIONS,
            extra_toolsets=[
                make_inspection_toolset(effective_settings, subject_run_id)
            ],
        )
        deps = CoreDeps(
            workspace_root=effective_settings.workspace_root.resolve(),
            run_id=analysis_run_id,
        )
        outcome = execute_run(
            agent,
            deps,
            prompt=_analysis_prompt(
                subject_run_id,
                intent=intent,
                scope=scope,
                selected_row_id=selected_row_id,
            ),
            settings=effective_settings,
            run_id=analysis_run_id,
        )
        if isinstance(outcome, PausedRun):
            raise AnalysisError(
                "ANALYSIS_PAUSED",
                "analysis Agent unexpectedly requested an approval",
            )
        if outcome.receipt.execution_state != "completed":
            raise AnalysisError(
                "ANALYSIS_RUN_FAILED",
                outcome.receipt.error or outcome.presentation,
            )
        content = _format_analysis_artifact(
            subject_run_id,
            analysis_run_id,
            outcome.presentation,
            facts,
        )
        path = analysis_path(settings, subject_run_id)
        _write_new_analysis(path, content)
        result = AnalysisResult(
            state="completed",
            subject_run_id=subject_run_id,
            analysis_run_id=analysis_run_id,
            artifact_path=artifact_path_text(settings, subject_run_id),
        )
    except Exception as exc:  # noqa: BLE001 — worker result must be observable
        result = AnalysisResult(
            state="failed",
            subject_run_id=subject_run_id,
            analysis_run_id=analysis_run_id,
            artifact_path=artifact_path_text(settings, subject_run_id),
            error=f"{type(exc).__name__}: {exc}",
        )
    with _lock:
        _in_flight.pop(subject_run_id, None)
        _results[subject_run_id] = result


__all__ = [
    "ANALYSIS_INSTRUCTIONS",
    "AnalysisError",
    "AnalysisResult",
    "analysis_path",
    "analysis_state",
    "artifact_path_text",
    "make_inspection_toolset",
    "read_analysis",
    "start_analysis",
]
